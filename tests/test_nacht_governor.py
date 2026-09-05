#!/usr/bin/env python3
"""Tests: nachtronde onder de governor (slice 11).

De nachtronde krijgt een optionele agent: mét agent lopen alle nachtelijke
taken door het governerspoor (aanmelden → afronden → wacht_op_controle) en
komt elk resultaat in het ochtendrapport. Zonder agent: gedrag ongewijzigd.
"""
import contextlib
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).parent.parent
sys.path.insert(0, str(REPO))

from kern import growkit_agents as ag
from kern.growkit_taken import voer_taak_uit

OK_TAAK = {"id": "n1", "titel": "nachttaak", "commando": "echo KWEEK-OK",
           "bewijs": {"type": "shell_check", "commando": "echo KWEEK-OK",
                      "verwacht_substr": "KWEEK-OK"}}


class TestNachtMetGovernor(unittest.TestCase):
    def setUp(self):
        self.doel = Path(tempfile.mkdtemp())
        (self.doel / "takenlijst.json").write_text(json.dumps([OK_TAAK]), encoding="utf-8")
        self.pad = self.doel / "governor.json"

    def test_nachttaak_loopt_governorspoor(self):
        reg = ag.nieuw_register()
        reg, ok, _ = ag.meld_taak_aan(reg, "nacht-agent", "n1")
        self.assertTrue(ok)
        self.pad.write_text(json.dumps(reg), encoding="utf-8")

        with contextlib.redirect_stdout(io.StringIO()):
            geslaagd, _ = voer_taak_uit(self.doel, dict(OK_TAAK),
                                        governor_pad=self.pad, agent="nacht-agent")
        self.assertTrue(geslaagd)
        reg2 = json.loads(self.pad.read_text(encoding="utf-8"))
        self.assertEqual(reg2["taken"]["n1"]["status"], "wacht_op_controle")
        # de mens keurt 's ochtends in de app:
        reg3, ok, _ = ag.keur_taak(reg2, "n1", goed=True)
        self.assertTrue(ok)
        self.assertEqual(reg3["taken"]["n1"]["status"], "goedgekeurd")

    def test_observatie_in_vangnet_en_governor(self):
        """Na de nachttaak staan zowel het vangnet als de governor gevuld."""
        reg = ag.nieuw_register()
        reg, _, _ = ag.meld_taak_aan(reg, "nacht-agent", "n1")
        self.pad.write_text(json.dumps(reg), encoding="utf-8")
        with contextlib.redirect_stdout(io.StringIO()):
            voer_taak_uit(self.doel, dict(OK_TAAK), governor_pad=self.pad,
                          agent="nacht-agent")
        # vangnet ving de stap
        from kern import growkit_vangnet
        self.assertEqual(growkit_vangnet.tel(self.doel / "vangnet"), 1)
        # governor wacht op controle
        reg2 = json.loads(self.pad.read_text(encoding="utf-8"))
        self.assertEqual(reg2["taken"]["n1"]["status"], "wacht_op_controle")

    def test_ochtendrapport_bevat_governor_status(self):
        """Het register bevat wacht_op_controle-taken voor het ochtendrapport."""
        reg = ag.nieuw_register()
        reg, _, _ = ag.meld_taak_aan(reg, "nacht-agent", "n1")
        self.pad.write_text(json.dumps(reg), encoding="utf-8")
        reg2, ok, _ = ag.taak_afgerond(reg, "nacht-agent", "n1")
        self.pad.write_text(json.dumps(reg2), encoding="utf-8")
        wachtend = [tid for tid, t in reg2["taken"].items()
                    if t.get("status") == "wacht_op_controle"]
        self.assertEqual(wachtend, ["n1"])


if __name__ == "__main__":
    unittest.main()
