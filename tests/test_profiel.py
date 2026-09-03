import json
import unittest
from pathlib import Path

PROFIEL = Path(__file__).parent.parent / "profielen" / "tweede-brein" / "profiel.json"
SJABLONEN = PROFIEL.parent / "sjablonen"


class TestTweedeBreinProfiel(unittest.TestCase):
    def setUp(self):
        with open(PROFIEL, encoding="utf-8") as f:
            self.profiel = json.load(f)

    def test_basale_structuur(self):
        self.assertEqual(self.profiel["profiel"], "tweede-brein")
        self.assertEqual(self.profiel["status"], "bewezen-vorm")
        self.assertIn("stappen", self.profiel)

    def test_elke_stap_heeft_verplichte_velden(self):
        for stap in self.profiel["stappen"]:
            for veld in ("id", "commando", "bewijs", "bij_falen", "idempotent"):
                self.assertIn(veld, stap, f"{stap.get('id', '?')} mist veld {veld}")
            self.assertIn(stap["bewijs"]["type"],
                          {"shell_check", "http_check", "file_exists", "json_valid", "file_equals", "mens_verificatie"})

    def test_sjablonen_bestaan(self):
        for bestand in ("INDEX.md", "AGENT-ROL.md", "REGELS.md", "geboortebewijs.json.template"):
            self.assertTrue((SJABLONEN / bestand).exists(), f"sjabloon {bestand} ontbreekt")

    def test_kernmappen_staan_in_profiel(self):
        for map_ in ("identiteit", "kennis", "projecten", "inbox", "logboek"):
            self.assertIn(map_, self.profiel["mappen"])


if __name__ == "__main__":
    unittest.main()
