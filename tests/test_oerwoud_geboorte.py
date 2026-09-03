"""Geboortebewijs volwaardig (§13, taak 1): placeholders worden feiten.

Regels:
- vul_geboortebewijs zet boom_id (uuid4), machine, locatie (geresolveerd
  doel-pad) en geplant_op (UTC, of expliciet meegegeven voor migratie).
- controleer_geboortebewijs weigert placeholders, kapotte JSON en missende
  verplichte velden.
- is_voor_fase5 herkent bomen uit fase 1-4 (placeholders) — migreerbaar.
- volmaak_na_plant: post-plant volmaking + append-only systeem-entry in het
  boom-logboek; idempotent (al geldig → niets doen, geen dubbele entry).
"""
import json
import re
import tempfile
import unittest
import uuid
from pathlib import Path

from kern.growkit_oerwoud import (
    controleer_geboortebewijs,
    is_voor_fase5,
    volmaak_na_plant,
    vul_geboortebewijs,
)

PLACEHOLDER_BEWIJS = {
    "boom_id": "{{BOOM_ID}}",
    "profiel": "tweede-brein",
    "machine": "{{MACHINE}}",
    "locatie": "{{LOCATIE}}",
    "geplant_op": "{{TIJDSTIP}}",
}


class TestVulGeboortebewijs(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.doel = Path(self._tmp.name) / "boom"
        self.doel.mkdir(parents=True)
        self.bewijs = self.doel / "geboortebewijs.json"
        self.bewijs.write_text(json.dumps(PLACEHOLDER_BEWIJS), encoding="utf-8")

    def tearDown(self):
        self._tmp.cleanup()

    def test_placeholders_worden_feiten(self):
        resultaat = vul_geboortebewijs(self.bewijs)
        self.assertEqual(resultaat["profiel"], "tweede-brein")
        uuid.UUID(resultaat["boom_id"])                      # geldige uuid4
        self.assertTrue(resultaat["machine"])
        self.assertEqual(resultaat["locatie"], str(self.doel.resolve()))
        self.assertIn("+00:00", resultaat["geplant_op"])
        opgeslagen = json.loads(self.bewijs.read_text(encoding="utf-8"))
        self.assertEqual(opgeslagen, resultaat)

    def test_expliciete_geplant_op_wordt_gerespecteerd(self):
        """Migratie: de geboorte is historisch feit, niet nu."""
        resultaat = vul_geboortebewijs(self.bewijs, geplant_op="2026-09-03T18:42:00+00:00")
        self.assertEqual(resultaat["geplant_op"], "2026-09-03T18:42:00+00:00")

    def test_geen_placeholders_na_vullen(self):
        vul_geboortebewijs(self.bewijs)
        self.assertNotIn("{{", self.bewijs.read_text(encoding="utf-8"))


class TestControleerGeboortebewijs(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.bewijs = Path(self._tmp.name) / "geboortebewijs.json"

    def tearDown(self):
        self._tmp.cleanup()

    def test_gevulde_bewijs_passen_de_controle(self):
        self.bewijs.write_text(json.dumps({
            "boom_id": str(uuid.uuid4()), "profiel": "tweede-brein",
            "machine": "mac", "locatie": "/tmp/boom",
            "geplant_op": "2026-09-03T18:42:00+00:00"}), encoding="utf-8")
        self.assertEqual(controleer_geboortebewijs(self.bewijs), [])

    def test_placeholders_worden_geweigerd(self):
        self.bewijs.write_text(json.dumps(PLACEHOLDER_BEWIJS), encoding="utf-8")
        bevindingen = controleer_geboortebewijs(self.bewijs)
        self.assertTrue(any("placeholder" in b.lower() for b in bevindingen))

    def test_kapotte_json_wordt_geweigerd(self):
        self.bewijs.write_text("{geen json", encoding="utf-8")
        bevindingen = controleer_geboortebewijs(self.bewijs)
        self.assertTrue(any("corrupt" in b.lower() for b in bevindingen))

    def test_missend_verplicht_veld_wordt_geweigerd(self):
        self.bewijs.write_text(json.dumps({"boom_id": str(uuid.uuid4())}), encoding="utf-8")
        bevindingen = controleer_geboortebewijs(self.bewijs)
        self.assertTrue(any("profiel" in b for b in bevindingen))


class TestIsVoorFase5(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.bewijs = Path(self._tmp.name) / "geboortebewijs.json"

    def tearDown(self):
        self._tmp.cleanup()

    def test_placeholder_bewijs_is_voor_fase5(self):
        self.bewijs.write_text(json.dumps(PLACEHOLDER_BEWIJS), encoding="utf-8")
        self.assertTrue(is_voor_fase5(self.bewijs))

    def test_gemaakt_bewijs_is_niet_voor_fase5(self):
        self.bewijs.write_text(json.dumps({
            "boom_id": str(uuid.uuid4()), "profiel": "tweede-brein",
            "machine": "mac", "locatie": "/tmp/boom",
            "geplant_op": "2026-09-03T18:42:00+00:00"}), encoding="utf-8")
        self.assertFalse(is_voor_fase5(self.bewijs))

    def test_afwezig_bewijs_is_voor_fase5(self):
        self.assertTrue(is_voor_fase5(self.bewijs))


class TestVolmaakNaPlant(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.doel = Path(self._tmp.name) / "boom"
        self.doel.mkdir(parents=True)
        (self.doel / "geboortebewijs.json").write_text(
            json.dumps(PLACEHOLDER_BEWIJS), encoding="utf-8")
        self.logboek = self.doel / "logboek.json"
        self.bestaand = [{"stap": "stap-008", "status": "wacht_op_mens",
                          "bewijs": "test", "tijdstip": "2026-09-03T19:00:00+00:00"}]
        self.logboek.write_text(json.dumps(self.bestaand), encoding="utf-8")

    def tearDown(self):
        self._tmp.cleanup()

    def test_volmaking_logt_append_only_systeem_entry(self):
        ok = volmaak_na_plant(self.doel, self.logboek)
        self.assertTrue(ok)
        entries = json.loads(self.logboek.read_text(encoding="utf-8"))
        self.assertEqual(entries[0], self.bestaand[0])          # append-only
        geboorte = [e for e in entries if e.get("type") == "geboorte"]
        self.assertEqual(len(geboorte), 1)
        self.assertEqual(geboorte[0]["status"], "geslaagd")
        self.assertIn("placeholder", geboorte[0]["bewijs"].lower())
        self.assertFalse(is_voor_fase5(self.doel / "geboortebewijs.json"))

    def test_volmaking_is_idempotent(self):
        volmaak_na_plant(self.doel, self.logboek)
        entries_voor = json.loads(self.logboek.read_text(encoding="utf-8"))
        ok = volmaak_na_plant(self.doel, self.logboek)
        self.assertFalse(ok)                                    # niets te doen
        entries_na = json.loads(self.logboek.read_text(encoding="utf-8"))
        self.assertEqual(entries_voor, entries_na)

    def test_kapotte_logboek_stopt_niet_de_volmaking(self):
        """Het logboek is kapot: de volmaking mag het bewijs niet weggooien —
        maar logt niets en meldt de situatie."""
        self.logboek.write_text("{half", encoding="utf-8")
        ok = volmaak_na_plant(self.doel, self.logboek)
        self.assertFalse(ok)                                    # gelogd worden lukt niet
        self.assertFalse(is_voor_fase5(self.doel / "geboortebewijs.json"))


if __name__ == "__main__":
    unittest.main()
