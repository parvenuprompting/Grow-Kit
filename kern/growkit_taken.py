"""GrowKit takenlijst — taken bestaan alleen mét bewijs (spec §7).

Elke taak volgt het stappen-schema (§4): zonder `bewijs` met `type` bestaat
de taak niet (poort-regel). Gebeurtenissen worden append-only gelogd.
"""
import datetime
import json
from pathlib import Path

from kern.growkit_poort import beoordeel_invoer


def laad_taken(pad: Path) -> list[dict]:
    """Lees de takenlijst; afwezig bestand is een lege lijst."""
    if not pad.exists():
        return []
    try:
        return json.loads(pad.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise ValueError(
            f"takenlijst {pad} is corrupt — roep de mens, nooit auto-repareren: {e}"
        ) from e


def valideer_taak(taak: dict) -> list[str]:
    """Poort-regel (§11, taak-type): geen bewijs-check → de taak bestaat niet."""
    bevindingen = []
    if not taak.get("id"):
        bevindingen.append("taak zonder id — ongeldig volgens het stappen-schema (§4)")
    ok, tekst, _ = beoordeel_invoer(taak, "taak")
    if not ok:
        bevindingen.append(tekst)
    return bevindingen


def log_taakgebeurtenis(pad: Path, taak_id: str, status: str, bewijs: str) -> None:
    """Append-only gebeurtenis per taak; bestaande entries blijven staan."""
    pad.parent.mkdir(parents=True, exist_ok=True)
    entries = json.loads(pad.read_text(encoding="utf-8")) if pad.exists() else []
    entries.append({
        "type": "taak",
        "taak": taak_id,
        "status": status,
        "bewijs": bewijs,
        "tijdstip": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
    })
    pad.write_text(json.dumps(entries, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
