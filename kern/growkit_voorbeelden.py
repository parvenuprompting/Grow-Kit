"""Drie lokale voorbeeldopdrachten (advies 5).

Eén bron: elk voorbeeldprofiel in profielen/ draagt zijn eigen `voorbeeld`-blok
(titel, criteria, uitleg). Zo kan de lijst in de app niet losraken van het plan
dat werkelijk draait. Een voorbeeld werkt zonder VPS, zonder netwerk en zonder
sleutels — dat is hieronder ook meteen een toetsbare regel.
"""
from seed import laad_profielen

# Wat een voorbeeld nooit mag aanroepen: niets buiten deze machine.
_VERBODEN = ("ssh ", "scp ", "rsync ", "curl ", "wget ", "http://", "https://")

VOORBEELD_STATUS = "voorbeeld"


def _is_voorbeeld(profiel: dict) -> bool:
    return profiel.get("status") == VOORBEELD_STATUS and isinstance(profiel.get("voorbeeld"), dict)


def voorbeeld_profielen() -> list[dict]:
    """Alle profielen die als voorbeeld gemarkeerd zijn (ook zonder voorbeeld-blok)."""
    return [p for p in laad_profielen() if p.get("status") == VOORBEELD_STATUS]


def voorbeelden() -> list[dict]:
    """De voorbeeldopdrachten zoals de app ze toont — een lijst zonder afwijkingen."""
    uit = []
    for profiel in sorted(laad_profielen(), key=lambda p: p.get("profiel", "")):
        if not _is_voorbeeld(profiel):
            continue
        blok = profiel["voorbeeld"]
        stappen = profiel.get("stappen", [])
        uit.append({
            "id": profiel["profiel"],
            "profiel": profiel["profiel"],
            "titel": blok.get("titel", profiel["profiel"]),
            "beschrijving": profiel.get("beschrijving", ""),
            "uitleg": blok.get("uitleg", ""),
            "criteria": list(blok.get("criteria", [])),
            "stappen": len(stappen),
            "mens_stappen": len([s for s in stappen if s.get("mens_nodig")]),
        })
    return uit


def externe_aanroepen(profiel: dict) -> list[str]:
    """Commando's die iets buiten deze machine zouden opvragen.

    Hoort leeg te zijn voor elk voorbeeld: een demo die een VPS of internet nodig
    heeft, is geen demo. Retourneert de verdachte regels (leeg = in orde).
    """
    verdacht = []
    for stap in profiel.get("stappen", []):
        teksten = {"commando": str(stap.get("commando", ""))}
        alternatief = (stap.get("bij_falen") or {}).get("alternatief_commando")
        if alternatief:
            teksten["alternatief"] = str(alternatief)
        for soort, tekst in teksten.items():
            if any(verboden in tekst for verboden in _VERBODEN):
                verdacht.append(f"{stap.get('id')} ({soort}): {tekst}")
    return verdacht
