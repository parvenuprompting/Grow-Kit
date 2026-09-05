"""Slice A — familie-register: de 7 Telegram-agents van Tiëndo.

De familie is géén boom: het is de vaste cast achter het harnas.
De kernmodule levert de feiten; de adapter bedient alleen.
"""
import json
import subprocess
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
ADAPTER = REPO / "adapter.py"
PY = Path.home() / ".hermes" / "hermes-agent" / "venv" / "bin" / "python"


def roep(invoer: dict) -> dict:
    cmd = invoer.pop("commando")
    proces = subprocess.run(
        [str(PY), str(ADAPTER), cmd],
        input=json.dumps(invoer), capture_output=True, text=True, timeout=60)
    if proces.returncode != 0:
        raise AssertionError(f"adapter faalde: {proces.stderr[-300:]}")
    return json.loads(proces.stdout)


class TestFamilieRegister(unittest.TestCase):
    def test_status_geeft_zeven_familieleden(self):
        uit = roep({"commando": "familie", "actie": "status"})
        self.assertTrue(uit["ok"])
        namen = [a["naam"] for a in uit["data"]["familie"]]
        self.assertEqual(namen, ["KairOS", "Riri", "Vigil", "Libra",
                                 "Memoria", "Codex", "Genius"])

    def test_iedereen_heeft_rol_en_platform(self):
        uit = roep({"commando": "familie", "actie": "status"})
        for agent in uit["data"]["familie"]:
            self.assertTrue(agent.get("rol"), f"{agent['naam']} mist rol")
            self.assertEqual(agent.get("platform"), "telegram")

    def test_genius_is_de_observer(self):
        uit = roep({"commando": "familie", "actie": "status"})
        genius = [a for a in uit["data"]["familie"] if a["naam"] == "Genius"][0]
        self.assertEqual(genius["rol"], "observer")

    def test_limiet_blijft_op_acht(self):
        uit = roep({"commando": "familie", "actie": "status"})
        self.assertEqual(uit["data"]["limieten"]["max_agents"], 8)
        self.assertLessEqual(len(uit["data"]["familie"]), 8)

    def test_onbekende_actie_is_nette_fout(self):
        proces = subprocess.run(
            [str(PY), str(ADAPTER), "familie"],
            input=json.dumps({"actie": "verwijder"}),
            capture_output=True, text=True, timeout=60)
        self.assertEqual(proces.returncode, 1)
        uit = json.loads(proces.stdout)
        self.assertFalse(uit["ok"])
        self.assertIn("fout", uit)


if __name__ == "__main__":
    unittest.main()
