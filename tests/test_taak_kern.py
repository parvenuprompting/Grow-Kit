"""Taak-uitvoeringskern (fase 6.1): één bron voor loop.py en de adapter."""
import json
import tempfile
import unittest
from pathlib import Path

from kern.growkit_taken import voer_taak_uit


class TestVoerTaakUit(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.doel = Path(self._tmp.name)
        (self.doel / "logboek.json").write_text("[]", encoding="utf-8")

    def tearDown(self):
        self._tmp.cleanup()

    def _geldige_taak(self):
        return {"id": "taak-001", "titel": "kweekbestand",
                "commando": "printf x > kweek.txt && echo KWEEK-OK",
                "bewijs": {"type": "shell_check", "commando": "test -f kweek.txt && echo KWEEK-OK",
                           "verwacht_substr": "KWEEK-OK"}}

    def test_geldige_taak_wordt_uitgevoerd_en_gelgd(self):
        geslaagd, bevindingen = voer_taak_uit(self.doel, self._geldige_taak())
        self.assertTrue(geslaagd)
        self.assertEqual(bevindingen, [])
        gebeurtenissen = json.loads((self.doel / "taken-logboek.json").read_text(encoding="utf-8"))
        self.assertEqual([e["status"] for e in gebeurtenissen], ["bezig", "geslaagd"])
        boom = json.loads((self.doel / "logboek.json").read_text(encoding="utf-8"))
        self.assertEqual(boom[0]["stap"], "taak-001")

    def test_ongeldige_taak_wordt_geweigerd_zonder_uitvoering(self):
        geslaagd, bevindingen = voer_taak_uit(self.doel, {"id": "taak-002", "titel": "zonder bewijs"})
        self.assertFalse(geslaagd)
        self.assertTrue(bevindingen)
        self.assertFalse((self.doel / "logboek.json").exists() and
                         len(json.loads((self.doel / "logboek.json").read_text(encoding="utf-8"))) > 0)
        gebeurtenissen = json.loads((self.doel / "taken-logboek.json").read_text(encoding="utf-8"))
        self.assertEqual(gebeurtenissen[-1]["status"], "geweigerd")

    def test_faal_wordt_gelgd_zonder_retries(self):
        faal = {"id": "taak-003", "titel": "faalt", "commando": "false",
                "bewijs": {"type": "shell_check", "commando": "false", "verwacht_substr": "OK"},
                "bij_falen": {"alternatief_commando": "false", "anders": "roep_mens"}}
        geslaagd, bevindingen = voer_taak_uit(self.doel, faal)
        self.assertFalse(geslaagd)
        self.assertEqual(bevindingen, [])
        gebeurtenissen = json.loads((self.doel / "taken-logboek.json").read_text(encoding="utf-8"))
        self.assertEqual(len([e for e in gebeurtenissen if e["status"] == "gefaald"]), 1)


if __name__ == "__main__":
    unittest.main()
