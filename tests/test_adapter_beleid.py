"""S12 — adapter-commando `beleid`: het beleidsregister doorgeven.

De adapter is bedienaar: hij roept alleen de kern aan. Weigeringen
als {"ok": false, "fout": ...} met exit 1, nooit tracebacks.
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


def roep(invoer: dict) -> tuple[dict, int]:
    cmd = invoer.pop("commando")
    proces = subprocess.run(
        [str(PY), str(ADAPTER), cmd],
        input=json.dumps(invoer), capture_output=True, text=True, timeout=60)
    if proces.returncode != 0:
        raise AssertionError(f"adapter faalde: {proces.stderr[-300:]}")
    return json.loads(proces.stdout), proces.returncode


class TestBeleidAdapter(unittest.TestCase):
    def test_status_geeft_zeven_beleidsobjecten(self):
        uit, _ = roep({"commando": "beleid", "actie": "status"})
        self.assertTrue(uit["ok"])
        self.assertEqual(len(uit["data"]["beleid"]), 7)
        namen = {b["agent"] for b in uit["data"]["beleid"]}
        self.assertEqual(namen, {"KairOS", "Riri", "Vigil", "Libra",
                                 "Memoria", "Codex", "Genius"})

    def test_controle_weigert_voor_uitvoering(self):
        uit, _ = roep({"commando": "beleid", "actie": "controle",
                       "agent": "vigil", "actiesoort": "wissen"})
        self.assertFalse(uit["ok"])          # weigering als antwoord, exit blijft 0 (net antwoord)
        self.assertIn("wissen", uit["weigering"])

    def test_controle_doorgt_(self):
        uit, _ = roep({"commando": "beleid", "actie": "controle",
                       "agent": "vigil", "actiesoort": "lezen"})
        self.assertTrue(uit["ok"])

    def test_onbekende_actiesoort_is_nette_fout(self):
        uit, proces = roep({"commando": "beleid", "actie": "controle",
                            "agent": "vigil", "actiesoort": "vliegen"})
        self.assertFalse(uit["ok"])
        self.assertIn("fout", uit)


if __name__ == "__main__":
    unittest.main()