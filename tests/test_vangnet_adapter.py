#!/usr/bin/env python3
"""Tests: vangnet-status via de adapter (models-stijl: JSON in/uit, nette fouten)."""
import json
import sys
import sqlite3
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).parent.parent
sys.path.insert(0, str(REPO))

from kern import growkit_vangnet as gv


def roep(invoer: dict):
    import io
    from contextlib import redirect_stdout
    import adapter
    buf = io.StringIO()
    code = 0
    with redirect_stdout(buf):
        import sys as s
        s.stdin = io.StringIO(json.dumps(invoer))
        code = adapter.main(["vangnet"]) or 0
    return int(code), json.loads(buf.getvalue().strip())


class TestVangnetStatus(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.doel = Path(self.tmp.name) / "boom"
        self.doel.mkdir()
        self.vangnet = self.doel / "vangnet"
        gv.vang_stap(self.vangnet, "s1", "geslaagd", "shell_check: OK")
        gv.vang_stap(self.vangnet, "s2", "gefaald", "shell_check: mist")
        gv.vang(self.vangnet, "review", "m1", {"rol": "reviewer"}, {"antwoord": "geslaagd"},
                oordeel="geslaagd")

    def tearDown(self):
        self.tmp.cleanup()

    def test_status_telt_per_bron(self):
        code, uit = roep({"doel": str(self.doel)})
        self.assertEqual(code, 0)
        data = uit["data"]
        self.assertEqual(data["totaal"], 3)
        per_bron = {r["bron"]: r["aantal"] for r in data["per_bron"]}
        self.assertEqual(per_bron["stap"], 2)
        self.assertEqual(per_bron["review"], 1)

    def test_status_toont_recente(self):
        code, uit = roep({"doel": str(self.doel)})
        recente = uit["data"]["recente"]
        self.assertEqual(len(recente), 3)
        self.assertIn("bron", recente[0])
        self.assertIn("oordeel", recente[0])

    def test_leeg_vangnet_is_net_antwoord(self):
        leeg = Path(self.tmp.name) / "leeg"
        leeg.mkdir()
        code, uit = roep({"doel": str(leeg)})
        self.assertEqual(uit["data"]["totaal"], 0)
        self.assertEqual(uit["data"]["recente"], [])

    def test_ontbrekend_vangnet_meldt_dat(self):
        nergens = Path(self.tmp.name) / "nergens"
        nergens.mkdir()
        code, uit = roep({"doel": str(nergens)})
        self.assertTrue(uit["ok"])
        self.assertEqual(uit["data"]["bestaat"], False)


if __name__ == "__main__":
    unittest.main()
