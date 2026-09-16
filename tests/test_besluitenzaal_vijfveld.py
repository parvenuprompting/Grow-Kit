"""Tests voor de vijf tegenpositie-velden (BSL-040, geratificeerd 10 sept) in de besluitenzaal.

Vijf velden per voorstel/besluit op het bord (Claude's besluit 1):
1. keuze — max 3 opties (al afgedwongen door de kern van KairOS)
2. aanbeveling — verplicht (al afgedwongen door de kern van KairOS)
3. vervaldatum — wanneer verloopt het voorstel (verstek-moment)
4. verstek — wat er automatisch gebeurt als de Baas niets doet vóór de vervaldatum
5. omkeerbaar — of het besluit na uitvoering teruggedraaid kan worden (ja/nee + hoe)
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from kern import growkit_besluitenzaal as bz


VOORSTEL_VOLLEDIG = """# Trigger-woordenboek v2
Geadviseerd door: Genius
Context: bestaand woordboek mist drie termen.
Optie A: uitbreiden met 3 termen
Optie B: opnieuw genereren
Aanbeveling: A — kleinste diff, direct testbaar
Vervaldatum: 15-09-2026
Verstek: optie A wordt uitgevoerd
Omkeerbaar: ja — git revert
"""

VOORSTEL_ONVOLLEDIG = """# Voorstel zonder vijf-veld
Geadviseerd door: Test
Optie A: iets
Aanbeveling: A
"""


class TestVijfVeldenParser(unittest.TestCase):
    def test_vervaldatum_geparseerd(self):
        v = bz.parseer_voorstel(VOORSTEL_VOLLEDIG, "test.md")
        self.assertEqual(v["vervaldatum"], "15-09-2026")

    def test_verstek_geparseerd(self):
        v = bz.parseer_voorstel(VOORSTEL_VOLLEDIG, "test.md")
        self.assertEqual(v["verstek"], "optie A wordt uitgevoerd")

    def test_omkeerbaar_geparseerd(self):
        v = bz.parseer_voorstel(VOORSTEL_VOLLEDIG, "test.md")
        self.assertTrue(v["omkeerbaar"])
        self.assertIn("git revert", v["omkeerbaar_hoe"])

    def test_ontbrekende_velden_leeg_of_false(self):
        v = bz.parseer_voorstel(VOORSTEL_ONVOLLEDIG, "test.md")
        self.assertEqual(v["vervaldatum"], "")
        self.assertEqual(v["verstek"], "")
        self.assertFalse(v["omkeerbaar"])

    def test_verlopen_voorstel_is_ongeldig(self):
        """Een voorstel met vervaldatum in het verleden rendert als verlopen."""
        verlopen = VOORSTEL_VOLLEDIG.replace("15-09-2026", "01-09-2026")
        v = bz.parseer_voorstel(verlopen, "test.md")
        self.assertTrue(bz.is_verlopen(v, vandaag="10-09-2026"))
        self.assertFalse(bz.is_verlopen(v, vandaag="01-09-2026"))

    def test_is_verlopen_zonder_vervaldatum_is_nooit_verlopen(self):
        v = bz.parseer_voorstel(VOORSTEL_ONVOLLEDIG, "test.md")
        self.assertFalse(bz.is_verlopen(v, vandaag="10-09-2026"))


class TestVijfVeldenUI(unittest.TestCase):
    def _vijf_velden_in_html(self, html: str) -> bool:
        return all(label in html for label in ("Vervaldatum", "Verstek", "Omkeerbaar"))

    def test_render_toont_drie_nieuwe_velden(self):
        v = bz.parseer_voorstel(VOORSTEL_VOLLEDIG, "test.md")
        uit = bz.render("", [v], [])
        self._vijf_velden_in_html(uit)

    def test_verlopen_voorstel_krijgt_label(self):
        verlopen = VOORSTEL_VOLLEDIG.replace("15-09-2026", "01-09-2026")
        v = bz.parseer_voorstel(verlopen, "test.md")
        uit = bz.render("", [v], [], vandaag="10-09-2026")
        self.assertIn("vervallen", uit.lower())

    def test_verlopen_voorstel_toont_verstek_als_uitkomst(self):
        """Verstek = wat er gebeurt als de Baas niets doet; bij verval is dat de melding."""
        verlopen = VOORSTEL_VOLLEDIG.replace("15-09-2026", "01-09-2026")
        v = bz.parseer_voorstel(verlopen, "test.md")
        uit = bz.render("", [v], [], vandaag="10-09-2026")
        self.assertIn("optie A wordt uitgevoerd", uit)

    def test_omkeerbaar_toont_hoe(self):
        v = bz.parseer_voorstel(VOORSTEL_VOLLEDIG, "test.md")
        uit = bz.render("", [v], [])
        self.assertIn("git revert", uit)

    def test_registerregel_met_vijf_velden_wordt_ontleed(self):
        """Besluiten in het register kunnen de vijf velden als suffix dragen."""
        regel = ("[BSL-040] Tegenpositie-veld geratificeerd | status: besloten | 10-09-2026 | "
                 "bron: inbox/x.md | vervaldatum: 20-09-2026 | verstek: van kracht | omkeerbaar: ja — herstemming")
        velden = bz.ontleed_registerregel(regel)
        self.assertEqual(velden["vervaldatum"], "20-09-2026")
        self.assertEqual(velden["verstek"], "van kracht")
        self.assertTrue(velden["omkeerbaar"])

    def test_registerregel_zonder_suffix_geeft_lege_velden(self):
        velden = bz.ontleed_registerregel(
            "[BSL-001] PLAN-EERST | status: besloten | 08-09-2026 | bron: inbox/a.md")
        self.assertEqual(velden["vervaldatum"], "")
        self.assertEqual(velden["verstek"], "")
        self.assertFalse(velden["omkeerbaar"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
