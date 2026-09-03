import json
import unittest

from kern.growkit_poort import (
    WEIGERING_BUI,
    WEIGERING_TUINIER,
    beoordeel_invoer,
)


class TestVrijeBeschrijving(unittest.TestCase):
    def test_vage_invoer_wordt_geweigerd(self):
        invoer = {"type": "vrije_beschrijving", "tekst": "maak me iets om m'n notities te ordenen of zo"}
        ok, tekst, vragen = beoordeel_invoer(invoer, "vrije_beschrijving")
        self.assertFalse(ok)
        self.assertIn("bui", tekst)
        # de drie verplichte velden komen terug als vragen
        self.assertEqual(len(vragen), 3)
        onderwerp = " ".join(v["vraag"].lower() for v in vragen)
        for sleutel in ("einddoel", "omgeving", "slaag"):
            self.assertIn(sleutel, onderwerp)
        # vragenlijst volgt het §11.3-formaat
        for v in vragen:
            self.assertIn("vraag", v)
            self.assertIn("opties", v)
            self.assertEqual(v["opties"][-1], "iets anders (beschrijf)")

    def test_complete_invoer_wordt_concept(self):
        invoer = {
            "type": "vrije_beschrijving",
            "einddoel": "een tweede brein voor mijn notities",
            "omgeving": "lokaal",
            "slaag_criterium": "vijf mappen bestaan en logboek is leeg",
        }
        ok, tekst, _ = beoordeel_invoer(invoer, "vrije_beschrijving")
        self.assertTrue(ok)
        self.assertIn("einddoel", tekst)
        self.assertIn("wacht_op_mens", tekst)

    def test_kiemkeuze_zonder_doel_wordt_geweigerd(self):
        ok, tekst, _ = beoordeel_invoer({"profiel": "tweede-brein"}, "kiemkeuze")
        self.assertFalse(ok)
        self.assertIn(WEIGERING_TUINIER, tekst)

    def test_taak_zonder_bewijs_bestaat_niet(self):
        ok, tekst, _ = beoordeel_invoer({"id": "taak-1", "commando": "echo hi"}, "taak")
        self.assertFalse(ok)
        self.assertIn("bewijs", tekst)


class TestWeigeringsteksten(unittest.TestCase):
    def test_vaste_constanten(self):
        self.assertIn("bui", WEIGERING_BUI)
        self.assertIn("helderziende", WEIGERING_TUINIER)


if __name__ == "__main__":
    unittest.main()
