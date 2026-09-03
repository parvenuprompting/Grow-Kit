"""Boom-register (§13, taak 2): één plek die weet welke bomen bestaan.

Regels:
- register/bomen.json in de brein-boom; append-only (niets verdwijnt).
- Dubbele boom-id → geweigerd (één actieve registratie per boom).
- Deregistratie is een vervolg-entry door de mens; daarna kan her-registratie.
- Registratie verwijst naar een geldig, gecontroleerd geboortebewijs.
- Corrupt register → nette NL-fout, nooit auto-reparatie.
"""
import json
import tempfile
import unittest
import uuid
from pathlib import Path

from kern.growkit_oerwoud import (
    lees_register,
    meld_deregistratie,
    meld_geboorte,
    recentste_status,
)


def _geldig_bewijs(doel: Path) -> Path:
    doel.mkdir(parents=True, exist_ok=True)
    pad = doel / "geboortebewijs.json"
    pad.write_text(json.dumps({
        "boom_id": str(uuid.uuid4()), "profiel": "tweede-brein",
        "machine": "mac-lokaal", "locatie": str(doel.resolve()),
        "geplant_op": "2026-09-03T20:00:00+00:00"}), encoding="utf-8")
    return pad


class TestMeldGeboorte(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.brein = Path(self._tmp.name) / "brein"
        self.register = self.brein / "register" / "bomen.json"
        self.bewijs_a = _geldig_bewijs(Path(self._tmp.name) / "boom-a")
        self.bewijs_b = _geldig_bewijs(Path(self._tmp.name) / "boom-b")

    def tearDown(self):
        self._tmp.cleanup()

    def test_geboorte_entry_is_append_only(self):
        bestaand = [{"type": "geboorte", "boom_id": "oude-boom", "tijdstip": "oud"}]
        self.register.parent.mkdir(parents=True)
        self.register.write_text(json.dumps(bestaand), encoding="utf-8")
        boom_id = json.loads(self.bewijs_a.read_text(encoding="utf-8"))["boom_id"]
        entry = meld_geboorte(self.register, self.bewijs_a)
        entries = json.loads(self.register.read_text(encoding="utf-8"))
        self.assertEqual(entries[0], bestaand[0])               # niets verdwijnt
        self.assertEqual(len(entries), 2)
        self.assertEqual(entries[1]["boom_id"], boom_id)
        self.assertEqual(entry["type"], "geboorte")
        self.assertIn("tijdstip", entry)

    def test_is_brein_wordt_geregistreerd(self):
        entry = meld_geboorte(self.register, self.bewijs_a, is_brein=True)
        self.assertTrue(entry.get("is_brein"))

    def test_dubbele_boom_id_wordt_geweigerd(self):
        meld_geboorte(self.register, self.bewijs_a)
        with self.assertRaises(ValueError) as ctx:
            meld_geboorte(self.register, self.bewijs_a)
        self.assertIn("al in het register", str(ctx.exception))

    def test_registratie_weigert_ongeldig_geboortebewijs(self):
        slecht = Path(self._tmp.name) / "boom-slecht"
        pad = _geldig_bewijs(slecht)
        pad.write_text(json.dumps({"boom_id": "{{BOOM_ID}}"}), encoding="utf-8")
        with self.assertRaises(ValueError) as ctx:
            meld_geboorte(self.register, pad)
        self.assertIn("placeholder", str(ctx.exception).lower())


class TestDeregistratieEnHerregistratie(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.register = Path(self._tmp.name) / "register" / "bomen.json"
        self.bewijs = _geldig_bewijs(Path(self._tmp.name) / "boom")
        self.boom_id = json.loads(self.bewijs.read_text(encoding="utf-8"))["boom_id"]

    def tearDown(self):
        self._tmp.cleanup()

    def test_deregistratie_is_vervolg_entry(self):
        meld_geboorte(self.register, self.bewijs)
        meld_deregistratie(self.register, self.boom_id, reden="boom verwijderd door de mens")
        entries = json.loads(self.register.read_text(encoding="utf-8"))
        self.assertEqual(len(entries), 2)                       # niets verwijderd
        self.assertEqual(entries[1]["type"], "deregistratie")
        self.assertIn("verwijderd", entries[1]["bewijs"])

    def test_na_deregistratie_is_herregistratie_mogelijk(self):
        meld_geboorte(self.register, self.bewijs)
        meld_deregistratie(self.register, self.boom_id, reden="test")
        entry = meld_geboorte(self.register, self.bewijs)       # niet geweigerd
        self.assertEqual(entry["type"], "registratie")

    def test_deregistratie_van_onbekende_boom_wordt_geweigerd(self):
        with self.assertRaises(ValueError):
            meld_deregistratie(self.register, "bestaat-niet", reden="test")


class TestLeesRegister(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.register = Path(self._tmp.name) / "bomen.json"

    def tearDown(self):
        self._tmp.cleanup()

    def test_afwezig_register_is_leeg(self):
        self.assertEqual(lees_register(self.register), [])

    def test_corrupt_register_geeft_nette_fout(self):
        self.register.write_text("{geen json", encoding="utf-8")
        with self.assertRaises(ValueError) as ctx:
            lees_register(self.register)
        self.assertIn("corrupt", str(ctx.exception).lower())

    def test_recentste_status_wint(self):
        entries = [
            {"type": "geboorte", "boom_id": "b1"},
            {"type": "geboorte", "boom_id": "b2"},
            {"type": "deregistratie", "boom_id": "b1", "bewijs": "test"},
        ]
        self.register.write_text(json.dumps(entries), encoding="utf-8")
        register = lees_register(self.register)
        self.assertEqual(recentste_status(register, "b1"), "gederegistreerd")
        self.assertEqual(recentste_status(register, "b2"), "geboorte")
        self.assertIsNone(recentste_status(register, "b3"))


if __name__ == "__main__":
    unittest.main()
