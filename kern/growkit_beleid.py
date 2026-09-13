#!/usr/bin/env python3
"""GrowKit ThreatLocker politiek-laag per agent (slice S12).

Elke agent in het familie-register krijgt een beleidsobject: mag/niet-mag
per actiesoort. Gesloten standaard: wat niet expliciet is toegestaan,
mag niet. De controle gebeurt vóór uitvoering — een weigering is een
antwoord vóórdat er iets gebeurt, nooit een rapport erna.

Deze module levert alleen feiten en beslissingen. Het register hier is
beleid (zoals het familie-register), geen config: het verandert via een
expliciete wijziging van dit bestand, niet via een adapter-aanroep.
"""
from typing import Literal

Actie = Literal["lezen", "schrijven", "netwerk", "wissen", "systeem"]

# Beleid per agent (gesloten standaard — alles wat niet hier staat: nee).
# Genius (observer) krijgt bewust GEEN acties: de governor-wet zegt dat
# de observer observeert, onthoudt en meldt — voert niets uit.
BELEID: dict[str, dict] = {
    "KairOS":  {"toegestaan": ["lezen", "schrijven", "netwerk"]},
    "Riri":    {"toegestaan": ["lezen", "netwerk"]},
    "Vigil":   {"toegestaan": ["lezen", "schrijven", "netwerk"]},
    "Libra":   {"toegestaan": ["lezen"]},
    "Memoria": {"toegestaan": ["lezen", "schrijven"]},
    "Codex":   {"toegestaan": ["lezen", "schrijven"]},
    "Genius":  {"toegestaan": []},  # observer: voert niets uit
}

# Acties die NOOIT door beleid open mogen staan — wet boven beleid.
NOOIT = {"wissen"}


def beleid_voor(agent: str) -> dict:
    """Het beleidsobject van een agent; onbekende agent = leeg beleid."""
    naam = (agent or "").strip().lower()
    for a, b in BELEID.items():
        if a.lower() == naam:
            return {"agent": a, "toegestaan": list(b["toegestaan"])}
    return {"agent": agent, "toegestaan": []}


def alle_beleidsobjecten() -> list[dict]:
    return [{"agent": a, "toegestaan": list(b["toegestaan"])}
            for a, b in BELEID.items()]


def toegestaan(agent: str, actie: str) -> bool:
    """Gesloten standaard + de nooit-mag-wet."""
    if actie in NOOIT:
        return False
    return actie in beleid_voor(agent)["toegestaan"]


def controleer(agent: str, actie: str) -> dict:
    """De weigering komt vóór uitvoering, in mensentaal."""
    if actie in NOOIT:
        return {"ok": False, "weigering":
                f"'{actie}' mag niemand in deze familie ooit — geen beleid "
                "kan dat openen."}
    if toegestaan(agent, actie):
        return {"ok": True, "weigering": None}
    b = beleid_voor(agent)
    return {"ok": False, "weigering":
            f"Geweigerd vóór uitvoering: '{agent}' mag '{actie}' niet — "
            f"staat niet in zijn beleid (toegestaan: "
            f"{', '.join(b['toegestaan']) or 'niets'}). Binnenhalen bij de "
            "Baas, niet bij de agent."}