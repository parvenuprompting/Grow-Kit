"""Omgevingsdetectie als gelabelde bron (§11.3-3b, audit-C).

Regels (fase 4, taak 7):
- detectie leest uitsluitend veldaanwezigheid: bestaat vps-doel.json in het
  profiel → VPS-standaard; anders de lokaal-standaard — beide gelabeld
  (standaardwaarde: true + bronvermelding 'omgevingsdetectie').
- De inhoud van vps-doel.json (host/gebruiker/poort) wordt nooit gelezen en
  kan daarom nooit in een concept verschijnen.
- De poort blijft ongewijzigd: de gelabelde standaard gaat als veldwaarde de
  poort in en wordt verbatim samengevoegd (fase-3-mechanisme).
"""
import json
import tempfile
import unittest
from pathlib import Path

import loop
from kern.growkit_poort import beoordeel_invoer


class TestDetectie(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.profiel_pad = Path(self._tmp.name) / "tweede-brein"
        self.profiel_pad.mkdir()

    def tearDown(self):
        self._tmp.cleanup()

    def test_vps_doel_aanwezig_geeft_gelabelde_vps_standaard(self):
        (self.profiel_pad / "vps-doel.json").write_text("{}", encoding="utf-8")
        standaard = loop.detecteer_omgeving(self.profiel_pad)
        self.assertTrue(standaard["standaardwaarde"])
        self.assertEqual(standaard["waarde"], "een VPS")
        self.assertIn("omgevingsdetectie", standaard["bron"])

    def test_zonder_vps_doel_lokaal_standaard(self):
        standaard = loop.detecteer_omgeving(self.profiel_pad)
        self.assertTrue(standaard["standaardwaarde"])
        self.assertEqual(standaard["waarde"], "deze machine (lokaal)")
        self.assertIn("omgevingsdetectie", standaard["bron"])

    def test_detectie_leest_nooit_de_inhoud(self):
        inhoud = {"host": "geheim-host.example", "gebruiker": "geheim-gebruiker", "poort": 2222}
        (self.profiel_pad / "vps-doel.json").write_text(json.dumps(inhoud), encoding="utf-8")
        standaard = loop.detecteer_omgeving(self.profiel_pad)
        tekst = json.dumps(standaard)
        for geheim in ("geheim-host.example", "geheim-gebruiker", "2222"):
            self.assertNotIn(geheim, tekst)


class TestDoorvoerViaFase3Mechanisme(unittest.TestCase):
    def test_gelabelde_standaard_vloeit_verbatim_door_de_poort(self):
        """De detectie-standaard gaat als veldwaarde de poort in — de poort
        voegt zonder her-interpretatie samen en het concept blijft gelabeld."""
        with tempfile.TemporaryDirectory() as tmp:
            profiel_pad = Path(tmp) / "boom"
            profiel_pad.mkdir()
            (profiel_pad / "vps-doel.json").write_text("{}", encoding="utf-8")
            invoer = {
                "type": "vrije_beschrijving",
                "tekst": "einddoel: fabriek; slaag-criterium: draait",
                "einddoel": "fabriek",
                "omgeving": loop.detecteer_omgeving(profiel_pad),
                "slaag_criterium": "draait",
            }
            ok, tekst, vragen = beoordeel_invoer(invoer, "vrije_beschrijving")
            self.assertTrue(ok)
            self.assertEqual(vragen, [])
            concept = json.loads(tekst)
            self.assertTrue(concept["omgeving"]["standaardwaarde"])
            self.assertEqual(concept["omgeving"]["waarde"], "een VPS")
            self.assertIn("omgevingsdetectie", concept["omgeving"]["bron"])


if __name__ == "__main__":
    unittest.main()
