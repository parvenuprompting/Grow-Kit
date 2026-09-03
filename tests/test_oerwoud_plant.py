"""Brein-detectie en registratie (§13, taak 3): één brein, vele bomen.

Regels:
- Per-machine staat: GROWKIT_OERWOUD_STAAT (tests) of ~/.growkit/oerwoud.json.
- Brein onbekend → één vraag: brein-pad / leeg = deze boom wordt het brein /
  "nee" = niet registreren (niets opgeslagen, niets aangemeld).
- Brein bekend → direct registreren (machine-feit, beslissing 2).
- Brein-pad onbereikbaar → foutstatus brein_onbereikbaar: mens, geen crash,
  géén fallback naar nieuw brein (oerwoud-splitsing voorkomen).
- Migratie (gat 1): oude bomen met placeholders volmaken met geplant_op
  terugrekend uit de eerste logboek-entry; weigering → geen registratie.
"""
import json
import os
import tempfile
import unittest
import uuid
from pathlib import Path

from kern import growkit_oerwoud as gw


class OerwoudTestBasis(unittest.TestCase):
    """Elke test draait in een geïsoleerde 'home' — nooit de echte ~/.growkit."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.home = Path(self._tmp.name) / "growkit-home"
        self._oude_env = os.environ.get("GROWKIT_OERWOUD_STAAT")
        os.environ["GROWKIT_OERWOUD_STAAT"] = str(self.home / "oerwoud.json")

    def _boom(self, naam: str, placeholders: bool = False) -> tuple[Path, Path]:
        doel = Path(self._tmp.name) / naam
        doel.mkdir(parents=True, exist_ok=True)
        logboek = doel / "logboek.json"
        logboek.write_text("[]", encoding="utf-8")
        bewijs = {
            "boom_id": str(uuid.uuid4()) if not placeholders else "{{BOOM_ID}}",
            "profiel": "tweede-brein",
            "machine": "mac-lokaal",
            "locatie": str(doel.resolve()) if not placeholders else "{{LOCATIE}}",
            "geplant_op": "2026-09-03T20:00:00+00:00" if not placeholders else "{{TIJDSTIP}}",
        }
        if placeholders:
            bewijs["machine"] = "{{MACHINE}}"
        (doel / "geboortebewijs.json").write_text(json.dumps(bewijs), encoding="utf-8")
        return doel, logboek


class TestStaat(OerwoudTestBasis):
    def test_staat_leeg_zonder_bestand(self):
        staat = gw.laad_oerwoud_staat()
        self.assertIsNone(staat["brein_pad"])
        self.assertIsNone(staat["fout"])

    def test_sla_en_laad_brein_pad(self):
        brein = Path("/tmp/ergens/brein")
        gw.sla_brein_pad(brein)
        staat = gw.laad_oerwoud_staat()
        self.assertEqual(staat["brein_pad"], brein)
        self.assertTrue(self.home.exists())                    # in de geïsoleerde home

    def test_onbereikbaar_brein_is_expliciete_fout(self):
        """Gat 2: verplaatst/verwijderd/niet-aangesloten brein → mens, geen crash,
        géén fallback naar 'nieuw brein' (oerwoud-splitsing voorkomen)."""
        gw.sla_brein_pad(Path(self._tmp.name) / "verdwenen-brein")
        staat = gw.laad_oerwoud_staat()
        self.assertEqual(staat["fout"], "brein_onbereikbaar")
        self.assertEqual(staat["brein_pad"], Path(self._tmp.name) / "verdwenen-brein")

    def test_corrupte_staat_is_nette_fout(self):
        self.home.mkdir(parents=True)
        (self.home / "oerwoud.json").write_text("{geen json", encoding="utf-8")
        with self.assertRaises(ValueError) as ctx:
            gw.laad_oerwoud_staat()
        self.assertIn("corrupt", str(ctx.exception).lower())


class TestRegistreerNieuweBoom(OerwoudTestBasis):
    def setUp(self):
        super().setUp()

    def _boom(self, naam: str) -> tuple[Path, Path]:
        doel = Path(self._tmp.name) / naam
        doel.mkdir(parents=True)
        logboek = doel / "logboek.json"
        logboek.write_text("[]", encoding="utf-8")
        (doel / "geboortebewijs.json").write_text(json.dumps({
            "boom_id": str(uuid.uuid4()), "profiel": "tweede-brein",
            "machine": "mac", "locatie": str(doel.resolve()),
            "geplant_op": "2026-09-03T20:00:00+00:00"}), encoding="utf-8")
        return doel, logboek

    def test_eerste_plant_leeg_maakt_deze_boom_het_brein(self):
        doel, _ = self._boom("boom-a")
        code = gw.registreer_nieuwe_boom(doel, invoer_fn=lambda _: "")
        self.assertEqual(code, 0)
        register = self.home.parent / "boom-a" / "register" / "bomen.json"
        entries = json.loads(register.read_text(encoding="utf-8"))
        self.assertEqual(len(entries), 1)
        self.assertTrue(entries[0].get("is_brein"))
        staat = gw.laad_oerwoud_staat()
        self.assertEqual(staat["brein_pad"], doel.resolve())

    def test_tweede_plant_registreert_zonder_vraag(self):
        brein, _ = self._boom("brein")
        gw.registreer_nieuwe_boom(brein, invoer_fn=lambda _: "")
        vragen = []

        def teller(_vraag: str) -> str:
            vragen.append(_vraag)
            return ""

        doel, _ = self._boom("boom-b")
        code = gw.registreer_nieuwe_boom(doel, invoer_fn=teller)
        self.assertEqual(code, 0)
        self.assertEqual(vragen, [])                           # brein bekend: geen vraag
        register = brein.resolve() / "register" / "bomen.json"
        entries = json.loads(register.read_text(encoding="utf-8"))
        self.assertEqual(len(entries), 2)

    def test_nee_is_geen_actie(self):
        doel, _ = self._boom("boom-a")
        code = gw.registreer_nieuwe_boom(doel, invoer_fn=lambda _: "nee")
        self.assertEqual(code, 1)
        self.assertFalse((self.home / "oerwoud.json").exists())  # niets opgeslagen
        self.assertFalse((doel / "register").exists())           # niets geregistreerd

    def test_pad_bestaat_niet_wordt_geweigerd(self):
        doel, _ = self._boom("boom-a")
        code = gw.registreer_nieuwe_boom(
            doel, invoer_fn=lambda _: str(Path(self._tmp.name) / "onbestaand"))
        self.assertEqual(code, 1)
        self.assertFalse((self.home / "oerwoud.json").exists())

    def test_onbereikbaar_brein_gaat_niet_naar_nieuw_brein(self):
        """Gat 2: de mens kiest 'afbreken' — het oude brein blijft staan."""
        verdwenen = Path(self._tmp.name) / "oud-brein"
        verdwenen.mkdir()
        gw.sla_brein_pad(verdwenen)
        verdwenen.rmdir()
        doel, _ = self._boom("boom-a")
        code = gw.registreer_nieuwe_boom(doel, invoer_fn=lambda _: "a")
        self.assertEqual(code, 1)
        staat = gw.laad_oerwoud_staat()
        self.assertEqual(staat["fout"], "brein_onbereikbaar")    # niet overschreven
        self.assertFalse((doel / "register").exists())           # géén nieuw brein aangemaakt

    def test_onbereikbaar_brein_met_pad_correctie_registreert(self):
        oud = Path(self._tmp.name) / "oud-brein"
        oud.mkdir()
        gw.sla_brein_pad(oud)
        oud.rmdir()
        nieuw = Path(self._tmp.name) / "nieuw-brein"
        nieuw.mkdir()
        (nieuw / "geboortebewijs.json").write_text(json.dumps({
            "boom_id": str(uuid.uuid4()), "profiel": "tweede-brein",
            "machine": "mac", "locatie": str(nieuw.resolve()),
            "geplant_op": "2026-09-03T20:00:00+00:00"}), encoding="utf-8")
        doel, _ = self._boom("boom-a")
        antwoorden = iter(["c", str(nieuw)])
        code = gw.registreer_nieuwe_boom(doel, invoer_fn=lambda _: next(antwoorden))
        self.assertEqual(code, 0)
        entries = json.loads((nieuw / "register" / "bomen.json").read_text(encoding="utf-8"))
        self.assertEqual(len(entries), 1)


class TestMigratieOudeBomen(OerwoudTestBasis):
    """Gat 1: bomen uit fase 1-4 hebben placeholders — migreerbaar met
    geplant_op teruggerekend uit de eerste logboek-entry."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.home = Path(self._tmp.name) / "growkit-home"
        self._oude_env = os.environ.get("GROWKIT_OERWOUD_STAAT")
        os.environ["GROWKIT_OERWOUD_STAAT"] = str(self.home / "oerwoud.json")
        self.brein = Path(self._tmp.name) / "brein"
        self.brein.mkdir()
        (self.brein / "geboortebewijs.json").write_text(json.dumps({
            "boom_id": str(uuid.uuid4()), "profiel": "tweede-brein",
            "machine": "mac", "locatie": str(self.brein.resolve()),
            "geplant_op": "2026-09-03T19:00:00+00:00"}), encoding="utf-8")
        gw.sla_brein_pad(self.brein)

    def tearDown(self):
        if self._oude_env is None:
            os.environ.pop("GROWKIT_OERWOUD_STAAT", None)
        else:
            os.environ["GROWKIT_OERWOUD_STAAT"] = self._oude_env
        self._tmp.cleanup()

    def _oude_boom(self) -> tuple[Path, Path]:
        doel = Path(self._tmp.name) / "oude-boom"
        doel.mkdir()
        logboek = doel / "logboek.json"
        logboek.write_text(json.dumps([
            {"stap": "stap-001", "status": "geslaagd", "bewijs": "test",
             "tijdstip": "2026-09-01T08:15:00+00:00"},
        ]), encoding="utf-8")
        (doel / "geboortebewijs.json").write_text(json.dumps({
            "boom_id": "{{BOOM_ID}}", "profiel": "tweede-brein",
            "machine": "{{MACHINE}}", "locatie": "{{LOCATIE}}",
            "geplant_op": "{{TIJDSTIP}}"}), encoding="utf-8")
        return doel, logboek

    def test_migratie_rekent_geplant_op_terug_uit_het_logboek(self):
        doel, logboek = self._oude_boom()
        code = gw.migratie_en_registratie(doel, logboek, invoer_fn=lambda _: "ja")
        self.assertEqual(code, 0)
        bewijs = json.loads((doel / "geboortebewijs.json").read_text(encoding="utf-8"))
        self.assertEqual(bewijs["geplant_op"], "2026-09-01T08:15:00+00:00")
        self.assertNotIn("{{", json.dumps(bewijs))
        entries = json.loads(logboek.read_text(encoding="utf-8"))
        self.assertEqual(len([e for e in entries if e.get("type") == "geboorte"]), 1)
        register = json.loads((self.brein / "register" / "bomen.json").read_text(encoding="utf-8"))
        self.assertEqual(len(register), 1)

    def test_weigering_is_geen_registratie(self):
        doel, logboek = self._oude_boom()
        code = gw.migratie_en_registratie(doel, logboek, invoer_fn=lambda _: "nee")
        self.assertEqual(code, 1)
        self.assertTrue(gw.is_voor_fase5(doel / "geboortebewijs.json"))
        self.assertFalse((self.brein / "register").exists())

    def test_corrupt_logboek_blokkeert_terugrekenen(self):
        doel, logboek = self._oude_boom()
        logboek.write_text("{half", encoding="utf-8")
        code = gw.migratie_en_registratie(doel, logboek, invoer_fn=lambda _: "ja")
        self.assertEqual(code, 1)
        self.assertTrue(gw.is_voor_fase5(doel / "geboortebewijs.json"))  # niets overschreven


if __name__ == "__main__":
    unittest.main()
