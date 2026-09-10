"""Tip-rotor op het Thuis-scherm (ZT-5, plan 2026-09-10).

Contract van `kern/growkit_tips.py`:
- `TipRotor(tips, nu)` met tips = lijst dicts (id/tekst/scherm/knop/
  conditie; conditie None of "" = generiek).
- `kies(uur, condities, gebeurtenis_hero, nu)` → tip-dict of None:
  * conditie-tips gaan vóór generieke tips;
  * een tip die vandaag al getoond is heeft kans 0 (wordt overgeslagen);
  * na 23:00 uur geen tips;
  * binnen 60 s na een gebeurtenis-hero géén tip.
- `volgende(uur, condities, gebeurtenis_hero, nu)` → volgende tip,
  max 3 wissels per sessie; daarna None.
- `teller_tekst(tekst)` → tekst zonder [N]-placeholders, voor de
  lengte-teller in de UI.
- `app/Resources/tips.json`: 12 tips, vast formaat
  id/tekst/scherm/knop/conditie.

Kern-logica testbaar zonder Swift; de SwiftUI-wiring (HomeView) is
build-bewijs in de slice zelf.
"""
import json
import unittest
from datetime import datetime
from pathlib import Path
import sys

REPO = Path(__file__).parent.parent
sys.path.insert(0, str(REPO / "kern"))

from growkit_tips import TipRotor, teller_tekst  # noqa: E402

NU = datetime(2026, 9, 10, 14, 0, 0)

TIPS = [
    {"id": "c1", "tekst": "Salotip: zet de drempel hoger.",
     "scherm": "saldo", "knop": "Naar saldo", "conditie": "saldo_laag"},
    {"id": "g1", "tekst": "Wist je dat je taken kunt plannen?",
     "scherm": "taken", "knop": "Naar taken", "conditie": None},
    {"id": "g2", "tekst": "Wist je dat je memo's kunt dictaat?",
     "scherm": "memo", "knop": "Naar memo", "conditie": None},
]


class TestConditieVoorGeneriek(unittest.TestCase):
    def test_conditie_tip_wint(self):
        r = TipRotor(TIPS, nu=NU)
        t = r.kies(14, condities={"saldo_laag"}, gebeurtenis_hero=False, nu=NU)
        self.assertEqual(t["id"], "c1")

    def test_geen_conditie_dan_generiek(self):
        r = TipRotor(TIPS, nu=NU)
        t = r.kies(14, condities=set(), gebeurtenis_hero=False, nu=NU)
        self.assertEqual(t["id"], "g1")

    def test_conditie_niet_waar_dan_generiek(self):
        r = TipRotor(TIPS, nu=NU)
        t = r.kies(14, condities={"andere"}, gebeurtenis_hero=False, nu=NU)
        self.assertEqual(t["id"], "g1")


class TestLaatstGetoond(unittest.TestCase):
    def test_kans_nul_bij_laatst_getoond_vandaag(self):
        r = TipRotor(TIPS, nu=NU)
        eerste = r.kies(14, condities=set(), gebeurtenis_hero=False, nu=NU)
        r.markeer_getoond(eerste, nu=NU)
        tweede = r.kies(14, condities=set(), gebeurtenis_hero=False, nu=NU)
        self.assertNotEqual(tweede["id"], eerste["id"])

    def test_alle_getoond_dan_none(self):
        r = TipRotor(TIPS, nu=NU)
        for t in TIPS:
            r.markeer_getoond(t, nu=NU)
        self.assertIsNone(
            r.kies(14, condities=set(), gebeurtenis_hero=False, nu=NU))


class TestAvondklok(unittest.TestCase):
    def test_geen_tips_na_23(self):
        r = TipRotor(TIPS, nu=NU)
        self.assertIsNone(
            r.kies(23, condities=set(), gebeurtenis_hero=False, nu=NU))
        self.assertIsNone(
            r.kies(0, condities=set(), gebeurtenis_hero=False, nu=NU))

    def test_wel_tips_voor_23(self):
        r = TipRotor(TIPS, nu=NU)
        self.assertIsNotNone(
            r.kies(22, condities=set(), gebeurtenis_hero=False, nu=NU))


class TestGebeurtenisHero(unittest.TestCase):
    def test_geen_tip_binnen_60s_na_hero(self):
        r = TipRotor(TIPS, nu=NU)
        r.markeer_hero(nu=NU)
        net_na = datetime(2026, 9, 10, 14, 0, 30)
        self.assertIsNone(
            r.kies(14, condities=set(), gebeurtenis_hero=True, nu=net_na))

    def test_wel_tip_na_60s(self):
        r = TipRotor(TIPS, nu=NU)
        r.markeer_hero(nu=NU)
        later = datetime(2026, 9, 10, 14, 1, 1)
        t = r.kies(14, condities=set(), gebeurtenis_hero=True, nu=later)
        self.assertIsNotNone(t)

    def test_geen_tips_tijdens_hero_actief(self):
        # Zolang de hero-gebeurtenis zelf zichtbaar is: geen tip.
        r = TipRotor(TIPS, nu=NU)
        self.assertIsNone(
            r.kies(14, condities=set(), gebeurtenis_hero=True, nu=NU))


class TestTellers(unittest.TestCase):
    def test_placeholders_uit_teller(self):
        # [N]-placeholders tellen niet mee voor de lengte-teller.
        self.assertEqual(teller_tekst("Er liggen [N] taken klaar."),
                         "Er liggen  taken klaar.")

    def test_placeholders_meerdere(self):
        self.assertEqual(teller_tekst("[N] + [N] = [N]"), " +  = ")


class TestVolgendeWissels(unittest.TestCase):
    def _drie(self):
        return [
            {"id": f"g{i}", "tekst": f"Tip {i}", "scherm": "thuis",
             "knop": "Ok", "conditie": None}
            for i in range(5)
        ]

    def test_max_3_wissels(self):
        r = TipRotor(self._drie(), nu=NU)
        eerste = r.kies(14, condities=set(), gebeurtenis_hero=False, nu=NU)
        self.assertIsNotNone(eerste)
        wissels = []
        for _ in range(5):
            wissels.append(
                r.volgende(14, condities=set(), gebeurtenis_hero=False,
                           nu=NU))
        # Elke wissel geeft een NIEUWE tip (getoond-vandaag heeft kans 0),
        # en na 3 wissels stopt de rotor.
        self.assertTrue(all(w is not None for w in wissels[:3]))
        self.assertIsNone(wissels[3])
        self.assertIsNone(wissels[4])
        ids = [w["id"] for w in wissels[:3]]
        self.assertEqual(len(set(ids)), 3)
        self.assertNotIn(eerste["id"], ids)


class TestTipsData(unittest.TestCase):
    def test_tips_json_bestaat_en_formaat(self):
        pad = REPO / "app" / "Resources" / "tips.json"
        self.assertTrue(pad.exists(), "app/Resources/tips.json ontbreekt")
        data = json.loads(pad.read_text(encoding="utf-8"))
        self.assertEqual(len(data), 12)
        for tip in data:
            self.assertIn("id", tip)
            self.assertIn("tekst", tip)
            self.assertIn("scherm", tip)
            self.assertIn("knop", tip)
            self.assertIn("conditie", tip)
            self.assertTrue(tip["tekst"].strip())


if __name__ == "__main__":
    unittest.main()
