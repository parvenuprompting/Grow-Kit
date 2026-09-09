"""Dynamische hero op het Thuis-scherm (ZT-3, plan 2026-09-09).

Contract:
- `begroeting(uur)` → per dagdeel: 5-11 "Goedemorgen", 12-17
  "Goedemiddag", 18-23 "Goedenavond", 0-4 → "Goedemorgen" (nachtbug:
  na middernacht hoort de morgen-begroeting, geen "Goedenavond").
- `hero_variant` kiest max 1 gebeurtenis op prioriteit:
  onbehandelde goedkeuringen > saldo-onder-drempel > nachtelijke
  bouwronde. Geen gebeurtenis geldig → None (gewone begroeting).
- `hero_tekst(uur, goedkeuringen, saldo, saldo_drempel, nachtronde)`
  combineert beide: gebeurtenis-tekst wint van de kale begroeting.

Kern-logica is testbaar zonder Swift; de SwiftUI-binding volgt in de
slice zelf (HomeView + build-bewijs).
"""
import unittest
from pathlib import Path
import sys

REPO = Path(__file__).parent.parent
sys.path.insert(0, str(REPO / "kern"))

from growkit_home import begroeting, hero_variant, hero_tekst  # noqa: E402


class TestBegroeting(unittest.TestCase):
    def test_ochtend(self):
        self.assertEqual(begroeting(9), "Goedemorgen")

    def test_middag(self):
        self.assertEqual(begroeting(14), "Goedemiddag")

    def test_avond(self):
        self.assertEqual(begroeting(20), "Goedenavond")

    def test_nachtbug(self):
        # 02:30 → nacht telt als morgen (afdekking van de nachtbug).
        self.assertEqual(begroeting(2), "Goedemorgen")
        self.assertEqual(begroeting(4), "Goedemorgen")


class TestHeroVariant(unittest.TestCase):
    def test_goedkeuringen_wint_van_saldo(self):
        v = hero_variant(goodkeuringen=1, saldo=0, saldo_drempel=100,
                         nachtronde=True)
        self.assertEqual(v, "goedkeuringen")

    def test_saldo_wint_van_nachtronde(self):
        v = hero_variant(goodkeuringen=0, saldo=5, saldo_drempel=100,
                         nachtronde=True)
        self.assertEqual(v, "saldo")

    def test_nachtronde_alleen(self):
        v = hero_variant(goodkeuringen=0, saldo=500, saldo_drempel=100,
                         nachtronde=True)
        self.assertEqual(v, "nachtronde")

    def test_geen_variant(self):
        v = hero_variant(goodkeuringen=0, saldo=500, saldo_drempel=100,
                         nachtronde=False)
        self.assertIsNone(v)

    def test_max_1_variant(self):
        # Resultaat is altijd precies één variant of None — nooit een lijst.
        v = hero_variant(goodkeuringen=3, saldo=0, saldo_drempel=10,
                         nachtronde=True)
        self.assertIn(v, {"goedkeuringen", "saldo", "nachtronde", None})


class TestHeroTekst(unittest.TestCase):
    def test_gebeurtenis_wint(self):
        t = hero_tekst(14, goodkeuringen=2, saldo=500, saldo_drempel=100,
                       nachtronde=False)
        self.assertIn("goedkeuring", t.lower())

    def test_geen_gebeurtenis_begroeting(self):
        t = hero_tekst(14, goodkeuringen=0, saldo=500, saldo_drempel=100,
                       nachtronde=False)
        self.assertEqual(t, "Goedemiddag")


if __name__ == "__main__":
    unittest.main()
