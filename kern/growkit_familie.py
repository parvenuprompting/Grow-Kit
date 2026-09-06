#!/usr/bin/env python3
"""GrowKit familie-register — de vaste cast van het harnas (slice A).

De familie is geen gouverneur-toestand maar een feitelijk register:
wie hoort erbij, wat is iemands rol, op welk platform draait hij.
De observer-rol is aan Genius — passend bij zijn aard (stille
waarnemer) en conform de gouverneur-regel dat de observer nooit
taken draagt.

Deze module levert alleen feiten. Er is geen mutatie: de familie
verandert via een expliciete wijziging van dit bestand, niet via
een adapter-aanroep. (Huisregel: het register is beleid, geen config.)
"""
from typing import Literal

Rol = Literal["uitvoering", "onderzoek", "bewaking", "kosten",
              "geheugen", "archief", "observer"]

FAMILIE: list[dict] = [
    {"naam": "KairOS",  "rol": "uitvoering", "platform": "telegram",
     "beschrijving": "Bouwer — voert uit, herstelt en coördineert het team."},
    {"naam": "Riri",    "rol": "onderzoek",  "platform": "telegram",
     "beschrijving": "Research — onderzoek, ontwerp, externe review."},
    {"naam": "Vigil",   "rol": "bewaking",   "platform": "telegram",
     "beschrijving": "Waker — infrastructuur, security, signalen."},
    {"naam": "Libra",   "rol": "kosten",     "platform": "telegram",
     "beschrijving": "Kostenbewaker — budget, pricing, verbruik."},
    {"naam": "Memoria", "rol": "geheugen",   "platform": "telegram",
     "beschrijving": "Geheugen — herinneringen, logboeken, overzicht."},
    {"naam": "Codex",   "rol": "archief",    "platform": "telegram",
     "beschrijving": "Archivaris — brein-boekingen, documenten, orde."},
    {"naam": "Genius",  "rol": "observer",   "platform": "telegram",
     "beschrijving": "Jongste — observeert en levert aan. Observer is zijn startpunt, geen vonnis: hij groeit in fasen."},
]

MAX_AGENTS = 8


def familie_register() -> dict:
    """Het register zoals de UI het mag tonen. Feiten, geen toestand."""
    return {
        "familie": [dict(a) for a in FAMILIE],
        "limieten": {"max_agents": MAX_AGENTS},
    }
