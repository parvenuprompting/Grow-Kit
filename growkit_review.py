"""GrowKit review-laag — provider-agnostische reviewer-rollen (spec §9, §12.5).

Rollen, geen leveranciers: nergens een modelnaam in code of defaults.
Machine-bewijs blijft eerste keus; de reviewer vermindert mens-inzet en
vervangt de mens niet.
"""
import json
from pathlib import Path

# Verboden velden: leveranciers-binding is een schema-fout (§12.5).
_VERBODEN_VELDEN = ("model", "provider", "leverancier")
_GELDIGE_TYPES = {"http", "cli"}


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
