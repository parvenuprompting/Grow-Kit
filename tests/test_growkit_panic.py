# tests/test_growkit_panic.py — TDD EERST (rood)
# De PANIC-knop: pauzeert alles, logt append-only, herstelt nooit automatisch.
import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from kern.growkit_panic import activeer_panic, herstel_na_panic, is_panic_actief, lees_status


class PanicTests(unittest.TestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.doel = Path(self.tmp.name) / "boom"
        self.doel.mkdir()
        self.logboek = self.doel / "logboek.json"
        self.logboek.write_text("[]", encoding="utf-8")

    def tearDown(self):
        self.tmp.cleanup()

    def test_activeer_panic_schrijft_status_en_logt(self):
        activeer_panic(self.doel, reden="test-simulatie")
        status = lees_status(self.doel)
        self.assertTrue(status["actief"])
        self.assertEqual(status["reden"], "test-simulatie")
        entries = json.loads(self.logboek.read_text(encoding="utf-8"))
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]["stap"], "PANIC")
        self.assertEqual(entries[0]["status"], "panic_actief")

    def test_panic_is_append_only_herstel_is_nieuwe_entry(self):
        activeer_panic(self.doel, reden="r1")
        herstel_na_panic(self.doel)
        entries = json.loads(self.logboek.read_text(encoding="utf-8"))
        self.assertEqual(len(entries), 2)  # geen verwijderde entries
        self.assertEqual(entries[0]["status"], "panic_actief")
        self.assertEqual(entries[1]["status"], "panic_hersteld")

    def test_is_panic_actief_na_herstel_is_false(self):
        activeer_panic(self.doel, reden="x")
        self.assertTrue(is_panic_actief(self.doel))
        herstel_na_panic(self.doel)
        self.assertFalse(is_panic_actief(self.doel))

    def test_status_bestand_wordt_geschreven_in_doel(self):
        activeer_panic(self.doel, reden="y")
        status_path = self.doel / "panic_status.json"
        self.assertTrue(status_path.exists())
        d = json.loads(status_path.read_text(encoding="utf-8"))
        self.assertIn("actief", d)
        self.assertIn("reden", d)
        self.assertIn("tijdstip", d)

    def test_herstel_zonder_panic_is_geen_fout(self):
        # idempotent: herstel zonder actieve panic doet niets maar crasht niet
        herstel_na_panic(self.doel)
        entries = json.loads(self.logboek.read_text(encoding="utf-8"))
        self.assertEqual(len(entries), 0)

    def test_activeer_twee_keer_overschrijft_reden_append_only_behouden(self):
        activeer_panic(self.doel, reden="eerste")
        activeer_panic(self.doel, reden="tweede")
        status = lees_status(self.doel)
        self.assertEqual(status["reden"], "tweede")
        entries = json.loads(self.logboek.read_text(encoding="utf-8"))
        # beide panics zijn gelogd (append-only), status-bestand toont de laatste
        self.assertEqual(len(entries), 2)
