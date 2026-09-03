"""GrowKit ratificatie — mens-momenten in bulk (spec §9).

Eén bron voor loop.py en de adapter: verzamelen van wachtende stappen en het
append-only verwerken van bulk-beslissingen (geratificeerd / herziening_nodig
mét reden en doorloop-vermelding). Geen auto-rollback; de mens blijft curator.
"""
import datetime
import json
from pathlib import Path


def _nu() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")


def wacht_ratificatie_stappen(logboek: Path) -> list[str]:
    """Stappen waarvan de laatst gelogde status review_ok_wacht_ratificatie is,
    in volgorde van eerste verschijning."""
    laatste: dict[str, str] = {}
    volgorde: list[str] = []
    if not logboek.exists():
        return []
    for entry in json.loads(logboek.read_text(encoding="utf-8")):
        sid = entry.get("stap")
        if not sid:
            continue
        if sid not in laatste:
            volgorde.append(sid)
        laatste[sid] = entry.get("status")
    return [sid for sid in volgorde if laatste[sid] == "review_ok_wacht_ratificatie"]


def ratificeer_bulk(logboek: Path, geratificeer: list[str],
                    afkeur: list[dict] | None = None) -> list[dict]:
    """Append-only vervolg-entries: 'geratificeerd' voor de meegegeven stappen,
    'herziening_nodig' (met reden + doorloop-vermelding) voor de afkeur-entries.

    afkeur: [{"stap_id": ..., "reden": ...}] — geen auto-rollback; het
    origineel blijft in het logboek. Retourneert de geschreven entries.
    """
    entries = json.loads(logboek.read_text(encoding="utf-8")) if logboek.exists() else []
    geschreven: list[dict] = []
    for sid in geratificeer:
        entry = {"type": "ratificatie", "stap": sid, "status": "geratificeerd",
                 "bewijs": "bulk-ratificatie door de mens (§9)", "tijdstip": _nu()}
        entries.append(entry)
        geschreven.append(entry)
    for afkeuring in (afkeur or []):
        sid = afkeuring["stap_id"]
        reden = afkeuring["reden"]
        laatste_index = max(i for i, e in enumerate(entries) if e.get("stap") == sid)
        latere = []
        for e in entries[laatste_index + 1:]:
            sid2 = e.get("stap")
            if sid2 and sid2 != sid and e.get("type") not in ("mijlpaal", "ratificatie") \
                    and sid2 not in latere:
                latere.append(sid2)
        vermelding = (f"{reden}; afgekeurd bij bulk-ratificatie; latere stappen "
                      f"in het logboek: {', '.join(latere) if latere else 'geen'}")
        entry = {"type": "ratificatie", "stap": sid, "status": "herziening_nodig",
                 "bewijs": vermelding, "tijdstip": _nu()}
        entries.append(entry)
        geschreven.append(entry)
    logboek.write_text(json.dumps(entries, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return geschreven
