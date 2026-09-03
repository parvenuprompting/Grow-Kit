import json
import tempfile
import unittest
from pathlib import Path

from kern.growkit_review import laad_reviewconfig, valideer_reviewconfig


class TestLaadReviewconfig(unittest.TestCase):
    def test_afwezig_bestand_geeft_none(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertIsNone(laad_reviewconfig(Path(d) / "reviewconfig.json"))

    def test_geldig_config_wordt_gelezen(self):
        with tempfile.TemporaryDirectory() as d:
            pad = Path(d) / "reviewconfig.json"
            pad.write_text(json.dumps({
                "rollen": {
                    "reviewer": {"type": "cli", "commando": "echo geslaagd"}
                }
            }), encoding="utf-8")
            config = laad_reviewconfig(pad)
            self.assertIsNotNone(config)
            self.assertIn("reviewer", config["rollen"])


class TestValideerReviewconfig(unittest.TestCase):
    def test_geldig_cli_config(self):
        bevindingen = valideer_reviewconfig({"rollen": {"reviewer": {"type": "cli", "commando": "echo x"}}})
        self.assertEqual(bevindingen, [])

    def test_geldig_http_config(self):
        bevindingen = valideer_reviewconfig({"rollen": {"reviewer": {"type": "http", "url": "http://localhost:1", "verwacht_status": 200}}})
        self.assertEqual(bevindingen, [])

    def test_verboden_leveranciersvelden(self):
        # model/provider/leverancier in een rol = leveranciers-binding = schema-fout
        for veld in ("model", "provider", "leverancier"):
            bevindingen = valideer_reviewconfig({"rollen": {"reviewer": {"type": "cli", "commando": "echo x", veld: "gpt-9"}}})
            self.assertTrue(any(veld in b for b in bevindingen), f"verboden veld {veld} niet gevonden")

    def test_http_zonder_url_wordt_geweigerd(self):
        bevindingen = valideer_reviewconfig({"rollen": {"reviewer": {"type": "http"}}})
        self.assertTrue(bevindingen)

    def test_cli_zonder_commando_wordt_geweigerd(self):
        bevindingen = valideer_reviewconfig({"rollen": {"reviewer": {"type": "cli"}}})
        self.assertTrue(bevindingen)

    def test_onbekend_type_wordt_geweigerd(self):
        bevindingen = valideer_reviewconfig({"rollen": {"reviewer": {"type": "rooksignaal"}}})
        self.assertTrue(bevindingen)


if __name__ == "__main__":
    unittest.main()
