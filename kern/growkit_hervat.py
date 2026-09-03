"""GrowKit state-reconstructie — herstart uit het logboek (spec §7, §11.4).

Bij crash of nieuwe sessie bepaalt reconstructie() per stap wat er met de
restdraai gebeurt. Geen blind herdraaien: een niet-idempotent geslaagde stap
wordt nooit opnieuw uitgevoerd; twijfel (onbekende status) gaat naar de mens
als heraanbieden, nooit stilzwijgend overgeslagen. Corrupt logboek → mens,
nooit auto-reparatie.
"""
import json
from pathlib import Path

_OVERSLAAN = ("geslaagd", "review_ok_wacht_ratificatie")
_HERAANBIEDEN = ("wacht_op_mens", "gefaald", "herziening_nodig")


def _laatste_statussen(entries: list[dict]) -> dict[str, dict]:
    """Laatste append-only entry per stap-id wint; mijlpaal-entries apart."""
    laatste: dict[str, dict] = {}
    mijlpalen = [e for e in entries if e.get("type") == "mijlpaal" and e.get("status") == "bevestigd"]
    for entry in entries:
        if entry.get("stap"):
            laatste[entry["stap"]] = entry
    return laatste, mijlpalen


def reconstructie(logboek: Path, profiel: dict) -> dict:
    """Logboek + profiel → beslissingen per stap + herstartpunt.

    Retourneert bij corrupt JSON {"fout": "corrupt_logboek"} — crashen of
    repareren is nooit aan de orde; de mens beslist.
    """
    if not logboek.exists():
        entries: list[dict] = []
    else:
        try:
            entries = json.loads(logboek.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return {"fout": "corrupt_logboek", "herstartpunt": "start"}

    laatste, mijlpalen = _laatste_statussen(entries)
    stappen: dict[str, dict] = {}
    for stap in profiel.get("stappen", []):
        sid = stap["id"]
        entry = laatste.get(sid)
        if entry is None:
            stappen[sid] = {"beslissing": "uitvoeren", "laatste_status": None, "noot": None}
            continue
        status = entry.get("status")
        if status == "geslaagd":
            noot = None
            if not stap.get("idempotent", True):
                noot = "niet-idempotent — nooit herdraaien; bewijs staat in het logboek"
            stappen[sid] = {"beslissing": "overslaan", "laatste_status": status, "noot": noot}
        elif status == "review_ok_wacht_ratificatie":
            stappen[sid] = {"beslissing": "overslaan",
                            "laatste_status": status,
                            "noot": "wacht op de bulk-ratificatie — geen herdraai, geen her-review"}
        elif status in _HERAANBIEDEN:
            stappen[sid] = {"beslissing": "heraanbieden", "laatste_status": status, "noot": None}
        else:
            stappen[sid] = {"beslissing": "heraanbieden", "laatste_status": status,
                            "noot": f"onbekende status {status!r} — de mens beslist"}

    if mijlpalen:
        laatste_mijlpaal = mijlpalen[-1]
        herstartpunt = {"stap": laatste_mijlpaal.get("stap", "mijlpaal-start"),
                        "tijdstip": laatste_mijlpaal.get("tijdstip")}
    else:
        herstartpunt = "start"

    return {"fout": None, "herstartpunt": herstartpunt, "stappen": stappen}
