#!/usr/bin/env python3
"""Tests voor de agent-governor (kern/growkit_agents.py).

De vijf regels: 2 taken per agent · subagent bij meer · controle vóór
vrijlating · observer voert niets uit · max 8 agents / 16 taken.
"""
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).parent.parent
sys.path.insert(0, str(REPO))

from kern import growkit_agents as ag


class Basis(unittest.TestCase):
    def setUp(self):
        self.reg = ag.nieuw_register()

    def test_observer_bestaat_altijd_en_draagt_niets(self):
        self.assertIn(ag.OBSERVER_NAAM, self.reg["agents"])
        self.assertEqual(self.reg["agents"][ag.OBSERVER_NAAM]["rol"], "observer")


class Regel2Taken(unittest.TestCase):
    def setUp(self):
        self.reg = ag.nieuw_register()

    def test_twee_taken_gaan_goed(self):
        reg, ok, _ = ag.meld_taak_aan(self.reg, "kairos", "t1")
        reg, ok2, _ = ag.meld_taak_aan(reg, "kairos", "t2")
        self.assertTrue(ok and ok2)

    def test_derde_taak_wordt_geweigerd(self):
        reg, _, _ = ag.meld_taak_aan(self.reg, "kairos", "t1")
        reg, _, _ = ag.meld_taak_aan(reg, "kairos", "t2")
        reg, ok, reden = ag.meld_taak_aan(reg, "kairos", "t3")
        self.assertFalse(ok)
        self.assertIn("2 taken", reden)

    def test_taak_bestaat_maar_een_keer(self):
        reg, ok, _ = ag.meld_taak_aan(self.reg, "kairos", "t1")
        reg, ok2, _ = ag.meld_taak_aan(reg, "vigil", "t1")
        self.assertFalse(ok2)


class RegelSubagent(unittest.TestCase):
    def setUp(self):
        self.reg = ag.nieuw_register()
        for t in ("t1", "t2"):
            self.reg, _, _ = ag.meld_taak_aan(self.reg, "kairos", t)

    def test_subagent_pas_bij_limiet(self):
        # kairos zit op de limiet (2 taken) — subagent moet lukken
        reg, ok, reden = ag.vorm_subagent(self.reg, "kairos")
        self.assertTrue(ok)
        self.assertIn("subagent-1", reg["agents"])
        # en de subagent kan taken dragen
        reg, ok, _ = ag.meld_taak_aan(reg, "subagent-1", "t3")
        self.assertTrue(ok)

    def test_subagent_niet_voordat_limiet_bereikt_is(self):
        reg, _, _ = ag.meld_taak_aan(self.reg, "vigil", "v1")   # vigil: 1 taak
        reg, ok, reden = ag.vorm_subagent(reg, "vigil")
        self.assertFalse(ok)
        self.assertIn("niet nodig", reden)

    def test_subagent_heeft_zelfde_limiet(self):
        reg, _, _ = ag.vorm_subagent(self.reg, "kairos")
        reg, _, _ = ag.meld_taak_aan(reg, "subagent-1", "t3")
        reg, _, _ = ag.meld_taak_aan(reg, "subagent-1", "t4")
        reg, ok, _ = ag.meld_taak_aan(reg, "subagent-1", "t5")
        self.assertFalse(ok)


class RegelControle(unittest.TestCase):
    def setUp(self):
        self.reg = ag.nieuw_register()
        self.reg, _, _ = ag.meld_taak_aan(self.reg, "kairos", "t1")

    def test_taak_klaar_is_niet_af(self):
        reg, ok, _ = ag.taak_afgerond(self.reg, "kairos", "t1", bewijs="tests groen")
        self.assertTrue(ok)
        self.assertEqual(reg["taken"]["t1"]["status"], "wacht_op_controle")

    def test_goedkeuring_vrijlaat_subagent(self):
        reg, _, _ = ag.vorm_subagent(self.reg, "kairos")
        reg, _, _ = ag.meld_taak_aan(reg, "subagent-1", "t3")
        reg, _, _ = ag.taak_afgerond(reg, "subagent-1", "t3")
        reg, ok, bericht = ag.keur_taak(reg, "t3", goed=True)
        self.assertTrue(ok)
        self.assertTrue(reg["agents"]["subagent-1"].get("vrijgelaten"))
        self.assertIn("vrijgelaten", bericht)

    def test_afkeuring_zet_terug_naar_open(self):
        reg, _, _ = ag.taak_afgerond(self.reg, "kairos", "t1")
        reg, ok, _ = ag.keur_taak(reg, "t1", goed=False, reden="test faalde")
        self.assertTrue(ok)
        self.assertEqual(reg["taken"]["t1"]["status"], "open")
        self.assertIn("t1", reg["agents"]["kairos"]["open"])


class RegelObserver(unittest.TestCase):
    def setUp(self):
        self.reg = ag.nieuw_register()

    def test_observer_krijgt_geen_taken(self):
        reg, ok, reden = ag.meld_taak_aan(self.reg, "observer", "t1")
        self.assertFalse(ok)
        self.assertIn("observer", reden.lower())

    def test_observer_kan_alleen_melden(self):
        reg, ok, _ = ag.melding_van_observer(self.reg, "Aandacht: limiet bereikt bij taken X")
        self.assertTrue(ok)
        self.assertEqual(len(reg["observer_meldingen"]), 1)


class RegelLimieten(unittest.TestCase):
    def setUp(self):
        self.reg = ag.nieuw_register()

    def _vul_tot_limiet(self):
        reg = self.reg
        # 8 agents × 2 taken: hoofd-agent + subagents
        for i in range(1, 9):
            agent = "hoofd" if i == 1 else f"subagent-{i-1}"
            if i > 1:
                reg, ok, _ = ag.vorm_subagent(reg, "hoofd")
                if not ok:
                    break
                agent = f"subagent-{i-1}"
            reg, _, _ = ag.meld_taak_aan(reg, agent, f"t{i}a")
            reg, _, _ = ag.meld_taak_aan(reg, agent, f"t{i}b")
        return reg

    def test_max_acht_agents(self):
        reg = self._vul_tot_limiet()
        agents = ag._bestaande_agents(reg)
        self.assertLessEqual(agents, ag.MAX_AGENTS)

    def test_meer_dan_16_taken_is_gretig_en_wordt_geweigerd(self):
        reg = self._vul_tot_limiet()
        # probeer nog een taak via een nieuwe agent
        reg, ok, reden = ag.meld_taak_aan(reg, "gretige-agent", "extra")
        self.assertFalse(ok)
        self.assertIn("Limiet", reden)

    def test_constanten_kloppen_met_afspraak(self):
        self.assertEqual(ag.MAX_TAKEN_PER_AGENT, 2)
        self.assertEqual(ag.MAX_AGENTS, 8)
        self.assertEqual(ag.MAX_TAKEN_TOTAAL, 16)


if __name__ == "__main__":
    unittest.main()
