"""Tip-rotor op het Thuis-scherm (ZT-5, plan 2026-09-10).

Rotates kleine tips onder de hero op het Thuis-scherm. Regels:
- conditie-tips gaan vóór generieke tips;
- een tip die vandaag al getoond is heeft kans 0;
- na 23:00 geen tips (avondklok);
- binnen 60 s na een gebeurtenis-hero géén tip;
- max 3 "volgende"-wissels per sessie.

Kern-logica zonder Swift, getest via tests/test_tips_rotor.py. De
SwiftUI-wiring staat in HomeView (build-bewijs).
"""
from datetime import datetime, timedelta
from typing import Optional

AVONDKLOK_UUR = 23          # vanaf dit uur geen tips
HERO_RUSTSEC = 60           # seconden rust na een gebeurtenis-hero
MAX_WISSELS_PER_SESSIE = 3  # max "volgende"-wissels per sessie


def teller_tekst(tekst: str) -> str:
    """Tekst zonder [N]-placeholders — voor de lengte-teller in de UI."""
    resultaat = []
    in_placeholder = False
    for teken in tekst:
        if teken == "[":
            in_placeholder = True
            continue
        if teken == "]":
            in_placeholder = False
            continue
        if not in_placeholder:
            resultaat.append(teken)
    return "".join(resultaat)


class TipRotor:
    """Kiest en wisselt tips volgens de ZT-5-regels."""

    def __init__(self, tips: list, nu: Optional[datetime] = None):
        self._tips = list(tips)
        self._nu = nu
        self._getoond_vandaag: set = set()   # id's getoond vandaag
        self._getoond_dag: Optional[str] = None
        self._hero_moment: Optional[datetime] = None
        self._wissels = 0
        self._huidige: Optional[dict] = None
        self._volgorde: list = []            # resterende kandidaten

    # ---------- intern ----------

    @staticmethod
    def _dag(nu: datetime) -> str:
        return nu.strftime("%Y-%m-%d")

    def _is_conditie(self, tip: dict) -> bool:
        return bool(tip.get("conditie"))

    def _kandidaten(self, condities: set) -> list:
        """Conditie-tips (waar) eerst, dan generiek; getoonde vandaag weg."""
        conditie = [
            t for t in self._tips
            if self._is_conditie(t) and t["conditie"] in condities
        ]
        generiek = [t for t in self._tips if not self._is_conditie(t)]
        return [t for t in conditie + generiek
                if t["id"] not in self._getoond_vandaag]

    # ---------- publiek ----------

    def markeer_getoond(self, tip: dict, nu: Optional[datetime] = None) -> None:
        """Registreer dat een tip getoond is (kans 0 tot eind van de dag)."""
        nu = nu or self._nu
        dag = self._dag(nu)
        if self._getoond_dag != dag:
            self._getoond_vandaag = set()
            self._getoond_dag = dag
        self._getoond_vandaag.add(tip["id"])

    def markeer_hero(self, nu: Optional[datetime] = None) -> None:
        """Registreer dat er een gebeurtenis-hero is getoond."""
        self._hero_moment = nu or self._nu

    def kies(
        self,
        uur: int,
        condities: set = None,
        gebeurtenis_hero: bool = False,
        nu: Optional[datetime] = None,
    ) -> Optional[dict]:
        """Kies de eerste geldige tip, of None volgens de regels."""
        condities = condities or set()
        nu = nu or self._nu
        if nu is None:
            raise ValueError("TipRotor heeft een nu-moment nodig")

        # Avondklok: vanaf 23:00 en in de nacht (0-4 uur) geen tips.
        if uur >= AVONDKLOK_UUR or uur <= 4:
            return None

        # Gebeurtenis-hero: geen tip tijdens de hero en 60 s erna.
        if gebeurtenis_hero:
            if self._hero_moment is None:
                self._hero_moment = nu
            if (nu - self._hero_moment).total_seconds() < HERO_RUSTSEC:
                return None

        kandidaten = self._kandidaten(condities)
        if not kandidaten:
            return None
        gekozen = kandidaten[0]
        self._huidige = gekozen
        self._volgorde = kandidaten[1:]
        self.markeer_getoond(gekozen, nu=nu)
        return gekozen

    def volgende(
        self,
        uur: int,
        condities: set = None,
        gebeurtenis_hero: bool = False,
        nu: Optional[datetime] = None,
    ) -> Optional[dict]:
        """Handmatige 'volgende'-wissel; max 3 per sessie."""
        condities = condities or set()
        nu = nu or self._nu
        if uur >= AVONDKLOK_UUR or uur <= 4:
            return None
        if self._wissels >= MAX_WISSELS_PER_SESSIE:
            return None
        if self._huidige is None:
            return self.kies(uur, condities, gebeurtenis_hero, nu)

        # Ververs de wachtrij: getoonde tips vallen weg (kans 0 vandaag).
        zelfde_conditie = (
            [t for t in self._volgorde if self._is_conditie(t)] +
            [t for t in self._volgorde if not self._is_conditie(t)])
        resterende = [t for t in zelfde_conditie
                      if t["id"] not in self._getoond_vandaag]
        if not resterende:
            # Hergebruik de volledige pool; vandaag-getoonde blijven kans 0,
            # dus zonder restanten is er niets nieuws.
            return None
        gekozen = resterende[0]
        self._volgorde = resterende[1:] + [
            t for t in resterende[1:] if t not in self._volgorde]
        self._huidige = gekozen
        self._wissels += 1
        self.markeer_getoond(gekozen, nu=nu)
        return gekozen
