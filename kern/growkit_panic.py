# kern/growkit_panic.py — de PANIC-knop
# Pauzeert alles, logt append-only, herstelt nooit automatisch.
# De Baas kan alleen via deze knop alles still zetten; herstart is handmatig.
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

STATUS_BESTAND = "panic_status.json"


def _nu() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _status_pad(doel: Path) -> Path:
    return doel / STATUS_BESTAND


def _log_panic(logboek: Path, status: str, reden: str) -> None:
    """Append-only: elke panic/herstel is een nieuwe entry, nooit een verwijderde."""
    entries = []
    if logboek.exists():
        entries = json.loads(logboek.read_text(encoding="utf-8"))
    entries.append({
        "stap": "PANIC",
        "status": status,
        "bewijs": reden,
        "tijdstip": _nu(),
    })
    logboek.write_text(
        json.dumps(entries, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def activeer_panic(doel: Path, reden: str) -> dict:
    """Activeer de PANIC-knop: schrijf status-bestand + append-only log-entry.

    De motor zelf controleert panic_status.json vóór elke stap; actieve panic
    betekent: geen nieuwe stappen, geen merges, geen pushes tot herstel.
    """
    doel = Path(doel)
    doel.mkdir(parents=True, exist_ok=True)
    payload = {
        "actief": True,
        "reden": reden,
        "tijdstip": _nu(),
    }
    _status_pad(doel).write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    logboek = doel / "logboek.json"
    _log_panic(logboek, "panic_actief", reden)
    return payload


def herstel_na_panic(doel: Path) -> dict:
    """Herstel na panic: nieuwe append-only entry, status uit. Idempotent."""
    doel = Path(doel)
    pad = _status_pad(doel)
    if not pad.exists():
        return {"actief": False, "reden": "geen panic actief", "tijdstip": _nu()}
    payload = {
        "actief": False,
        "reden": "hersteld na panic",
        "tijdstip": _nu(),
    }
    pad.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    logboek = doel / "logboek.json"
    _log_panic(logboek, "panic_hersteld", "herstel na panic")
    return payload


def is_panic_actief(doel: Path) -> bool:
    """De motor roept dit vóór elke stap. Actieve panic = geen nieuwe stappen."""
    pad = _status_pad(Path(doel))
    if not pad.exists():
        return False
    try:
        data = json.loads(pad.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return False
    return bool(data.get("actief", False))


def lees_status(doel: Path) -> dict:
    """Lees de huidige panic-status (voor rapportage en de GUI-knop)."""
    pad = _status_pad(Path(doel))
    if not pad.exists():
        return {"actief": False, "reden": "geen panic", "tijdstip": None}
    try:
        return json.loads(pad.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {"actief": False, "reden": "status-bestand onleesbaar", "tijdstip": None}
