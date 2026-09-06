"""Testen voor de Telegram-koppel-kern (kern/growkit_telegram.py).

Wizard-data: voortgang per agent (6 stappen per bot + 2 groep-stappen),
tokens één keer invoeren → Sleutelhangar, nooit terug te lezen in de app
en nooit op schijf in de wizard-state.
"""
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from kern import growkit_telegram as tg

FAMILIE = ["kairos", "riri", "vigil", "libra", "memoria", "codex", "genius"]


class TestWizardData(unittest.TestCase):
    def test_zeven_agents_in_vaste_volgorde(self):
        self.assertEqual(tg.FAMILIE, FAMILIE)

    def test_stappenlijst_per_agent(self):
        stappen = tg.stappen_voor("kairos")
        self.assertEqual(len(stappen), 6)
        self.assertIn("BotFather", stappen[0])
        self.assertIn("token", stappen[1].lower())
        self.assertIn("herstart", stappen[4].lower())
        self.assertIn("/status", stappen[5])

    def test_groep_stappen(self):
        stappen = tg.groep_stappen()
        self.assertEqual(len(stappen), 2)
        self.assertIn("groep", stappen[0].lower())
        self.assertIn("verdeelregel", stappen[1].lower())


class TestVoortgang(unittest.TestCase):
    def test_voortgang_bewaren_en_lezen(self):
        with tempfile.TemporaryDirectory() as tmp:
            with mock.patch.object(tg, "_voortgang_pad",
                                   return_value=Path(tmp) / "wizard.json"):
                tg.markeer_klaar("kairos", 1)
                tg.markeer_klaar("kairos", 2)
                stand = tg.voortgang()
                self.assertEqual(stand.get("kairos"), [1, 2])
                self.assertNotIn("riri", stand)

    def test_token_wordt_niet_in_voortgang_bewaard(self):
        with tempfile.TemporaryDirectory() as tmp:
            pad = Path(tmp) / "wizard.json"
            with mock.patch.object(tg, "_voortgang_pad", return_value=pad), \
                 mock.patch.object(tg, "bewaar_token", return_value=True) as bewaar:
                tg.markeer_klaar("kairos", 2, token="123456:ABC-DEF")
                raw = pad.read_text()
                self.assertNotIn("ABC-DEF", raw)     # token lekt niet in state
                bewaar.assert_called_once()           # en ging wél naar de hangar-laag


class TestKeychain(unittest.TestCase):
    def setUp(self):
        import sys
        if sys.platform != "darwin":
            self.skipTest("Keychain is macOS-only")

    def test_token_naar_keychain(self):
        with mock.patch.object(tg.subprocess, "run") as nep:
            nep.return_value = mock.Mock(returncode=0)
            ok = tg.bewaar_token("kairos", "123456:ABC-DEF")
            self.assertTrue(ok)
            cmd = nep.call_args[0][0]
            self.assertEqual(cmd[0], "security")
            self.assertIn("GrowKit Telegram: kairos", " ".join(cmd))

    def test_mask_toont_alleen_achterste_4(self):
        with mock.patch.object(tg.subprocess, "run") as nep:
            nep.return_value = mock.Mock(returncode=0, stdout="123456:ABC-DEF\n")
            self.assertEqual(tg.toon_token_mask("kairos"), "••••-DEF")

    def test_mask_zonder_token_geeft_vraagtekens(self):
        with mock.patch.object(tg.subprocess, "run") as nep:
            nep.return_value = mock.Mock(returncode=44, stdout="")
            self.assertEqual(tg.toon_token_mask("kairos"), "niet ingesteld")


if __name__ == "__main__":
    unittest.main()
