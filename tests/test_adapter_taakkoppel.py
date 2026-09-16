"""S13 — adapter-commando `taakkoppel` (en lijst met eigenaren).

De adapter is bedienaar: alleen de kern aanroepen, JSON in → JSON uit.
Weigeringen zijn nette NL-antwoorden, nooit tracebacks.
"""
import json
import subprocess
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
ADAPTER = REPO / "adapter.py"
_PY_HERMES = Path.home() / ".hermes" / "hermes-agent" / "venv" / "bin" / "python"
PY = _PY_HERMES if _PY_HERMES.exists() else Path(sys.executable)


def roep(invoer: dict) -> dict:
    cmd = invoer.pop("commando")
    proces = subprocess.run(
        [str(PY), str(ADAPTER), cmd],
        input=json.dumps(invoer), capture_output=True, text=True, timeout=60)
    if proces.returncode != 0:
        raise AssertionError(f"adapter faalde: {proces.stderr[-300:]}")
    return json.loads(proces.stdout)


class TestTaakKoppelAdapter(unittest.TestCase):
    def setUp(self):
        import tempfile
        self.tmp = tempfile.TemporaryDirectory()
        self.doel = self.tmp.name
        taken = [{"id": "t1", "titel": "x", "bewijs":
                  [{"type": "file_exists", "pad": "x.txt"}]}]
        (Path(self.doel) / "takenlijst.json").write_text(
            json.dumps(taken), encoding="utf-8")

    def tearDown(self):
        self.tmp.cleanup()

    def test_koppel_via_adapter(self):
        uit = roep({"commando": "taakkoppel", "actie": "koppel",
                    "doel": self.doel, "taak_id": "t1", "eigenaar": "Vigil"})
        self.assertTrue(uit["ok"])
        self.assertEqual(uit["data"]["eigenaar"], "Vigil")

    def test_lijst_toont_eigenaar(self):
        roep({"commando": "taakkoppel", "actie": "koppel", "doel": self.doel,
              "taak_id": "t1", "eigenaar": "vigil"})
        uit = roep({"commando": "taakkoppel", "actie": "lijst",
                    "doel": self.doel})
        self.assertTrue(uit["ok"])
        self.assertEqual(uit["taken"][0]["eigenaar"], "Vigil")

    def test_onbekende_familie_is_nette_weigering(self):
        uit = roep({"commando": "taakkoppel", "actie": "koppel",
                    "doel": self.doel, "taak_id": "t1", "eigenaar": "Hacker"})
        self.assertFalse(uit["ok"])
        self.assertIn("familie", uit["fout"])


if __name__ == "__main__":
    unittest.main()