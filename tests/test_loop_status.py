"""Status-modus (§13, taak 5): het oerwoud zichtbaar, puur lezend.

Regels:
- Toont identiteit (geboortebewijs), register-status, tellers (wachtend /
  verzonden) en de laatste mijlpaal- of faal-entry.
- Eén uitzondering op alleen-lezen: een oude (is_voor_fase5) of niet-
  geregistreerde boom krijgt het migratie-en-registratie-aanbod; weigering
  → geen actie.
- Zonder geboortebewijs → nette mededeling, geen crash.
"""
import contextlib
import io
import json
import os
import tempfile
import unittest
import uuid
from pathlib import Path

from loop import toon_status


class TestStatus(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.home = Path(self._tmp.name) / "growkit-home"
        self._oude_env = os.environ.get("GROWKIT_OERWOUD_STAAT")
        os.environ["GROWKIT_OERWOUD_STAAT"] = str(self.home / "oerwoud.json")
        self.brein = Path(self._tmp.name) / "brein"
        self.brein.mkdir(parents=True)
        (self.brein / "inbox").mkdir()
        (self.brein / "register").mkdir()
        (self.brein / "register" / "bomen.json").write_text("[]", encoding="utf-8")
        self.doel = Path(self._tmp.name) / "boom"
        self.doel.mkdir()
        self.bewijs = self.doel / "geboortebewijs.json"
        self.boom_id = str(uuid.uuid4())
        self._schrijf_bewijs(self.boom_id)
        self.logboek = self.doel / "logboek.json"
        self.logboek.write_text("[]", encoding="utf-8")
        # dit brein kent de boom al
        (self.brein / "register" / "bomen.json").write_text(json.dumps([
            {"type": "geboorte", "boom_id": self.boom_id, "profiel": "tweede-brein",
             "machine": "mac", "locatie": str(self.doel.resolve()),
             "geplant_op": "2026-09-03T20:00:00+00:00", "tijdstip": "2026-09-03T20:00:01+00:00"},
        ]), encoding="utf-8")
        from kern.growkit_oerwoud import sla_brein_pad
        sla_brein_pad(self.brein)

    def tearDown(self):
        if self._oude_env is None:
            os.environ.pop("GROWKIT_OERWOUD_STAAT", None)
        else:
            os.environ["GROWKIT_OERWOUD_STAAT"] = self._oude_env
        self._tmp.cleanup()

    def _schrijf_bewijs(self, boom_id: str) -> None:
        self.bewijs.write_text(json.dumps({
            "boom_id": boom_id, "profiel": "tweede-brein", "machine": "mac",
            "locatie": str(self.doel.resolve()),
            "geplant_op": "2026-09-03T20:00:00+00:00"}), encoding="utf-8")

    def _voorstel(self, naam: str) -> None:
        (self.doel / "inbox").mkdir(exist_ok=True)
        (self.doel / "inbox" / naam).write_text("inhoud", encoding="utf-8")

    def _run(self, invoer_fn=None) -> tuple[int, str]:
        import contextlib
        import io
        uit = io.StringIO()
        with contextlib.redirect_stdout(uit):
            code = toon_status(self.doel, invoer_fn=invoer_fn or (lambda _: self.fail("geen vraag verwacht")))
        return code, uit.getvalue()

    def test_status_toont_identiteit_en_register(self):
        code, uit = self._run()
        self.assertEqual(code, 0)
        self.assertIn(self.boom_id, uit)
        self.assertIn("tweede-brein", uit)
        self.assertIn("geboorte", uit)                          # register-status

    def test_teller_klopt_bij_n_en_n_plus_een(self):
        self._voorstel("VOORSTEL-a.md")
        _, uit1 = self._run(invoer_fn=lambda _: "nee")      # doorstroom uitstellen
        self.assertIn("1 wachtend", uit1)
        self._voorstel("VOORSTEL-b.md")
        _, uit2 = self._run(invoer_fn=lambda _: "nee")
        self.assertIn("2 wachtend", uit2)

    def test_laatste_mijlpaal_wordt_getoond(self):
        entries = [{"type": "mijlpaal", "stap": "mijlpaal-start", "status": "bevestigd",
                    "bewijs": "bevestigd door de mens", "tijdstip": "2026-09-03T19:00:00+00:00"}]
        self.logboek.write_text(json.dumps(entries), encoding="utf-8")
        _, uit = self._run()
        self.assertIn("mijlpaal", uit.lower())

    def test_zonder_geboortebewijs_nette_melding(self):
        self.bewijs.unlink()
        code, uit = self._run()
        self.assertEqual(code, 0)
        self.assertIn("geen geboortebewijs", uit.lower())
        self.assertNotIn("Traceback", uit)

    def test_niet_geregistreerde_oude_boom_krijgt_migratie_aanbod(self):
        """Gat 1: de ingang voor oude bomen — migratie + registratie hier."""
        self._schrijf_bewijs("{{BOOM_ID}}")
        self._voorstel("VOORSTEL-a.md")
        self.logboek.write_text(json.dumps([
            {"stap": "stap-001", "status": "geslaagd", "bewijs": "test",
             "tijdstip": "2026-09-01T08:15:00+00:00"}]), encoding="utf-8")
        antwoorden = iter(["nee", "ja"])                        # doorstroom nee, migratie ja
        code, uit = self._run(invoer_fn=lambda _: next(antwoorden))
        self.assertEqual(code, 0)
        bewijs = json.loads(self.bewijs.read_text(encoding="utf-8"))
        self.assertNotIn("{{", json.dumps(bewijs))
        self.assertEqual(bewijs["geplant_op"], "2026-09-01T08:15:00+00:00")
        register = json.loads((self.brein / "register" / "bomen.json").read_text(encoding="utf-8"))
        self.assertEqual(len(register), 2)                      # oude entry + deze boom

    def test_weigering_van_het_aanbod_is_geen_actie(self):
        self._schrijf_bewijs("{{BOOM_ID}}")
        antwoorden = iter(["nee"])
        code, uit = self._run(invoer_fn=lambda _: next(antwoorden))
        self.assertEqual(code, 0)
        self.assertIn("{{", self.bewijs.read_text(encoding="utf-8"))   # niets overschreven
        register = json.loads((self.brein / "register" / "bomen.json").read_text(encoding="utf-8"))
        self.assertEqual(len(register), 1)


if __name__ == "__main__":
    unittest.main()


class TestDoorstroomAanbod(unittest.TestCase):
    """Beslissing 4: wachtende VOORSTELLEN krijgen in de status één aanbod."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.home = Path(self._tmp.name) / "growkit-home"
        self._oude_env = os.environ.get("GROWKIT_OERWOUD_STAAT")
        os.environ["GROWKIT_OERWOUD_STAAT"] = str(self.home / "oerwoud.json")
        self.brein = Path(self._tmp.name) / "brein"
        self.brein.mkdir(parents=True)
        (self.brein / "inbox").mkdir()
        (self.brein / "register").mkdir()
        (self.brein / "register" / "bomen.json").write_text("[]", encoding="utf-8")
        self.doel = Path(self._tmp.name) / "boom"
        self.doel.mkdir()
        (self.doel / "inbox").mkdir()
        (self.doel / "geboortebewijs.json").write_text(json.dumps({
            "boom_id": str(uuid.uuid4()), "profiel": "tweede-brein", "machine": "mac",
            "locatie": str(self.doel.resolve()),
            "geplant_op": "2026-09-03T20:00:00+00:00"}), encoding="utf-8")
        self.logboek = self.doel / "logboek.json"
        self.logboek.write_text("[]", encoding="utf-8")
        from kern.growkit_oerwoud import sla_brein_pad
        sla_brein_pad(self.brein)
        # de boom is bij het planten al geregistreerd (fase 5-flow)
        boom_id = json.loads((self.doel / "geboortebewijs.json").read_text(encoding="utf-8"))["boom_id"]
        (self.brein / "register" / "bomen.json").write_text(json.dumps([
            {"type": "geboorte", "boom_id": boom_id, "profiel": "tweede-brein",
             "machine": "mac", "locatie": str(self.doel.resolve()),
             "geplant_op": "2026-09-03T20:00:00+00:00", "tijdstip": "2026-09-03T20:00:01+00:00"},
        ]), encoding="utf-8")

    def tearDown(self):
        if self._oude_env is None:
            os.environ.pop("GROWKIT_OERWOUD_STAAT", None)
        else:
            os.environ["GROWKIT_OERWOUD_STAAT"] = self._oude_env
        self._tmp.cleanup()

    def test_wachtende_voorstellen_krijgen_een_aanbod(self):
        (self.doel / "inbox" / "VOORSTEL-inzicht.md").write_text("inzicht", encoding="utf-8")
        antwoorden = iter(["ja"])
        uit = io.StringIO()
        with contextlib.redirect_stdout(uit):
            code = toon_status(self.doel, invoer_fn=lambda _: next(antwoorden))
        self.assertEqual(code, 0)
        verzonden = [p for p in (self.brein / "inbox").iterdir()
                     if p.name.startswith("VOORSTEL-")]
        self.assertEqual(len(verzonden), 1)
        self.assertIn("VOORSTELLEN verzonden", uit.getvalue())

    def test_weigering_verstuurt_niets(self):
        (self.doel / "inbox" / "VOORSTEL-inzicht.md").write_text("inzicht", encoding="utf-8")
        antwoorden = iter(["nee"])
        with contextlib.redirect_stdout(io.StringIO()):
            code = toon_status(self.doel, invoer_fn=lambda _: next(antwoorden))
        self.assertEqual(code, 0)
        verzonden = [p for p in (self.brein / "inbox").iterdir()
                     if p.name.startswith("VOORSTEL-")]
        self.assertEqual(verzonden, [])

    def test_geen_wachtende_voorstellen_geen_vraag(self):
        with contextlib.redirect_stdout(io.StringIO()):
            code = toon_status(self.doel, invoer_fn=lambda _: self.fail("geen vraag verwacht"))
        self.assertEqual(code, 0)


class TestOnbereikbaarBrein(unittest.TestCase):
    """Gat 2 in de status: een dood brein-pad roept de mens, geen crash."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.home = Path(self._tmp.name) / "growkit-home"
        self._oude_env = os.environ.get("GROWKIT_OERWOUD_STAAT")
        os.environ["GROWKIT_OERWOUD_STAAT"] = str(self.home / "oerwoud.json")
        self.doel = Path(self._tmp.name) / "boom"
        self.doel.mkdir()
        (self.doel / "geboortebewijs.json").write_text(json.dumps({
            "boom_id": str(uuid.uuid4()), "profiel": "tweede-brein", "machine": "mac",
            "locatie": str(self.doel.resolve()),
            "geplant_op": "2026-09-03T20:00:00+00:00"}), encoding="utf-8")
        (self.doel / "logboek.json").write_text("[]", encoding="utf-8")
        verdwenen = Path(self._tmp.name) / "verdwenen-brein"
        verdwenen.mkdir()
        from kern.growkit_oerwoud import sla_brein_pad
        sla_brein_pad(verdwenen)
        verdwenen.rmdir()

    def tearDown(self):
        if self._oude_env is None:
            os.environ.pop("GROWKIT_OERWOUD_STAAT", None)
        else:
            os.environ["GROWKIT_OERWOUD_STAAT"] = self._oude_env
        self._tmp.cleanup()

    def test_onbereikbaar_brein_geeft_mens_vraag_geen_crash(self):
        import contextlib
        import io
        antwoorden = iter(["a"])                                # afbreken
        uit = io.StringIO()
        with contextlib.redirect_stdout(uit):
            code = toon_status(self.doel, invoer_fn=lambda _: next(antwoorden))
        self.assertEqual(code, 1)
        self.assertIn("niet bereikbaar", uit.getvalue())
        self.assertNotIn("Traceback", uit.getvalue())

    def test_pad_correctie_in_de_status_werkt(self):
        import contextlib
        import io
        nieuw = Path(self._tmp.name) / "nieuw-brein"
        nieuw.mkdir()
        (nieuw / "register").mkdir()
        (nieuw / "register" / "bomen.json").write_text("[]", encoding="utf-8")
        antwoorden = iter(["c", str(nieuw), "nee"])
        uit = io.StringIO()
        with contextlib.redirect_stdout(uit):
            code = toon_status(self.doel, invoer_fn=lambda _: next(antwoorden))
        self.assertEqual(code, 0)
        self.assertIn("niet geregistreerd", uit.getvalue())
        staat = json.loads((self.home / "oerwoud.json").read_text(encoding="utf-8"))
        self.assertEqual(Path(staat["brein_pad"]), nieuw.resolve())


if __name__ == "__main__":
    unittest.main()
