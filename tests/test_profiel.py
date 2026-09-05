"""Slice H — tests voor geheugen-geboorte: het profiel als append-only knoop.

Bewijsvruchten:
- concept → ratificatie → opslag: er is géén opslag zonder bevestiging
- opslag is append-only: wijzigingen voegen een regel toe, overschrijven nooit
- elke regel draagt een datum (geheugen vervalt; "rol van 2026" ≠ 2028)
- alles lokaal (tmp-dir), niets de cloud in
- lege profielen zijn toegestaan (skip = "Later invullen")
"""
import json
import tempfile
import unittest
from pathlib import Path

from kern import growkit_profiel as pf


class TestGeheugenGeboorte(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.wortel = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_geen_opslag_zonder_ratificatie(self):
        r = pf.concept("Tiëndo", rol="ondernemer", doel="rustig bouwen",
                       wortel=self.wortel)
        self.assertTrue(r["ok"])
        self.assertIsNone(r["data"]["opgeslagen"])  # nog niets weggeschreven
        pad = self.wortel / "profiel.json"
        self.assertFalse(pad.exists())

    def test_ratificatie_schrijft_profiel_met_datum(self):
        c = pf.concept("Tiëndo", rol="ondernemer", wortel=self.wortel)
        r = pf.bekrachtig(c["data"]["concept"], wortel=self.wortel)
        self.assertTrue(r["ok"])
        doc = json.loads((self.wortel / "profiel.json").read_text())
        self.assertEqual(doc["huidig"]["naam"], "Tiëndo")
        self.assertIn("datum", doc["huidig"])

    def test_wijziging_is_nieuwe_regel_niet_overschrijving(self):
        c1 = pf.concept("Tiëndo", rol="ondernemer", wortel=self.wortel)
        pf.bekrachtig(c1["data"]["concept"], wortel=self.wortel)
        c2 = pf.concept("Tiëndo", rol="vlaggenschip-bouwer", wortel=self.wortel)
        pf.bekrachtig(c2["data"]["concept"], wortel=self.wortel)
        doc = json.loads((self.wortel / "profiel.json").read_text())
        self.assertEqual(doc["huidig"]["rol"], "vlaggenschip-bouwer")
        self.assertEqual(len(doc["regels"]), 2)
        self.assertEqual(doc["regels"][0]["rol"], "ondernemer")  # historie blijft

    def test_leeg_profiel_mag(self):
        c = pf.concept("", wortel=self.wortel)
        r = pf.bekrachtig(c["data"]["concept"], wortel=self.wortel)
        self.assertTrue(r["ok"])
        doc = json.loads((self.wortel / "profiel.json").read_text())
        self.assertEqual(doc["huidig"].get("naam", ""), "")

    def test_lezen_geeft_leeg_profiel_als_er_nog_geen_is(self):
        r = pf.lees(wortel=self.wortel)
        self.assertTrue(r["ok"])
        self.assertIsNone(r["data"]["profiel"])
        self.assertFalse(r["data"]["bestaat"])

    def test_context_regel_voor_agents(self):
        c = pf.concept("Tiëndo", rol="curator", taal="NL", wortel=self.wortel)
        pf.bekrachtig(c["data"]["concept"], wortel=self.wortel)
        r = pf.context_regel(wortel=self.wortel)
        self.assertIn("Tiëndo", r)
        self.assertIn("curator", r)


if __name__ == "__main__":
    unittest.main()
