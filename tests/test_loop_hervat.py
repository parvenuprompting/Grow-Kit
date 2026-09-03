"""Loop.py hervat-modus (§7, audit-B): restdraai-profiel, motor ongewijzigd.

Regels (fase 4, taak 4):
- reconstructie() → restdraai = heraanbieden + uitvoeren; overslaan-stappen
  krijgen nooit een tweede entry (niet-idempotent nooit herdraaid).
- Herstartpunt (laatste bevestigde mijlpaal) wordt getoond vóór de restdraai.
- Corrupt logboek → mens-boodschap, geen crash.
- Restdraai draait pas na mens-bevestiging (kernregel §11.1 hard).
- Zonder profiel-injectie leest de loop de profielnaam uit het
  geboortebewijs in de doelmap — self-contained hervatten.
"""
import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

import loop


def _stap(sid: str, commando: str, verwacht: str, idempotent: bool) -> dict:
    return {
        "id": sid,
        "commando": commando,
        "verwacht": "test",
        "bewijs": {"type": "shell_check", "commando": commando, "verwacht_substr": verwacht},
        "idempotent": idempotent,
    }


def _profiel() -> dict:
    return {
        "profiel": "test-boom",
        "stappen": [
            _stap("stap-001", "echo OK-1", "OK-1", True),
            _stap("stap-002", "printf x > bestand2.txt && echo OK-2", "OK-2", False),
            _stap("stap-003", "echo OK-3", "OK-3", True),
            _stap("stap-004", "printf y > bestand4.txt && echo OK-4", "OK-4", False),
        ],
    }


def _entry(stap: str, status: str) -> dict:
    return {"stap": stap, "status": status, "bewijs": "test", "tijdstip": "2026-09-03T20:00:00+00:00"}


class TestHervatModus(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.doel = Path(self._tmp.name)
        self.logboek = self.doel / "logboek.json"
        self._antwoorden = []

    def tearDown(self):
        self._tmp.cleanup()

    def _invoer_fn(self, _vraag: str) -> str:
        if not self._antwoorden:
            self.fail("er werd een vraag gesteld die niet verwacht was")
        return self._antwoorden.pop(0)

    def _run(self) -> tuple[int, str]:
        uit = io.StringIO()
        with contextlib.redirect_stdout(uit):
            code = loop.hervat_boom(doel=self.doel, profiel=_profiel(), invoer_fn=self._invoer_fn)
        return code, uit.getvalue()

    def test_restdraai_loopt_heraangeboden_en_nieuwe_stappen(self):
        self.logboek.write_text(json.dumps([
            _entry("stap-001", "geslaagd"),
            _entry("stap-002", "geslaagd"),
            _entry("stap-003", "gefaald"),
        ]), encoding="utf-8")
        self._antwoorden = ["ja"]
        code, uit = self._run()
        self.assertEqual(code, 0)
        self.assertIn("nooit herdraaien", uit)          # niet-idempotent overslaan bewijst zich
        self.assertIn("stap-003, stap-004", uit)
        entries = json.loads(self.logboek.read_text(encoding="utf-8"))
        self.assertEqual(len([e for e in entries if e["stap"] == "stap-002"]), 1)  # geen herdraai
        laatste_003 = [e for e in entries if e["stap"] == "stap-003"][-1]
        self.assertEqual(laatste_003["status"], "geslaagd")
        self.assertTrue(any(e["stap"] == "stap-004" for e in entries))

    def test_geen_bevestiging_niets_uitgevoerd(self):
        bestaand = [_entry("stap-001", "geslaagd"), _entry("stap-003", "gefaald")]
        self.logboek.write_text(json.dumps(bestaand), encoding="utf-8")
        self._antwoorden = ["nee"]
        code, uit = self._run()
        self.assertEqual(code, 1)
        self.assertIn("Geen bevestiging", uit)
        entries = json.loads(self.logboek.read_text(encoding="utf-8"))
        self.assertEqual(entries, bestaand)             # append-only: niets bijgeschreven

    def test_geen_hervatting_nodig_stelt_geen_vragen(self):
        self.logboek.write_text(json.dumps([_entry(f"stap-00{i}", "geslaagd") for i in range(1, 5)]),
                                encoding="utf-8")
        code, uit = self._run()
        self.assertEqual(code, 0)
        self.assertIn("Niets te hervatten", uit)

    def test_corrupt_logboek_geeft_mens_boodschap(self):
        self.logboek.write_text("{half geschreven", encoding="utf-8")
        code, uit = self._run()
        self.assertEqual(code, 1)
        self.assertIn("corrupt", uit.lower())
        self.assertNotIn("Traceback", uit)

    def test_herstartpunt_wordt_getoond(self):
        mijlpaal = {"type": "mijlpaal", "stap": "mijlpaal-start", "status": "bevestigd",
                    "bewijs": "bevestigd", "tijdstip": "2026-09-03T19:00:00+00:00"}
        self.logboek.write_text(json.dumps([mijlpaal, _entry("stap-001", "geslaagd")]), encoding="utf-8")
        self._antwoorden = ["nee"]
        code, uit = self._run()
        self.assertEqual(code, 1)
        self.assertIn("mijlpaal-start", uit)
        self.assertIn("2026-09-03T19:00:00+00:00", uit)


class TestHervatUitGeboortebewijs(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.doel = Path(self._tmp.name) / "boom"
        self.doel.mkdir(parents=True)

    def tearDown(self):
        self._tmp.cleanup()

    def test_profiel_wordt_uit_het_geboortebewijs_gelezen(self):
        (self.doel / "geboortebewijs.json").write_text(
            json.dumps({"boom_id": "x", "profiel": "tweede-brein"}), encoding="utf-8")
        uit = io.StringIO()
        with contextlib.redirect_stdout(uit):
            code = loop.hervat_boom(doel=self.doel, invoer_fn=lambda _: "nee")
        self.assertEqual(code, 1)                        # geweigerd, maar het profiel is wél geladen
        self.assertIn("8 stappen", uit.getvalue())                  # tweede-brein heeft 8 stappen

    def test_corrupt_geboortebewijs_geeft_nette_fout(self):
        (self.doel / "geboortebewijs.json").write_text("{geen json", encoding="utf-8")
        uit = io.StringIO()
        with contextlib.redirect_stdout(uit):
            code = loop.hervat_boom(doel=self.doel, invoer_fn=lambda _: "nee")
        self.assertEqual(code, 1)
        self.assertIn("roep de mens", uit.getvalue().lower())
        self.assertNotIn("Traceback", uit)


if __name__ == "__main__":
    unittest.main()
