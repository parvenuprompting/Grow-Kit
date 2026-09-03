"""GrowKit review-laag — provider-agnostische reviewer-rollen (spec §9, §12.5).

Rollen, geen leveranciers: nergens een modelnaam in code of defaults.
Machine-bewijs blijft eerste keus; de reviewer vermindert mens-inzet en
vervangt de mens niet.
"""
import json
import subprocess
import urllib.request
from pathlib import Path

# Verboden velden: leveranciers-binding is een schema-fout (§12.5).
_VERBODEN_VELDEN = ("model", "provider", "leverancier")
_GELDIGE_TYPES = {"http", "cli"}
_OORDELEN = ("geslaagd", "gefaald", "onduidelijk")


def laad_reviewconfig(pad: Path) -> dict | None:
    """Lees reviewconfig.json; None bij afwezigheid (review uit → alles naar de mens)."""
    if not pad.exists():
        return None
    try:
        with open(pad, encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        print(f"  ! Ongeldige reviewconfig ({pad}): {e} — review uit, alles gaat naar de mens.")
        return None


def valideer_reviewconfig(config: dict) -> list[str]:
    """Controleer de vorm van een reviewconfig. Lege lijst = geldig."""
    bevindingen = []
    rollen = config.get("rollen")
    if not isinstance(rollen, dict) or not rollen:
        return ["geen 'rollen'-mapping gevonden"]
    for naam, rol in rollen.items():
        if not isinstance(rol, dict):
            bevindingen.append(f"rol '{naam}' is geen object")
            continue
        for veld in _VERBODEN_VELDEN:
            if veld in rol:
                bevindingen.append(f"rol '{naam}': verboden veld '{veld}' — leveranciers-binding is een schema-fout (§12.5)")
        soort = rol.get("type")
        if soort not in _GELDIGE_TYPES:
            bevindingen.append(f"rol '{naam}': onbekend type {soort!r} (geldige types: {sorted(_GELDIGE_TYPES)})")
            continue
        if soort == "http":
            if not rol.get("url"):
                bevindingen.append(f"rol '{naam}': http-rol zonder 'url'")
        if soort == "cli":
            if not rol.get("commando"):
                bevindingen.append(f"rol '{naam}': cli-rol zonder 'commando'")
    return bevindingen


def _vertaal_antwoord(tekst: str) -> str:
    """Exacte string-match op de drie gecodeerde oordelen; alles anders = onduidelijk."""
    antwoord = tekst.strip()
    for oordeel in _OORDELEN:
        if antwoord == oordeel:
            return oordeel
    return "onduidelijk"


def roep_reviewer(rol: str, stap: dict, uitvoer: str, config: dict) -> str:
    """Raadpleeg de reviewer-rol; retourneer geslaagd/gefaald/onduidelijk.

    Technische twijfel (time-out, crash, onzin) is altijd 'onduidelijk':
    bij twijfel roep je de mens, nooit een gok (spec §9).
    """
    roldef = (config or {}).get("rollen", {}).get(rol)
    if not roldef:
        return "onduidelijk"
    payload = json.dumps({"stap": stap, "uitvoer": uitvoer}, ensure_ascii=False)
    try:
        if roldef["type"] == "cli":
            # stdin-only transport: de uitvoer is onvoorspelbare inhoud en mag
            # nooit in een shell-string terechtkomen (review-les: geen interpolatie).
            # 'commando' is een argv-lijst (of één string via shlex gesplitst),
            # uitgevoerd met shell=False.
            import shlex
            commando = roldef["commando"]
            argv = commando if isinstance(commando, list) else shlex.split(commando)
            resultaat = subprocess.run(
                argv, input=payload, shell=False,
                capture_output=True, text=True, timeout=60)
            return _vertaal_antwoord(resultaat.stdout)
        # http
        verzoek = urllib.request.Request(
            roldef["url"], data=payload.encode("utf-8"),
            headers={"Content-Type": "application/json"}, method="POST")
        with urllib.request.urlopen(verzoek, timeout=10) as r:
            if r.status != roldef.get("verwacht_status", 200):
                return "onduidelijk"
            antwoord = json.loads(r.read().decode("utf-8"))
            oordeel = antwoord.get("oordeel")
            return oordeel if oordeel in _OORDELEN else "onduidelijk"
    except Exception:
        return "onduidelijk"
