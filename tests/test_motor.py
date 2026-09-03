import json
import tempfile
import unittest
from pathlib import Path

from kern.growkit_motor import voer_stap_uit, voer_uit


def maak_profiel():
    return {
        "profiel": "test",
        "stappen": [
            {
                "id": "stap-001",
                "commando": "echo OK",
                "verwacht": "OK verschijnt",
                "bewijs": {"type": "shell_check", "commando": "echo OK", "verwacht_substr": "OK"},
                "bij_falen": {"alternatief_commando": None, "anders": "roep_mens"},
                "idempotent": True,
            },
            {
                "id": "stap-002",
                "commando": "false",
                "verwacht": "onmogelijk",
                "bewijs": {"type": "shell_check", "commando": "false", "verwacht_substr": "nooit"},
                "bij_falen": {"alternatief_commando": "echo ook-niet", "anders": "roep_mens"},
                "idempotent": False,
            },
        ],
    }


class TestStap(unittest.TestCase):
    def test_geslaagde_stap(self):
        with tempfile.TemporaryDirectory() as d:
            ok, _ = voer_stap_uit(maak_profiel()["stappen"][0], Path(d), None)
            self.assertTrue(ok)

    def test_gefaalde_stap_met_alternatief_ook_faalt(self):
        with tempfile.TemporaryDirectory() as d:
            ok, _ = voer_stap_uit(maak_profiel()["stappen"][1], Path(d), None)
            self.assertFalse(ok)


class TestVolledigeRun(unittest.TestCase):
    def test_run_stopt_bij_falen_en_logt(self):
        with tempfile.TemporaryDirectory() as d:
            doel = Path(d) / "plant"
            doel.mkdir()
            logboek = Path(d) / "logboek.json"
            logboek.write_text("[]", encoding="utf-8")
            ok = voer_uit(maak_profiel(), doel, logboek, None)
            self.assertFalse(ok)  # stap-002 faalt per opzet
            entries = json.loads(logboek.read_text(encoding="utf-8"))
            self.assertEqual(entries[0]["stap"], "stap-001")
            self.assertEqual(entries[0]["status"], "geslaagd")
            self.assertEqual(entries[1]["status"], "gefaald")


if __name__ == "__main__":
    unittest.main()
