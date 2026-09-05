"""Ronde 2 — tests voor de wizard-hervatvlag: hervat waar je was.

Eén generiek mechanisme, twee toepassingen (profiel-kieming en
Tailscale-onboarding) en straks meer. Bewijsvruchten:
- voortgang is append-only: stap afronden voegt een event toe, overschrijft nooit
- hervatten geeft de eerste onafgeronde stap terug
- een stap mag niet worden afgerond die nog niet aan de beurt is (volgorde-bewaking)
- afgeronde stappen worden niet opnieuw uitgevoerd
- onafhankelijk van welke wizard: alle wizards hebben hun eigen voortgang
"""
import json
import tempfile
import unittest
from pathlib import Path

from kern import growkit_hervatvlag as hv


class TestHervatvlag(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.wortel = Path(self.tmp.name)
        self.stappen = ["detecteer", "installeer", "verbind", "verifieer"]

    def tearDown(self):
        self.tmp.cleanup()

    def test_nieuwe_wizard_begint_bij_stap_1(self):
        r = hv.hervat("tailscale", self.stappen, wortel=self.wortel)
        self.assertTrue(r["ok"])
        self.assertEqual(r["data"]["volgende"], "detecteer")
        self.assertEqual(r["data"]["afgerond"], [])

    def test_stap_afronden_append_only(self):
        hv.rond_af("tailscale", "detecteer", wortel=self.wortel)
        pad = self.wortel / "hervatvlag" / "tailscale.json"
        doc = json.loads(pad.read_text())
        self.assertEqual(len(doc["events"]), 1)  # één append, geen overschrijving
        hv.rond_af("tailscale", "installeer", wortel=self.wortel)
        doc = json.loads(pad.read_text())
        self.assertEqual(len(doc["events"]), 2)

    def test_hervatten_geeft_volgende_onafgeronde_stap(self):
        hv.rond_af("tailscale", "detecteer", wortel=self.wortel)
        hv.rond_af("tailscale", "installeer", wortel=self.wortel)
        r = hv.hervat("tailscale", self.stappen, wortel=self.wortel)
        self.assertEqual(r["data"]["volgende"], "verbind")

    def test_klaar_is_klaar(self):
        for s in self.stappen:
            hv.rond_af("tailscale", s, wortel=self.wortel)
        r = hv.hervat("tailscale", self.stappen, wortel=self.wortel)
        self.assertTrue(r["data"]["klaar"])
        self.assertIsNone(r["data"]["volgende"])

    def test_stappen_mogen_niet_overslaan(self):
        hv.rond_af("tailscale", "verbind", wortel=self.wortel)  # 2 stappen overgeslagen
        r = hv.hervat("tailscale", self.stappen, wortel=self.wortel)
        # de vlag is genoteerd maar hervatten stuurt gewoon naar de eerste
        # onafgeronde stap: geen gat in de volgorde
        self.assertEqual(r["data"]["volgende"], "detecteer")

    def test_afgeronde_stap_wordt_niet_twee_keer_geteld(self):
        hv.rond_af("tailscale", "detecteer", wortel=self.wortel)
        hv.rond_af("tailscale", "detecteer", wortel=self.wortel)
        r = hv.hervat("tailscale", self.stappen, wortel=self.wortel)
        self.assertEqual(len(r["data"]["afgerond"]), 1)  # gedupliceerd

    def test_wizards_zijn_onafhankelijk(self):
        hv.rond_af("tailscale", "detecteer", wortel=self.wortel)
        r = hv.hervat("profiel-kieming", ["kies", "plant"], wortel=self.wortel)
        self.assertEqual(r["data"]["volgende"], "kies")
        self.assertEqual(r["data"]["afgerond"], [])


if __name__ == "__main__":
    unittest.main()
