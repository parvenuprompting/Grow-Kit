"""Slice S13 — Familierij stap D: taak koppelen aan een familielid.

Een taak in de takenlijst van een boom kan worden gekoppeld aan een
familielid uit het familie-register. Bewijs:
- de koppeling slaat de eigenaar bij de taak op (append-vriendelijk veld)
- een onbekende eigenaar wordt geweigerd (de familie is wie hij is)
- de zijbalk-overzichtslijst toont per taak de eigenaar
"""
import json
import tempfile
import unittest
from pathlib import Path

from kern import growkit_taken as tk


class TestTaakKoppelen(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.doel = Path(self.tmp.name)
        self.bestand = self.doel / "takenlijst.json"
        self.takenlijst = [
            {"id": "taak-1", "titel": "Basis-audit", "bewijs": [
                {"type": "file_exists", "pad": "x.txt"}]},
            {"id": "taak-2", "titel": "Onderzoek markt", "bewijs": [
                {"type": "file_exists", "pad": "y.txt"}]},
        ]
        self.bestand.write_text(json.dumps(self.takenlijst),
                                encoding="utf-8")

    def tearDown(self):
        self.tmp.cleanup()

    def test_koppel_bestaande_taak_aan_familielid(self):
        uit = tk.koppel_eigenaar(self.bestand, "taak-1", "Vigil")
        self.assertTrue(uit["ok"])
        taken = json.loads(self.bestand.read_text(encoding="utf-8"))
        eigenaar = next(t for t in taken if t["id"] == "taak-1")["eigenaar"]
        self.assertEqual(eigenaar, "Vigil")

    def test_onbekend_familielid_wordt_geweigerd(self):
        uit = tk.koppel_eigenaar(self.bestand, "taak-1", "Hacker")
        self.assertFalse(uit["ok"])
        self.assertIn("familie", uit["fout"])

    def test_onbekende_taak_wordt_geweigerd(self):
        uit = tk.koppel_eigenaar(self.bestand, "taak-99", "Vigil")
        self.assertFalse(uit["ok"])

    def test_lijst_toont_eigenaar_per_taak(self):
        tk.koppel_eigenaar(self.bestand, "taak-2", "Libra")
        uit = tk.taken_met_eigenaar(self.bestand)
        gevonden = {t["id"]: t.get("eigenaar") for t in uit}
        self.assertEqual(gevonden["taak-2"], "Libra")
        self.assertIsNone(gevonden["taak-1"])

    def test_hoofdletterongevoelig_registeren(self):
        uit = tk.koppel_eigenaar(self.bestand, "taak-1", "kairos")
        self.assertTrue(uit["ok"])
        taken = json.loads(self.bestand.read_text(encoding="utf-8"))
        self.assertEqual(
            next(t for t in taken if t["id"] == "taak-1")["eigenaar"],
            "KairOS")


if __name__ == "__main__":
    unittest.main()