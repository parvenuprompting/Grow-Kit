"""Taak-uitvoering via de loop (§7): poort eerst, motor uit.

Regels (fase 4, taak 6):
- Kies taak uit de takenlijst → poort-validatie → motor als éénstaps-profiel.
- Taak zonder bewijs bestaat niet: geweigerd, niets uitgevoerd.
- Gebeurtenissen append-only in het taken-logboek; uitvoeringen ook in het
  boom-logboek (één bron van executie-geschiedenis).
- Bij faal: mens, geen retries (motor-faalcontract: één alternatief).
"""
import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

import loop


def _geldige_taak() -> dict:
    return {
        "id": "taak-001",
        "titel": "maak het kweekbestand",
        "commando": "printf x > kweek.txt && echo KWEEK-OK",
        "bewijs": {"type": "shell_check", "commando": "test -f kweek.txt && echo KWEEK-OK",
                   "verwacht_substr": "KWEEK-OK"},
    }


class TestTaakUitvoering(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.doel = Path(self._tmp.name)
        self.takenlijst = self.doel / "takenlijst.json"
        self._antwoorden = []

    def tearDown(self):
        self._tmp.cleanup()

    def _invoer_fn(self, _vraag: str) -> str:
        if not self._antwoorden:
            self.fail("er werd een vraag gesteld die niet verwacht was")
        return self._antwoorden.pop(0)

    def _run(self) -> tuple[int, str]:
        uit = io.StringIO()
        with contextlib.redirect_stdout(uit):
            code = loop.voer_taak(self.doel, invoer_fn=self._invoer_fn)
        return code, uit.getvalue()

    def test_geldige_taak_wordt_uitgevoerd_en_gelogd(self):
        self.takenlijst.write_text(json.dumps([_geldige_taak()]), encoding="utf-8")
        self._antwoorden = ["1"]
        code, uit = self._run()
        self.assertEqual(code, 0)
        self.assertTrue((self.doel / "kweek.txt").exists())
        gebeurtenissen = json.loads((self.doel / "taken-logboek.json").read_text(encoding="utf-8"))
        self.assertEqual(gebeurtenissen[-1]["taak"], "taak-001")
        self.assertEqual(gebeurtenissen[-1]["status"], "geslaagd")
        boom_logboek = json.loads((self.doel / "logboek.json").read_text(encoding="utf-8"))
        self.assertEqual(boom_logboek[0]["stap"], "taak-001")
        self.assertEqual(boom_logboek[0]["status"], "geslaagd")

    def test_taak_zonder_bewijs_geweigerd_niets_uitgevoerd(self):
        self.takenlijst.write_text(json.dumps([{"id": "taak-002", "titel": "zonder bewijs"}]),
                                    encoding="utf-8")
        self._antwoorden = ["1"]
        code, uit = self._run()
        self.assertEqual(code, 1)
        self.assertIn("bewijs", uit.lower())
        self.assertFalse((self.doel / "logboek.json").exists())   # niets uitgevoerd
        gebeurtenissen = json.loads((self.doel / "taken-logboek.json").read_text(encoding="utf-8"))
        self.assertEqual(gebeurtenissen[-1]["status"], "geweigerd")

    def test_faal_geeft_mens_geen_retries(self):
        faal_taak = {
            "id": "taak-003",
            "titel": "faalt altijd",
            "commando": "false",
            "bewijs": {"type": "shell_check", "commando": "false", "verwacht_substr": "OK"},
            "bij_falen": {"alternatief_commando": "false", "anders": "roep_mens"},
        }
        self.takenlijst.write_text(json.dumps([_geldige_taak(), faal_taak]), encoding="utf-8")
        self._antwoorden = ["2"]
        code, uit = self._run()
        self.assertEqual(code, 2)
        self.assertIn("Roep de mens", uit)
        gebeurtenissen = json.loads((self.doel / "taken-logboek.json").read_text(encoding="utf-8"))
        self.assertEqual(gebeurtenissen[-1]["status"], "gefaald")
        self.assertEqual(len([e for e in gebeurtenissen
                              if e["taak"] == "taak-003" and e["status"] == "gefaald"]), 1)

    def test_geen_taken_stelt_geen_vragen(self):
        code, uit = self._run()
        self.assertEqual(code, 0)
        self.assertIn("Geen taken", uit)


if __name__ == "__main__":
    unittest.main()
