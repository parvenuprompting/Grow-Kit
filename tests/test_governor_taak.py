#!/usr/bin/env python3
"""Tests: governor aan taak-uitvoering gekoppeld (slice 10).

Het spoor: taak starten → governor 'aanmelden'; motor klaar → 'afronden'
(wacht_op_controle); menselijke controle → 'goedgekeurd' (+ subagent
vrijgelaten indien werkloos). De taken-modus van de adapter regelt dit
vanzelf wanneer de governor is aangezet; zonder governor verandert niets.
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


def _governor_pad(doel: Path) -> Path:
    return doel / "governor.json"


def _doel_met_taak(taak_id: str = "t1") -> Path:
    tmp = Path(tempfile.mkdtemp())
    taak = {"id": taak_id, "titel": "testtaak",
            "commando": "echo KWEEK-OK",
            "bewijs": {"type": "shell_check", "commando": "echo KWEEK-OK",
                       "verwacht_substr": "KWEEK-OK"}}
    (tmp / "takenlijst.json").write_text(json.dumps([taak]), encoding="utf-8")
    return tmp


class TestTaakGovernorSpoor(unittest.TestCase):
    def setUp(self):
        self.doel = Path(tempfile.mkdtemp())
        # geen bestaand register: de taken-modus vormt er zelf een
        self.pad = _governor_pad(self.doel)

    def test_zonder_governor_gedrag_ongewijzigd(self):
        import contextlib, io
        from kern.growkit_review import laad_reviewconfig
        with contextlib.redirect_stdout(io.StringIO()):
            geslaagd, bevindingen = voer_taak_uit(self.doel, {"id": "t1",
                "commando": "echo KWEEK-OK",
                "bewijs": {"type": "shell_check", "commando": "echo KWEEK-OK",
                           "verwacht_substr": "KWEEK-OK"}})
        self.assertTrue(geslaagd)
        self.assertFalse(self.pad.exists())  # geen register gevormd

    def test_met_governor_loopt_het_hele_spoor(self):
        """aanmelden → afronden (wacht) → controle goed → vrijgelaten (subagent)."""
        import contextlib, io
        from kern import growkit_agents as ag

        # 1. taak aanmelden bij een subagent (binnen de gouverneursregels):
        # kairos zit op zijn 2-takenlimiet → vormt subagent-1 → die draagt t1.
        reg = ag.nieuw_register()
        reg, ok, _ = ag.meld_taak_aan(reg, "kairos", "ander")
        self.assertTrue(ok)
        reg, ok, _ = ag.meld_taak_aan(reg, "kairos", "ander2")
        self.assertTrue(ok)
        reg, ok, _ = ag.vorm_subagent(reg, "kairos")
        self.assertTrue(ok)
        reg, ok, reden = ag.meld_taak_aan(reg, "subagent-1", "t1")
        self.assertTrue(ok, reden)  # subagent draagt de taak
        # sla op zoals de adapter dat doet
        self.pad.write_text(json.dumps(reg), encoding="utf-8")

        # 2. taak uitvoeren mét governor: afronden wordt vanzelf geboekt
        with contextlib.redirect_stdout(io.StringIO()):
            geslaagd, _ = voer_taak_uit(
                self.doel, {"id": "t1", "commando": "echo KWEEK-OK",
                            "bewijs": {"type": "shell_check",
                                       "commando": "echo KWEEK-OK",
                                       "verwacht_substr": "KWEEK-OK"}},
                reviewconfig=None, governor_pad=self.pad, agent="subagent-1")
        self.assertTrue(geslaagd)
        reg2 = json.loads(self.pad.read_text(encoding="utf-8"))
        self.assertEqual(reg2["taken"]["t1"]["status"], "wacht_op_controle")

        # 3. mens keurt goed in de app → subagent vrijgelaten
        reg3, ok, reden = ag.keur_taak(reg2, "t1", goed=True)
        self.assertTrue(ok)
        self.assertTrue(reg3["agents"]["subagent-1"].get("vrijgelaten"))

    def test_governor_bereikt_laat_taak_niet_draaien(self):
        """Weigering van de governor = geen motor-start (poortgetrouw)."""
        with contextlib.redirect_stdout(io.StringIO()):
            geslaagd, bevindingen = voer_taak_uit(
                self.doel, {"id": "t1", "commando": "echo KWEEK-OK",
                            "bewijs": {"type": "shell_check",
                                       "commando": "echo KWEEK-OK",
                                       "verwacht_substr": "KWEEK-OK"}},
                governor_pad=self.pad, agent="observer", vereist_governor=True)
        self.assertFalse(geslaagd)
        self.assertTrue(any("observer" in b for b in bevindingen))


if __name__ == "__main__":
    unittest.main()