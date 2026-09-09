"""growkit_antwoorden — Slice A: agent-antwoorden lezen (voor de Grow Kit-app).

Bron: /root/.hermes/agenttaken/<agent>/antwoorden/<taak_id>.json op de VPS.
De module volgt het adapter-patroon: bestandslezer en map-lijster zijn injecteerbaar,
zodat de app-logica offline en deterministisch testbaar is.

Publieke functies:
- lees_antwoord(pad, lezer) — één antwoordbestand netjes inlezen
- overzicht_antwoorden(map_paden, lijster, lezer, status=None, top=None) — nieuwste eerst
"""
import json
from datetime import datetime

VERPLICHTE_VELDEN = {"taak_id", "agent", "antwoord", "afgerond_op"}


def lees_antwoord(pad: str, lezer) -> dict:
    """Lees één antwoordbestand. Corrupt JSON of missende velden = ValueError."""
    raw = lezer(pad)
    try:
        d = json.loads(raw)
    except (json.JSONDecodeError, TypeError) as e:
        raise ValueError(f"corrupt antwoordbestand {pad}: {e}") from e
    if not isinstance(d, dict) or not VERPLICHTE_VELDEN.issubset(d):
        ontbrekend = VERPLICHTE_VELDEN - set(d if isinstance(d, dict) else {})
        raise ValueError(f"antwoordbestand mist velden {ontbrekend}: {pad}")
    return d


def overzicht_antwoorden(map_paden: list[str], lijster, lezer,
                         status: str | None = None, top: int | None = None) -> list[dict]:
    """Verzamel antwoorden over meerdere agent-mappen, nieuwste eerst.

    Corrupte bestanden worden overgeslagen (met reden weggeschreven in 'fout'-veld
    zou dubbel zijn — simpelweg negeren houdt het overzicht bruikbaar).
    status-filter: substring-match op het status-veld (bv. 'gefaald', 'afgerond').
    """
    resultaten = []
    for map_pad in map_paden:
        for bestand in lijster(map_pad):
            if not bestand.endswith(".json"):
                continue
            try:
                d = lees_antwoord(bestand, lezer)
            except (ValueError, FileNotFoundError):
                continue
            if status and status not in str(d.get("status", "")):
                continue
            resultaten.append(d)
    resultaten.sort(key=lambda d: str(d.get("afgerond_op", "")), reverse=True)
    return resultaten[:top] if top else resultaten
