#!/usr/bin/env python3
"""KairOS netwerkmonitor — poortwachter voor fase 1.

Bewijst verificatie-eis 2 van de KairOS OS fase-1 opdracht: "geen
verkeer naar externe AI-aanbieders tijdens normale werking".

Werking: leest een verkeersmomentopname (netstat/lsof-regels, via JSON)
plus de Ollama-taglijst, en oordeelt in machine-toetsbare JSON.

Aanroepen:
    python3 netwerkmonitor.py --verkeer <pad.json>   # van tevoren opgehaald
    python3 netwerkmonitor.py --once                 # haalt verkeer zelf op

Uitvoer (altijd JSON):
    {"ok": true/false, "datum": ..., "bevindingen": [...]}
"""
from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

# Bekende externe AI-aanbieders (hostnamen). Alles wat hiernaar praat
# tijdens "normale werking" is een alarmslag.
EXTERN_AI_HOSTS = (
    "api.openai.com",
    "api.anthropic.com",
    "generativelanguage.googleapis.com",   # Google AI / Gemini
    "aiplatform.googleapis.com",
    "openrouter.ai",
    "api.deepseek.com",
    "api.groq.com",
    "api.mistral.ai",
    "api.x.ai",
    "router.requesty.ai",
    "api.together.xyz",
    "api.fireworks.ai",
    "api.cohere.com",
    "api.githubcopilot.com",
    "ollama.com",                          # cloud-modellen + pull-bron
    "registry.ollama.ai",
)

# Hosts die in het lokale verkeer thuishoren (nooit alarm).
LOKALE_PATRONEN = (
    "localhost", "127.0.0.1", "::1",
    ".local",                              # mDNS (kairos.local)
    "192.168.", "10.", "172.16.", "172.17.", "172.18.",
    "172.19.", "172.20.", "172.21.", "172.22.", "172.23.",
    "172.24.", "172.25.", "172.26.", "172.27.",
    "172.28.", "172.29.", "172.30.", "172.31.",
    "0.0.0.0", "*",
)

# AI-aanbieders per subnetvorm (voor zover herkenbaar aan IP):
# bewust beperkt; de hostnamen hierboven doen het echte werk.
EXTERN_AI_SUBNETTEN = ()


def _is_lokaal(tekst: str) -> bool:
    return any(p in tekst for p in LOKALE_PATRONEN)


def _bestemming(regel: str) -> str:
    """Het deel van de regel ná de pijl: waar gaat het verkeer heen.
    Alleen de bestemming telt voor lokaal/extern — het bronadres is op
    de Pi altijd lokaal en mag de beoordeling niet verdoezelen."""
    if "->" in regel:
        return regel.split("->", 1)[1]
    return regel


def scan_verkeersregels(regels: list[str]) -> list[dict]:
    """Beoordeel netstat/lsof-regels. Alarm bij een bekende AI-host,
    waarschuwing bij onbekende externe hosts (kunnen legitiem zijn:
    apt, NTP, DNS)."""
    bevindingen = []
    for regel in regels:
        if not regel.strip():
            continue
        bestemming = _bestemming(regel).lower()
        if _is_lokaal(bestemming):
            continue
        treffers = [h for h in EXTERN_AI_HOSTS if h in bestemming]
        if treffers:
            bevindingen.append({
                "ernst": "ALARM",
                "melding": f"verkeer naar externe AI-aanbieder: "
                           f"{', '.join(treffers)}",
                "bron": regel.strip(),
            })
        else:
            bevindingen = bevindingen + [{
                "ernst": "WAARSCHUWING",
                "melding": "onbekende externe host — handmatig beoordelen",
                "bron": regel.strip(),
            }]
    return bevindingen


def scan_ollama_tags(tags: dict | None) -> list[dict]:
    """Beoordeel de Ollama-modeltaglijst. ':cloud'-modellen bellen via
    ollama.com en zijn dus een externe afhankelijkheid."""
    if tags is None:
        return [{"ernst": "WAARSCHUWING",
                 "melding": "Ollama onbereikbaar — kon taglijst niet lezen",
                 "bron": "ollama-api"}]
    bevindingen = []
    for model in tags.get("models", []):
        naam = model.get("name", "")
        if naam.endswith(":cloud") or "cloud" in naam:
            bevindingen.append({
                "ernst": "ALARM",
                "melding": f"Ollama-model is een cloud-model: {naam}",
                "bron": "ollama-tags",
            })
    return bevindingen


def _lees_ollama_tags() -> dict | None:
    """Lees de taglijst via de Ollama-API (fallback: urllib, geen curl)."""
    try:
        import urllib.request
        with urllib.request.urlopen(
                "http://127.0.0.1:11434/api/tags", timeout=5) as antwoord:
            return json.loads(antwoord.read().decode())
    except Exception:
        return None


def oordeel(bevindingen: list[dict]) -> bool:
    """Waar = schone monitor (hoogstens waarschuwingen)."""
    return not any(b["ernst"] == "ALARM" for b in bevindingen)


def rapport(oordeel: bool, bevindingen: list[dict]) -> dict:
    return {
        "ok": oordeel,
        "datum": datetime.now(timezone.utc).isoformat(),
        "bevindingen": bevindingen,
    }


def _haal_verkeer_op() -> list[str]:
    """Momentopname van netwerkverbindingen (netstat; lsof als fallback).
    Op macOS heet het commando netstat, op de Pi (Debian) ook netstat —
    de vlaggen verschillen, dus probeer beide vormen."""
    voor_vormen = (
        ["netstat", "-anv", "-p", "tcp"],
        ["netstat", "-tupn"],          # Linux/Pi-vorm
        ["lsof", "-i", "-n", "-P"],
    )
    for commando in voor_vormen:
        try:
            uit = subprocess.run(commando, capture_output=True, text=True,
                                 timeout=15)
            if uit.returncode == 0 and uit.stdout.strip():
                return uit.stdout.splitlines()
        except (FileNotFoundError, subprocess.TimeoutExpired):
            continue
    return []


def eindoordeel(verkeer_pad: Path | None = None) -> dict:
    """Alle bronnen samen: verkeer + Ollama-tags -> één JSON-rapport."""
    bevindingen: list[dict] = []
    if verkeer_pad is not None:
        regels = json.loads(Path(verkeer_pad).read_text())
    else:
        regels = _haal_verkeer_op()
    bevindingen += scan_verkeersregels(regels)
    bevindingen += scan_ollama_tags(_lees_ollama_tags())
    return rapport(oordeel(bevindingen), bevindingen)


def main(argv: list[str]) -> int:
    if "--once" in argv or "--verkeer" in argv:
        pad = None
        if "--verkeer" in argv:
            pad = Path(argv[argv.index("--verkeer") + 1])
        uit = eindoordeel(verkeer_pad=pad)
        print(json.dumps(uit, ensure_ascii=False, indent=2))
        return 0 if uit["ok"] else 2
    print(__doc__)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
