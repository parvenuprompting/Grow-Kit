"""Bewijsruns KairOS fase 1 — 6 sept 2026 (op de Mac).

Run 1: netwerkmonitor --once op deze Mac. De Mac heeft wél :cloud-modellen
in Ollama, dus de monitor MOET alarm slaan (positieve test: de poortwachter
bijt). Uitvoer -> bewijs/netwerkmonitor-mac-2026-09-06.json

Run 2: lokale modelrespons gemma3:1b via de Ollama-API (127.0.0.1), twee
testvragen uit de testset. Uitvoer -> bewijs/ollama-demo-2026-09-06.log
"""
import json
import subprocess
import sys
import urllib.request
from pathlib import Path

BEWIJS = Path(__file__).parent
REPO = Path(__file__).resolve().parents[4]  # bewijs -> fase1 -> plannen -> docs -> repo
MONITOR = REPO / "scripts" / "kairos" / "netwerkmonitor.py"
assert MONITOR.exists(), f"monitor niet gevonden: {MONITOR}"

print("=== RUN 1: netwerkmonitor (verwacht: ALARM op :cloud-modellen) ===")
uit = subprocess.run(
    [sys.executable, str(MONITOR), "--once"],
    capture_output=True, text=True, timeout=120)
if uit.returncode not in (0, 2):
    print("MONITOR FAALDE:", uit.stderr[:800])
    sys.exit(1)
print(uit.stdout[:2500])
(BEWIJS / "netwerkmonitor-mac-2026-09-06.json").write_text(uit.stdout)
monitor_vangt = '"ok": false' in uit.stdout
assert monitor_vangt, "monitor sloeg GEEN alarm — bewijs ongeldig"

print()
print("=== RUN 2: lokaal model gemma3:1b (volledig via 127.0.0.1) ===")


def vraag(prompt: str, systeem: str | None = None) -> str:
    berichten = []
    if systeem:
        berichten.append({"role": "system", "content": systeem})
    berichten.append({"role": "user", "content": prompt})
    verzoek = urllib.request.Request(
        "http://127.0.0.1:11434/api/chat",
        data=json.dumps({
            "model": "gemma3:1b",
            "messages": berichten,
            "stream": False,
            "keep_alive": "24h",
        }).encode(),
        headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(verzoek, timeout=180) as antwoord:
        return json.loads(antwoord.read().decode())["message"]["content"]


regels = [
    "KairOS fase 1 — bewijs lokale modelrespons (gemma3:1b via Ollama, 127.0.0.1)",
    "Gedraaid op de Mac; op de Pi wordt dezelfde testset offline herhaald.",
    "",
    "--- Testvraag 1 (stijl: één korte Nederlandse zin) ---",
    "VRAAG: Zeg in één zin wat een vangnet doet.",
]
a1 = vraag("Zeg in één zin wat een vangnet doet.")
regels += ["ANTWOORD: " + a1.strip(), ""]

soul = (
    "Je bent de Vangnet-specialist van Tiëndo. Je controleert antwoorden: "
    "Nederlands, kort, zonder herhaling. Je antwoordt altijd in het Nederlands "
    "en in de eerste persoon."
)
regels += [
    "--- Testvraag 4 (met systeem-prompt: past bij de persoon) ---",
    "VRAAG: Wie ben je en wat doe je?",
]
a2 = vraag("Wie ben je en wat doe je?", systeem=soul)
regels += ["ANTWOORD: " + a2.strip(), ""]

tekst = "\n".join(regels)
print(tekst)
(BEWIJS / "ollama-demo-2026-09-06.log").write_text(tekst)
print()
print("Klaar. Bewijsstukken staan in bewijs/.")
