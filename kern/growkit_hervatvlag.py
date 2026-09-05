#!/usr/bin/env python3
"""GrowKit hervatvlag (ronde 2) — één generiek "hervat waar je was"-mechanisme.

Geïnspireerd door Antigravity's installatiewizard, vastgesteld als
prioriteit 1 in de GrowKit-reactie (5 sept 2026). Twee toepassingen:
profiel-kieming en Tailscale-onboarding; elke toekomstige wizard kan
hem hergebruiken.

Regels:
- voortgang is append-only: elk event wordt toegevoegd, nooit overschreven
- "volgende" is altijd de eerste stap in de lijst die nog niet afgerond is —
  een overgeslagen stap kan geen gat creëren
- wizards zijn onafhankelijk: elke wizard heeft zijn eigen eventlog
- opslag lokaal, leesbaar, zonder secrets
"""
import json
from datetime import datetime, timezone
from pathlib import Path


def _nu() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _pad(naam: str, wortel: Path | None) -> Path:
    basis = Path(wortel) if wortel else Path.home() / "growkit-profiel"
    return basis / "hervatvlag" / f"{naam}.json"


def _laad(pad: Path) -> dict:
    if not pad.exists():
        return {"events": []}
    try:
        doc = json.loads(pad.read_text(encoding="utf-8"))
        if not isinstance(doc.get("events", []), list):
            raise ValueError
        return doc
    except (json.JSONDecodeError, ValueError):
        # corrupte voortgang = nette fout; geen auto-herstel (huisregel)
        raise ValueError(f"Hervatvlag {pad} is corrupt — roep de mens.")


def rond_af(naam: str, stap: str, *, wortel: Path | None = None) -> dict:
    """Markeer een stap als afgerond: één append-only event."""
    naam, stap = naam.strip(), stap.strip()
    if not naam or not stap:
        return {"ok": False, "fout": "rond_af vereist wizard-naam en stap."}
    pad = _pad(naam, wortel)
    pad.parent.mkdir(parents=True, exist_ok=True)
    doc = _laad(pad)
    doc["events"].append({"stap": stap, "tijd": _nu()})
    pad.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n",
                   encoding="utf-8")
    return {"ok": True, "data": {"wizard": naam, "stap": stap}}


def hervat(naam: str, stappen: list[str], *, wortel: Path | None = None) -> dict:
    """Waar was ik? Eerste stap uit `stappen` die niet als afgerond staat."""
    naam = naam.strip()
    if not naam or not stappen:
        return {"ok": False, "fout": "hervat vereist wizard-naam en stappenlijst."}
    pad = _pad(naam, wortel)
    doc = _laad(pad) if pad.exists() else {"events": []}
    afgerond_in_volgorde: list[str] = []
    gezien: set[str] = set()
    for event in doc["events"]:
        stap = event.get("stap", "")
        if stap in stappen and stap not in gezien:
            gezien.add(stap)
            afgerond_in_volgorde.append(stap)
    volgende = next((s for s in stappen if s not in gezien), None)
    return {"ok": True, "data": {
        "wizard": naam,
        "afgerond": afgerond_in_volgorde,
        "volgende": volgende,
        "klaar": volgende is None,
        "totaal": len(stappen),
    }}
