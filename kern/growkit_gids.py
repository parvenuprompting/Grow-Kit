"""AI Gids-kern — kerninzichten uit Tiëndo's Google Drive-documenten.

De gids laadt een statische JSON (kern/data/ai-gids.json) met
gedistilleerde kerninzichten, elk met bronvermelding. Zoeken werkt over
titel, inhoud en bron. De JSON is de bron van waarheid; deze module is
de leeslaag voor de adapter en de app.

Huisregel uit de brondocumenten: een feit zonder bron is een aanname —
elk inzicht in de gids noemt waar het vandaan komt.
"""
from __future__ import annotations

import json
from pathlib import Path

_DATA_PAD = Path(__file__).parent / "data" / "ai-gids.json"
_cache: dict | None = None


def laad() -> dict:
    """Laad de gids (gecached). RuntimeError bij ontbrekend/corrupt bestand."""
    global _cache
    if _cache is not None:
        return _cache
    if not _DATA_PAD.is_file():
        raise RuntimeError(f"AI Gids-data ontbreekt: {_DATA_PAD}")
    try:
        _cache = json.loads(_DATA_PAD.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise RuntimeError(f"AI Gids-data is corrupt: {e}") from e
    return _cache


def themas() -> list[dict]:
    """Alle thema's met hun inzichten, in vastgestelde volgorde."""
    return laad()["thema's"]


def alle_inzichten() -> list[dict]:
    """Vlakke lijst van alle inzichten (met thema erbij)."""
    resultaat: list[dict] = []
    for thema in themas():
        for i in thema["inzichten"]:
            resultaat.append({**i, "thema": thema["thema"]})
    return resultaat


def zoek(term: str) -> list[dict]:
    """Zoek inzichten op titel, inhoud of bron (hoofdletterongevoelig)."""
    term = term.strip().lower()
    if not term:
        return []
    return [
        i for i in alle_inzichten()
        if term in i["titel"].lower()
        or term in i["inhoud"].lower()
        or term in i["bron"].lower()
    ]


def bronnen() -> list[str]:
    """De bron-documenten waarop de gids rust."""
    return laad().get("bronnen", [])
