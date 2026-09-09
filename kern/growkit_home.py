"""Dynamische hero op het Thuis-scherm (ZT-3).

Begroeting per dagdeel + max 1 gebeurtenis-variant op vaste prioriteit:
onbehandelde goedkeuringen > saldo-onder-drempel > nachtelijke bouwronde.
Geen gebeurtenis geldig → None; de SwiftUI-hero toont dan de kale begroeting.
Kern-logica zonder Swift, testbaar via tests/test_home_hero.py.
"""
from typing import Optional

def begroeting(uur: int) -> str:
    """Begroeting per dagdeel; 0-4 uur → morgen-tekst (nachtbug)."""
    if 0 <= uur <= 4:
        return "Goedemorgen"
    if 5 <= uur <= 11:
        return "Goedemorgen"
    if 12 <= uur <= 17:
        return "Goedemiddag"
    return "Goedenavond"


def hero_variant(
    goodkeuringen: int,
    saldo: float,
    saldo_drempel: float,
    nachtronde: bool,
) -> Optional[str]:
    """Kies max 1 gebeurtenis-variant op prioriteit, of None."""
    if goodkeuringen > 0:
        return "goedkeuringen"
    if saldo < saldo_drempel:
        return "saldo"
    if nachtronde:
        return "nachtronde"
    return None


_VARIANT_TEKST = {
    "goedkeuringen": "Er liggen {n} onbehandelde goedkeuringen klaar.",
    "saldo": "Je saldo zit onder de drempel.",
    "nachtronde": "De nachtelijke bouwronde heeft nieuws.",
}


def hero_tekst(
    uur: int,
    goodkeuringen: int = 0,
    saldo: float = 0.0,
    saldo_drempel: float = 0.0,
    nachtronde: bool = False,
) -> str:
    """Hero-tekst: gebeurtenis-variant wint, anders de kale begroeting."""
    variant = hero_variant(goodkeuringen, saldo, saldo_drempel, nachtronde)
    if variant == "goedkeuringen":
        return _VARIANT_TEKST[variant].format(n=goodkeuringen)
    if variant is not None:
        return _VARIANT_TEKST[variant]
    return begroeting(uur)
