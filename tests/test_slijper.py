"""Slijper-schuring (§11.1 taken 1-2): alleen expliciet maken wat erin zit.

Regels (fase 3, taak 5):
- Complete invoer → concept met exact de drie inhoudsvelden, zonder
  her-interpretatie, mét bronvermelding van de rauwe invoer.
- Ontbrekende velden → alleen vragen over wat ontbreekt.
- Alleen omgeving-ontbreken → gelabelde standaardwaarde (standaardwaarde:
  true + bronvermelding); een ongelabelde standaardwaarde is een testfaal.
- Einddoel wordt nooit door de slijper ingevuld — dan volgt een vraag.
"""
import json
import unittest

from kern.growkit_poort import WEIGERING_BUI, beoordeel_invoer

STANDAARD_OMGEVING = "deze machine (lokaal)"


def _invoer(**wijzigingen) -> dict:
    invoer = {
        "type": "vrije_beschrijving",
        "tekst": "einddoel: een tweede brein; omgeving: lokaal; slaag-criterium: vijf mappen bestaan",
        "einddoel": "een tweede brein",
        "omgeving": "lokaal",
        "slaag_criterium": "vijf mappen bestaan",
    }
    for sleutel, waarde in wijzigingen.items():
        if waarde is None:
            invoer.pop(sleutel, None)
        else:
            invoer[sleutel] = waarde
    return invoer


class TestConceptSamenvoeging(unittest.TestCase):
    def test_complete_invoer_geeft_concept_exact_drie_inhoudsvelden(self):
        ok, tekst, vragen = beoordeel_invoer(_invoer(), "vrije_beschrijving")
        self.assertTrue(ok)
        self.assertEqual(vragen, [])
        concept = json.loads(tekst)
        self.assertEqual(set(concept),
                         {"einddoel", "omgeving", "slaag_criterium", "bron", "status"})
        # geen her-interpretatie: waarden zijn letterlijk overgenomen
        self.assertEqual(concept["einddoel"], "een tweede brein")
        self.assertEqual(concept["omgeving"], "lokaal")
        self.assertEqual(concept["slaag_criterium"], "vijf mappen bestaan")
        self.assertEqual(concept["status"], "wacht_op_mens")

    def test_concept_vermeldt_rauwe_invoer_als_bron(self):
        raw = _invoer()["tekst"]
        _, tekst, _ = beoordeel_invoer(_invoer(), "vrije_beschrijving")
        concept = json.loads(tekst)
        self.assertEqual(concept["bron"], {"ruwe_invoer": raw})

    def test_ontbrekend_einddoel_geeft_alleen_die_vraag(self):
        ok, tekst, vragen = beoordeel_invoer(_invoer(einddoel=None), "vrije_beschrijving")
        self.assertFalse(ok)
        self.assertIn(WEIGERING_BUI, tekst)
        self.assertEqual(len(vragen), 1)
        self.assertIn("einddoel", vragen[0]["vraag"])

    def test_ontbrekend_slaag_criterium_geeft_alleen_die_vraag(self):
        ok, _, vragen = beoordeel_invoer(_invoer(slaag_criterium=None), "vrije_beschrijving")
        self.assertFalse(ok)
        self.assertEqual(len(vragen), 1)
        self.assertIn("slaag", vragen[0]["vraag"])

    def test_meerdere_ontbrekende_velden_leveren_geen_concept(self):
        ok, tekst, vragen = beoordeel_invoer(_invoer(einddoel=None, omgeving=None),
                                             "vrije_beschrijving")
        self.assertFalse(ok)
        self.assertEqual(len(vragen), 2)
        # geen standaardwaarde in een geweigerde beurt: geen concept, geen invul
        self.assertNotIn("standaardwaarde", tekst)
        self.assertNotIn(STANDAARD_OMGEVING, tekst)


class TestGelabeldeStandaardwaarden(unittest.TestCase):
    def test_alleen_omgeving_ontbreekt_krijgt_gelabelde_standaard(self):
        ok, tekst, vragen = beoordeel_invoer(_invoer(omgeving=None), "vrije_beschrijving")
        self.assertTrue(ok)
        self.assertEqual(vragen, [])
        concept = json.loads(tekst)
        omg = concept["omgeving"]
        self.assertIsInstance(omg, dict)
        self.assertTrue(omg.get("standaardwaarde"))
        self.assertEqual(omg.get("waarde"), STANDAARD_OMGEVING)
        self.assertIn("bron", omg)
        self.assertIn("standaard", omg["bron"].lower())
        # overige velden blijven letterlijk uit de invoer
        self.assertEqual(concept["einddoel"], "een tweede brein")
        self.assertEqual(concept["slaag_criterium"], "vijf mappen bestaan")

    def test_ongelabelde_standaardwaarde_is_testfaal(self):
        """De standaardwaarde mag nooit als kale waarde in het concept staan."""
        _, tekst, _ = beoordeel_invoer(_invoer(omgeving=None), "vrije_beschrijving")
        concept = json.loads(tekst)
        omg = concept["omgeving"]
        if isinstance(omg, str):
            self.assertNotEqual(omg, STANDAARD_OMGEVING,
                                "ongelabelde standaardwaarde in het concept — testfaal (§11.1 punt 2)")

    def test_einddoel_wordt_nooit_ingevuld_door_de_slijper(self):
        """Zonder einddoel volgt een vraag, nooit een invul — ook niet gelabeld."""
        ok, _, vragen = beoordeel_invoer(_invoer(einddoel=None), "vrije_beschrijving")
        self.assertFalse(ok)
        self.assertEqual([v["vraag"] for v in vragen], ["Wat is het einddoel?"])


if __name__ == "__main__":
    unittest.main()
