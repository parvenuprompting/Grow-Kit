"""growkit_panic_crons — Slice C: PANIC geldt ook voor zaadjes-crons.

De bestaande PANIC-knop (growkit_panic) pauzeert Grow Kit-agents. Deze module
breidt hetzelfde signaal uit naar de wakers van Het Zaad: elke cron-script roept
waker_poort() aan vóór zijn werk; actieve panic = netjes stoppen met logregel.

Status-bestand: <wakers-pad>/panic-status.json (zelfde formaat als growkit_panic).
Stilte-log: <wakers-pad>/waker-stilte.log (append-only, wie/ wanneer).
"""
import json
from datetime import datetime, timezone
from pathlib import Path

STATUS_BESTAND = "panic-status.json"
STILTE_LOG = "waker-stilte.log"


def _nu() -> str:
    return datetime.now(timezone.utc).isoformat()


def activeer_panic(wakers_pad: Path, reden: str) -> dict:
    """Activeer panic voor de wakers (delegatie naar zelfde formaat als growkit_panic)."""
    wakers_pad = Path(wakers_pad)
    wakers_pad.mkdir(parents=True, exist_ok=True)
    payload = {"actief": True, "reden": reden, "tijdstip": _nu()}
    (wakers_pad / STATUS_BESTAND).write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return payload


def herstel_na_panic(wakers_pad: Path) -> dict:
    """Beëindig panic (alleen na expliciete actie van de Baas)."""
    wakers_pad = Path(wakers_pad)
    payload = {"actief": False, "reden": "hersteld", "tijdstip": _nu()}
    (wakers_pad / STATUS_BESTAND).write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return payload


def is_panic_actief(wakers_pad: Path) -> bool:
    """Corrupt of ontbrekend statusbestand = géén panic (fail-open: wakers blijven draaien).
    Bewuste keuze: panic is een bewuste menselijke stop, geen fragiele toestand."""
    bestand = Path(wakers_pad) / STATUS_BESTAND
    if not bestand.exists():
        return False
    try:
        d = json.loads(bestand.read_text())
    except (json.JSONDecodeError, OSError):
        return False
    return bool(d.get("actief"))


def waker_poort(wakers_pad: Path, naam: str) -> tuple[bool, str]:
    """Elke waker roept dit vóór zijn run. Terug: (mag_doorgaan, reden)."""
    wakers_pad = Path(wakers_pad)
    if is_panic_actief(wakers_pad):
        reden = f"panic actief — waker '{naam}' stopt netjes"
        with open(wakers_pad / STILTE_LOG, "a", encoding="utf-8") as f:
            f.write(f"{_nu()} {naam}: {reden}\n")
        return False, reden
    return True, ""
