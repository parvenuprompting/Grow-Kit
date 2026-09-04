#!/usr/bin/env python3
"""Tests voor GrowKit Vangnet — fase 1 (vastleggen, fail-open, nul-inbreng)."""
import json
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).parent.parent
sys.path.insert(0, str(REPO))

from kern import growkit_vangnet
from kern import growkit_motor


class TestVangnetVastleggen(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.doel = Path(self.tmp.name) / "boom"
        self.doel.mkdir()
        self.vangnet = self.doel / "vangnet"

    def tearDown(self):
        self.tmp.cleanup()

    def test_stap_wordt_vastgelegd_met_taak_en_oordeel(self):
        growkit_vangnet.vang_stap(self.vangnet, "stap-1", "geslaagd", "shell_check: OK")
        self.assertEqual(growkit_vangnet.tel(self.vangnet), 1)
        con = growkit_vangnet.sqlite3.connect(self.vangnet / "vangnet.db")
        rij = con.execute("SELECT bron, taak, oordeel FROM vangsten").fetchone()
        con.close()
        self.assertEqual(rij, ("stap", "stap-1", "geslaagd"))

    def test_review_wordt_vastgelegd_met_rol(self):
        stap = {"id": "mens-1", "mens_nodig": {"instructie": "keur dit"}}
        growkit_vangnet.vang_review(self.vangnet, "reviewer", stap, "keur dit", "geslaagd")
        con = growkit_vangnet.sqlite3.connect(self.vangnet / "vangnet.db")
        rij = con.execute("SELECT bron, taak, oordeel FROM vangsten").fetchone()
        con.close()
        self.assertEqual(rij, ("review", "mens-1", "geslaagd"))

    def test_secrets_worden_gehasht_niet_bewaard(self):
        growkit_vangnet.vang(self.vangnet, "review", "t",
                             {"rol": "r", "api_key": "geheim-123"})
        con = growkit_vangnet.sqlite3.connect(self.vangnet / "vangnet.db")
        rij = con.execute("SELECT input_json FROM vangsten").fetchone()
        con.close()
        self.assertNotIn("geheim-123", rij[0])

    def test_tel_met_bron_filter(self):
        growkit_vangnet.vang_stap(self.vangnet, "s1", "geslaagd", "ok")
        growkit_vangnet.vang(self.vangnet, "review", "s2", {"x": 1})
        self.assertEqual(growkit_vangnet.tel(self.vangnet, bron="stap"), 1)
        self.assertEqual(growkit_vangnet.tel(self.vangnet, bron="review"), 1)


class TestFailOpen(unittest.TestCase):
    """Vangnet-regel 2: faalt het, dan gaat de loop door."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.doel = Path(self.tmp.name) / "boom"
        self.doel.mkdir()

    def tearDown(self):
        self.tmp.cleanup()

    def test_vang_op_ongeldig_pad_gooit_niets(self):
        # Een pad waar geen map gemaakt kan worden: geen exception, geen crash.
        growkit_vangnet.vang(Path("/proc/onzin/vangnet"), "stap", "t", {"x": 1})

    def test_motor_gaat_door_bij_dood_vangnet(self):
        # Vangnet wijst naar een pad dat geen DB kan worden (een bestand op de plek van de map).
        blokkade = self.doel / "vangnet"
        blokkade.write_text("geen map", encoding="utf-8")
        profiel = {"profiel": "t", "stappen": [
            {"id": "s1", "commando": "echo KWEEK-OK",
             "bewijs": {"type": "shell_check", "commando": "echo KWEEK-OK",
                        "verwacht_substr": "KWEEK-OK"}}]}
        logboek = self.doel / "logboek.json"
        logboek.write_text("[]", encoding="utf-8")
        ok = growkit_motor.voer_uit(profiel, self.doel, logboek, None,
                                    vangnet=blokkade)
        self.assertTrue(ok)  # de run slaagde ondanks een dichtgeklapte vangnet-map


class TestAansluitpunt(unittest.TestCase):
    """De loop vangt automatisch mee wanneer vangnet is gezet; zonder, niets."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.doel = Path(self.tmp.name) / "boom"
        self.doel.mkdir()

    def tearDown(self):
        self.tmp.cleanup()

    def _profiel(self):
        return {"profiel": "t", "stappen": [
            {"id": "s1", "commando": "echo KWEEK-OK",
             "bewijs": {"type": "shell_check", "commando": "echo KWEEK-OK",
                        "verwacht_substr": "KWEEK-OK"}}]}

    def test_motor_zet_zelf_vangsten_weg(self):
        logboek = self.doel / "logboek.json"
        logboek.write_text("[]", encoding="utf-8")
        growkit_motor.voer_uit(self._profiel(), self.doel, logboek, None,
                               vangnet=growkit_motor.vangnet_pad_voor(self.doel))
        self.assertEqual(growkit_vangnet.tel(self.doel / "vangnet"), 1)

    def test_zonder_vangnet_geen_db(self):
        logboek = self.doel / "logboek.json"
        logboek.write_text("[]", encoding="utf-8")
        growkit_motor.voer_uit(self._profiel(), self.doel, logboek, None)
        self.assertFalse((self.doel / "vangnet").exists())


if __name__ == "__main__":
    unittest.main()
