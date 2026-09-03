"""Takenlijst-schema (§7): taken bestaan alleen mét bewijs.

Regels (fase 4, taak 1):
- Een taak zonder bewijs-check is ongeldig — de poort-regel uit fase 2.
- Afwezig takenlijstbestand → lege lijst.
- Taakgebeurtenissen zijn append-only; corrupt bestand → nette NL-fout.
"""
import json
import tempfile
import unittest
from pathlib import Path

from kern.growkit_taken import laad_taken, log_taakgebeurtenis, valideer_taak


def _geldige_taak() -> dict:
    return {
        "id": "taak-001",
        "titel": "check dat de kweekmap bestaat",
        "commando": "test -d kweek && echo KWEEK-OK",
        "bewijs": {"type": "shell_check", "commando": "test -d kweek && echo KWEEK-OK",
                   "verwacht_substr": "KWEEK-OK"},
    }


class TestValideerTaak(unittest.TestCase):
    def test_taak_zonder_bewijs_is_ongeldig(self):
        bevindingen = valideer_taak({"id": "taak-001", "titel": "zonder bewijs"})
        self.assertTrue(bevindingen)
        self.assertTrue(any("bewijs" in b.lower() for b in bevindingen))

    def test_geldige_taak_leegt_de_bevindingen(self):
        self.assertEqual(valideer_taak(_geldige_taak()), [])

    def test_taak_zonder_id_is_ongeldig(self):
        bevindingen = valideer_taak({"titel": "x", "bewijs": {"type": "shell_check"}})
        self.assertTrue(any("id" in b.lower() for b in bevindingen))


class TestLaadTaken(unittest.TestCase):
    def test_afwezig_bestand_geeft_lege_lijst(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(laad_taken(Path(tmp) / "takenlijst.json"), [])

    def test_geldig_bestand_levert_taken(self):
        with tempfile.TemporaryDirectory() as tmp:
            pad = Path(tmp) / "takenlijst.json"
            pad.write_text(json.dumps([_geldige_taak()]), encoding="utf-8")
            taken = laad_taken(pad)
            self.assertEqual(len(taken), 1)
            self.assertEqual(taken[0]["id"], "taak-001")

    def test_corrupt_bestand_geeft_nette_fout(self):
        with tempfile.TemporaryDirectory() as tmp:
            pad = Path(tmp) / "takenlijst.json"
            pad.write_text("{geen json", encoding="utf-8")
            with self.assertRaises(ValueError) as ctx:
                laad_taken(pad)
            self.assertIn("corrupt", str(ctx.exception).lower())


class TestLogTaakgebeurtenis(unittest.TestCase):
    def test_gebeurtenissen_zijn_append_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            pad = Path(tmp) / "taken-logboek.json"
            bestaand = [{"type": "taak", "taak": "taak-000", "status": "geslaagd", "bewijs": "eerder"}]
            pad.write_text(json.dumps(bestaand), encoding="utf-8")
            log_taakgebeurtenis(pad, "taak-001", "voorgesteld", "nieuwe taak")
            entries = json.loads(pad.read_text(encoding="utf-8"))
            self.assertEqual(entries[0], bestaand[0])
            self.assertEqual(len(entries), 2)
            self.assertEqual(entries[1]["taak"], "taak-001")
            self.assertEqual(entries[1]["status"], "voorgesteld")
            self.assertIn("tijdstip", entries[1])

    def test_bestand_wordt_aangemaakt_waar_nodig(self):
        with tempfile.TemporaryDirectory() as tmp:
            pad = Path(tmp) / "diep" / "genest" / "taken-logboek.json"
            log_taakgebeurtenis(pad, "taak-001", "geslaagd", "KWEEK-OK")
            entries = json.loads(pad.read_text(encoding="utf-8"))
            self.assertEqual(len(entries), 1)
            self.assertEqual(entries[0]["status"], "geslaagd")


if __name__ == "__main__":
    unittest.main()
