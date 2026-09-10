"""GrowKit tip-rotor (ZT-5) — één tip, met regels.

Regels (plan 2026-09-10, ZT-5):
- conditie-tips gaan vóór generieke tips;
- een tip die vandaag al getoond is heeft kans nul;
- geen tips na 23:00 (de avond is van de rust);
- geen tip binnen 60 s na een gebeurtenis-hero;
- [N]-placeholders in de tekst worden ingevuld uit de tellers;
- maximaal 3 'volgende'-wissels per sessie.

Tijd en toeval zijn geïnjecteerd (nu, keuze): deterministisch testbaar.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any

VOLGENDE_MAX = 3          # max 'volgende'-wissels per sessie
STILTE_NA_GEBEURTENIS = 60  # seconden geen tip na gebeurtenis-hero
AVONDGRENS_UUR = 23       # na 23:00 geen tips


def mag_wisselen(aantal_wissels: int) -> bool:
    """Mag de gebruiker nog een 'volgende'-wissel doen deze sessie?"""
    return aantal_wissels < VOLGENDE_MAX


def _voldoet(conditie: dict[str, Any] | None, tellers: dict[str, int]) -> bool:
    if not conditie:
        return True
    veld = conditie.get("veld")
    minimum = conditie.get("min", 0)
    return tellers.get(veld, 0) >= minimum


def _vul_placeholders(tekst: str, tellers: dict[str, int]) -> str:
    """Vervang [veld] door de tellerwaarde; [N] door de eerste teller."""
    uit = tekst
    for veld, waarde in tellers.items():
        uit = uit.replace(f"[{veld}]", str(waarde))
    if "[N]" in uit and tellers:
        uit = uit.replace("[N]", str(next(iter(tellers.values()))))
    return uit


def kies_tip(tips: list[dict], *, nu: datetime | None = None,
             tellers: dict[str, int] | None = None,
             laatst_getoond: dict[str, date] | None = None,
             gebeurtenis_op: datetime | None = None,
             keuze: Any = None) -> dict | None:
    """Kies één tip conform de regels; None betekent: vandaag geen tip."""
    nu = nu or datetime.now()
    tellers = tellers or {}
    laatst_getoond = laatst_getoond or {}

    if nu.hour >= AVONDGRENS_UUR:
        return None
    if gebeurtenis_op is not None and (nu - gebeurtenis_op).total_seconds() < STILTE_NA_GEBEURTENIS:
        return None
    kandidaten = [t for t in tips if laatst_getoond.get(t["id"]) != nu.date()]
    if not kandidaten:
        return None

    conditie_tips = [t for t in kandidaten
                     if t.get("conditie") and _voldoet(t["conditie"], tellers)]
    if conditie_tips:
        kandidaten = conditie_tips
    elif any(t.get("conditie") for t in kandidaten):
        # condities bestaan maar geen enkele is voldaan: alleen generieke
        generiek = [t for t in kandidaten if not t.get("conditie")]
        if not generiek:
            return None
        kandidaten = generiek

    if keuze is not None:
        tip = keuze.choice(kandidaten)
    else:
        import random
        tip = random.choice(kandidaten)

    getoond = dict(tip)
    getoond["tekst"] = _vul_placeholders(tip.get("tekst", ""), tellers)
    return getoond
