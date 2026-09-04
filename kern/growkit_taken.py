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


def voer_taak_uit(doel: Path, taak: dict, reviewconfig=None) -> tuple[bool, list[str]]:
    """Poort → gebeurtenissen → motor: de volledige taak-uitvoering als kern.

    Geen prints — loop.py en de adapter geven zelf hun eigen vorm. Retourneert
    (geslaagd, bevindingen): bevindingen non-leeg = poort-weigering (niets
    uitgevoerd, gebeurtenis 'geweigerd' gelogd). Faalcontract van de motor
    staat onaangetast: één alternatief, dan de mens.
    """
    import json as _json
    from kern import growkit_motor

    taak_id = taak.get("id", "onbekend")
    taken_logboek = doel / "taken-logboek.json"
    bevindingen = valideer_taak(taak)
    if bevindingen:
        log_taakgebeurtenis(taken_logboek, taak_id, "geweigerd",
                            "poort-weigering: " + "; ".join(bevindingen))
        return False, bevindingen
    log_taakgebeurtenis(taken_logboek, taak_id, "bezig", "motor-start")
    boom_logboek = doel / "logboek.json"
    if not boom_logboek.exists():
        boom_logboek.write_text("[]", encoding="utf-8")
    geslaagd = growkit_motor.voer_uit({"profiel": f"taak-{taak_id}", "stappen": [taak]},
                                      doel, boom_logboek, None, reviewconfig=reviewconfig,
                                      vangnet=growkit_motor.vangnet_pad_voor(doel))
    if geslaagd:
        log_taakgebeurtenis(taken_logboek, taak_id, "geslaagd", "machine-bewijs (§3)")
    else:
        log_taakgebeurtenis(taken_logboek, taak_id, "gefaald", "motor-faalcontract — roep de mens")
    return geslaagd, []
