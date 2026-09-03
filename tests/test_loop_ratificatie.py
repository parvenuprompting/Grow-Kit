"""Ratificatie in bulk (§9): één bevestiging, append-only, geen rollback.

Regels (fase 4, taak 5):
- Alle stappen met laatste status review_ok_wacht_ratificatie als één lijst;
  één bevestiging → per stap een append-only vervolg-entry `geratificeerd`.
- Afkeur van een stap → `herziening_nodig` mét doorloop-vermelding; de rest
  blijft wachten; géén auto-rollback.
- Doorloop (gat-review): na afkeuring behandelt reconstructie() de stap als
  heraanbieden — het gat uit het plan-review is hier bewezen gesloten.
- Geen wachtende stappen → geen vraag gesteld.
"""
import json
import tempfile
import unittest
from pathlib import Path

import loop
from kern.growkit_hervat import reconstructie


def _entry(stap: str, status: str) -> dict:
    return {"stap": stap, "status": status, "bewijs": f"{stap} {status}",
            "tijdstip": "2026-09-03T20:00:00+00:00"}


def _profiel() -> dict:
    return {"profiel": "test-boom",
            "stappen": [{"id": f"stap-00{i}", "idempotent": True} for i in range(1, 4)]}


class TestRatificatie(unittest.TestCase):
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

    def _verwacht_logboek(self):
        return [
            _entry("stap-001", "geslaagd"),
            _entry("stap-002", "review_ok_wacht_ratificatie"),
            _entry("stap-003", "review_ok_wacht_ratificatie"),
        ]

    def _run(self) -> tuple[int, str]:
        import contextlib, io
        uit = io.StringIO()
        with contextlib.redirect_stdout(uit):
            code = loop.ratificeer(self.doel, invoer_fn=self._invoer_fn)
        return code, uit.getvalue()

    def test_een_ja_ratificeert_alle_wachtende_stappen(self):
        origineel = self._verwacht_logboek()
        self.logboek.write_text(json.dumps(origineel), encoding="utf-8")
        self._antwoorden = ["ja"]
        code, uit = self._run()
        self.assertEqual(code, 0)
        entries = json.loads(self.logboek.read_text(encoding="utf-8"))
        self.assertEqual(entries[:3], origineel)             # append-only: niets veranderd
        geratificeerd = [e for e in entries if e.get("type") == "ratificatie"]
        self.assertEqual([e["stap"] for e in geratificeerd], ["stap-002", "stap-003"])
        self.assertTrue(all(e["status"] == "geratificeerd" for e in geratificeerd))
        self.assertTrue(all("tijdstip" in e for e in geratificeerd))
        self.assertNotIn("stap-001", [e["stap"] for e in geratificeerd])

    def test_afkeur_zet_herziening_nodig_en_rest_blijft_wachten(self):
        origineel = self._verwacht_logboek()
        self.logboek.write_text(json.dumps(origineel), encoding="utf-8")
        self._antwoorden = ["1"]
        code, uit = self._run()
        self.assertEqual(code, 0)
        entries = json.loads(self.logboek.read_text(encoding="utf-8"))
        self.assertEqual(entries[:3], origineel)
        ratificaties = [e for e in entries if e.get("type") == "ratificatie"]
        self.assertEqual(len(ratificaties), 1)
        self.assertEqual(ratificaties[0]["stap"], "stap-002")
        self.assertEqual(ratificaties[0]["status"], "herziening_nodig")
        self.assertIn("stap-003", ratificaties[0]["bewijs"])  # doorloop-vermelding
        self.assertIn("stap-003", uit)                        # zichtbaar voor de mens

    def test_doorloop_na_afkeuring_reconstructie_behandelt_als_heraanbieden(self):
        self.logboek.write_text(json.dumps(self._verwacht_logboek()), encoding="utf-8")
        self._antwoorden = ["1"]
        code, _ = self._run()
        self.assertEqual(code, 0)
        resultaat = reconstructie(self.logboek, _profiel())
        self.assertEqual(resultaat["stappen"]["stap-002"]["beslissing"], "heraanbieden")
        self.assertEqual(resultaat["stappen"]["stap-003"]["beslissing"], "overslaan")

    def test_geen_wachtende_stappen_geen_vraag(self):
        self.logboek.write_text(json.dumps([_entry("stap-001", "geslaagd")]), encoding="utf-8")
        code, uit = self._run()
        self.assertEqual(code, 0)
        self.assertIn("Geen ratificatie-moment", uit)

    def test_nee_is_geen_actie(self):
        origineel = self._verwacht_logboek()
        self.logboek.write_text(json.dumps(origineel), encoding="utf-8")
        self._antwoorden = ["nee"]
        code, uit = self._run()
        self.assertEqual(code, 1)
        self.assertIn("Geen ratificatie", uit)
        entries = json.loads(self.logboek.read_text(encoding="utf-8"))
        self.assertEqual(entries, origineel)


if __name__ == "__main__":
    unittest.main()
