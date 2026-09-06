"""Adapter-tests voor CyberSeed: status, soul, chat, log, wis."""
import json
import sys
import unittest
from pathlib import Path
from unittest import mock

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

import adapter
from kern import growkit_cyberseed as cs


class TestCyberseedCommandos(unittest.TestCase):
    def test_status_geeft_ollama_en_soul_leeftijd(self):
        with mock.patch.object(cs, "ollama_status",
                               return_value={"draait": True,
                                             "modellen": ["qwen3:8b"],
                                             "sprout_basis_aanwezig": True}), \
             mock.patch.object(cs, "soul_leeftijd_uren", return_value=2.5):
            r = adapter.COMMANDOS["cyberseedstatus"]({})
        self.assertTrue(r["ok"])
        self.assertTrue(r["data"]["draait"])
        self.assertEqual(r["data"]["soul_leeftijd_uren"], 2.5)
        self.assertEqual(r["data"]["model_naam"], cs.MODEL_NAAM)

    def test_soul_genereert_en_bewaart(self):
        with mock.patch.object(cs, "verfris_soul", return_value=0.0), \
             mock.patch.object(cs, "soul_lees", return_value="# SOUL"):
            r = adapter.COMMANDOS["cyberseedsoul"]({"actie": "genereer"})
            self.assertTrue(r["ok"])
            r2 = adapter.COMMANDOS["cyberseedsoul"]({"actie": "lees"})
            self.assertEqual(r2["data"]["soul"], "# SOUL")

    def test_chat_stuurt_van_door_en_scant_secrets(self):
        with mock.patch.object(cs, "chat", return_value="hoi") as chat_mock:
            r = adapter.COMMANDOS["cyberseedchat"](
                {"bericht": "dag", "van": "Tiëndo"})
        self.assertTrue(r["ok"])
        self.assertEqual(r["data"]["antwoord"], "hoi")
        chat_mock.assert_called_once_with("dag", van="Tiëndo", model="")
        # secret in bericht wordt geweigerd (scanner vóór de kern)
        with mock.patch.object(cs, "chat", return_value="x"):
            with self.assertRaises(adapter.AdapterFout):
                adapter.COMMANDOS["cyberseedchat"](
                    {"bericht": "key sk-abcdef1234567890abcdef", "van": "X"})

    def test_wis_zonder_bevestiging_weigert(self):
        with mock.patch.object(cs, "chatlog_wis",
                               side_effect=PermissionError("bevestig=True")):
            with self.assertRaises(adapter.AdapterFout):
                adapter.COMMANDOS["cyberseedwis"]({})
        with mock.patch.object(cs, "chatlog_wis") as wis:
            r2 = adapter.COMMANDOS["cyberseedwis"]({"bevestig": True})
        self.assertTrue(r2["ok"])
        wis.assert_called_once_with(bevestig=True)

    def test_log_geeft_regels(self):
        with mock.patch.object(cs, "chatlog_lees",
                               return_value=[{"rol": "gebruiker", "tekst": "a"}]):
            r = adapter.COMMANDOS["cyberseedlog"]({"aantal": 5})
        self.assertTrue(r["ok"])
        self.assertEqual(len(r["data"]["regels"]), 1)


if __name__ == "__main__":
    unittest.main()
