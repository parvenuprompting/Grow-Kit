"""Testen voor de CyberSeed-kern (kern/growkit_cyberseed.py).

CyberSeed Sprout v0.5 — het lokale model met een zelfbijgewerkte SOUL.
Basis: Ollama op localhost:11434 (OpenAI-compatibel HTTP). Alles lokaal;
de SOUL-snapshot komt uit bestaande GrowKit-bronnen (≤ 4000 tokens);
de chatlog is append-only JSONL; wissen vereist bevestiging.
"""
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from kern import growkit_cyberseed as cs


class TestConstanten(unittest.TestCase):
    def test_modelnaam_en_basis(self):
        self.assertEqual(cs.MODEL_NAAM, "cyberseed-sprout-v0.5")
        self.assertEqual(cs.BASIS_MODEL_DEFAULT, "qwen3:8b")
        self.assertEqual(cs.OLLAMA_URL, "http://localhost:11434")


class TestOllamaStatus(unittest.TestCase):
    def test_draait_met_modellen(self):
        payload = json.dumps({"models": [
            {"name": "qwen3:8b"}, {"name": "bge-m3:latest"}]}).encode()
        with mock.patch.object(cs, "_http_get", return_value=(200, payload)):
            s = cs.ollama_status()
        self.assertTrue(s["draait"])
        self.assertIn("qwen3:8b", s["modellen"])
        self.assertTrue(s["sprout_basis_aanwezig"])

    def test_ollama_uit_geen_crash(self):
        with mock.patch.object(cs, "_http_get",
                               side_effect=OSError("connection refused")):
            s = cs.ollama_status()
        self.assertFalse(s["draait"])
        self.assertEqual(s["modellen"], [])
        self.assertFalse(s["sprout_basis_aanwezig"])


class TestSoulSnapshot(unittest.TestCase):
    def test_snapshot_heeft_vaste_kop_en_secties(self):
        bronnen = {
            "profiel": "Naam: Tiëndo. Baas van de familie.",
            "ratificaties": [],
            "saldo": "€ 11.89",
            "audit": ["2026-09-06 20:00 · GrowKit ronde afgerond"],
            "bomen": ["growkit-hoofd (actief)"],
        }
        with mock.patch.object(cs, "_verzamel_bronnen", return_value=bronnen):
            snap = cs.soul_snapshot()
        self.assertTrue(snap.startswith("# CyberSeed SOUL · snapshot "))
        for sectie in ("## Wie ik dien", "## Wacht op de mens",
                       "## Saldo", "## Laatste werk", "## Actieve projecten"):
            self.assertIn(sectie, snap)

    def test_snapshot_deterministisch_bij_zelfde_invoer(self):
        bronnen = {"profiel": "X", "ratificaties": [], "saldo": "€ 1",
                   "audit": ["a"], "bomen": ["b"]}
        with mock.patch.object(cs, "_verzamel_bronnen", return_value=bronnen):
            a = cs.soul_snapshot()
            b = cs.soul_snapshot()
        # alleen het tijdstempel verschilt; de rest is gelijk
        self.assertEqual(a.split("\n", 1)[1], b.split("\n", 1)[1])

    def test_snapshot_wordt_afgekapt_op_limiet(self):
        bronnen = {"profiel": "x" * 20000, "ratificaties": [], "saldo": "€ 1",
                   "audit": [], "bomen": []}
        with mock.patch.object(cs, "_verzamel_bronnen", return_value=bronnen):
            snap = cs.soul_snapshot()
        self.assertLessEqual(len(snap), cs.SOUL_MAX_TEKENS)


class TestSoulBewaar(unittest.TestCase):
    def test_bewaar_en_leeftijd(self):
        with tempfile.TemporaryDirectory() as tmp:
            with mock.patch.object(cs, "_basis_pad", return_value=Path(tmp)):
                cs.soul_bewaar("# CyberSeed SOUL · snapshot 2026\n## Wie ik dien\nX")
                pad = Path(tmp) / "SOUL.md"
                self.assertTrue(pad.exists())
                leeftijd = cs.soul_leeftijd_uren()
                self.assertIsNotNone(leeftijd)
                self.assertLess(leeftijd, 0.01)

    def test_geen_soul_geeft_none(self):
        with tempfile.TemporaryDirectory() as tmp:
            with mock.patch.object(cs, "_basis_pad", return_value=Path(tmp)):
                self.assertIsNone(cs.soul_leeftijd_uren())


class TestChat(unittest.TestCase):
    def _ollama_antwoord(self):
        return json.dumps({
            "message": {"role": "assistant", "content": "Hallo Tiëndo."}
        }).encode()

    def test_chat_geeft_antwoord_en_logt(self):
        with tempfile.TemporaryDirectory() as tmp:
            with mock.patch.object(cs, "_basis_pad", return_value=Path(tmp)), \
                 mock.patch.object(cs, "_http_post",
                                   return_value=(200, self._ollama_antwoord())), \
                 mock.patch.object(cs, "soul_lees",
                                   return_value="# CyberSeed SOUL"):
                antw = cs.chat("Wie ben je?", van="Tiëndo")
            self.assertEqual(antw, "Hallo Tiëndo.")
            logpad = Path(tmp) / "chatlog.jsonl"
            regels = logpad.read_text().strip().splitlines()
            self.assertEqual(len(regels), 2)  # gebruiker + assistent
            eerste = json.loads(regels[0])
            self.assertEqual(eerste["rol"], "gebruiker")
            self.assertEqual(eerste["tekst"], "Wie ben je?")
            # SOUL-inhoud is NIET gelogd (privacy + omvang)
            self.assertNotIn("CyberSeed SOUL", logpad.read_text())

    def test_chat_met_ollama_uit_gooit_netjes(self):
        with tempfile.TemporaryDirectory() as tmp:
            with mock.patch.object(cs, "_basis_pad", return_value=Path(tmp)), \
                 mock.patch.object(cs, "_http_post",
                                   side_effect=OSError("connection refused")):
                with self.assertRaises(ConnectionError):
                    cs.chat("hoi", van="Tiëndo")


class TestChatlog(unittest.TestCase):
    def test_lees_en_wis_met_bevestiging(self):
        with tempfile.TemporaryDirectory() as tmp:
            with mock.patch.object(cs, "_basis_pad", return_value=Path(tmp)), \
                 mock.patch.object(cs, "_http_post",
                                   return_value=(200, json.dumps(
                                       {"message": {"content": "ok"}}).encode())), \
                 mock.patch.object(cs, "soul_lees", return_value="S"):
                cs.chat("a", van="X")
                cs.chat("b", van="X")
                alles = cs.chatlog_lees(10)
                self.assertEqual(alles[-1]["tekst"], "ok")   # assistent
                self.assertEqual(alles[-2]["tekst"], "b")    # gebruiker
                # wissen zonder bevestiging wordt geweigerd
                with self.assertRaises(PermissionError):
                    cs.chatlog_wis()
                cs.chatlog_wis(bevestig=True)
                self.assertEqual(cs.chatlog_lees(10), [])


if __name__ == "__main__":
    unittest.main()
