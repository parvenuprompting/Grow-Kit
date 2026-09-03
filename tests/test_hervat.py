"""State-reconstructie (§7, §11.4): herstart leest het logboek, nooit blind herdraaien.

Regels (fase 4, taak 2):
- geslaagd / review_ok_wacht_ratificatie → "overslaan" (niet-idempotent geslaagd
  krijgt de noot "nooit herdraaien").
- wacht_op_mens / gefaald / herziening_nodig → "heraanbieden" (na mens-fix).
- stap zonder log-entry → "uitvoeren".
- Onbekende status → "heraanbieden" mét noot — nooit stilzwijgend overslaan.
- Herstartpunt = laatste bevestigde mijlpaal; zonder → "start".
- Corrupt JSON → foutstatus "corrupt_logboek", geen exceptie naar buiten.
"""
import json
import tempfile
import unittest
from pathlib import Path

from kern.growkit_hervat import reconstructie


def _profiel(n: int = 3, niet_idempotent: set[str] | None = None) -> dict:
    niet_idempotent = niet_idempotent or set()
    return {
        "profiel": "test-boom",
        "stappen": [
            {"id": f"stap-{i:03d}", "idempotent": f"stap-{i:03d}" not in niet_idempotent}
            for i in range(1, n + 1)
        ],
    }


def _entry(stap: str, status: str) -> dict:
    return {"stap": stap, "status": status, "bewijs": f"{stap} {status}", "tijdstip": "2026-09-03T20:00:00+00:00"}


class TestBeslissingen(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.pad = Path(self._tmp.name) / "logboek.json"

    def tearDown(self):
        self._tmp.cleanup()

    def _log(self, entries: list[dict], profiel: dict) -> dict:
        self.pad.write_text(json.dumps(entries), encoding="utf-8")
        return reconstructie(self.pad, profiel)

    def test_geslaagde_idempotente_stap_wordt_overgeslagen(self):
        result = self._log([_entry("stap-001", "geslaagd")], _profiel(2))
        self.assertEqual(result["stappen"]["stap-001"]["beslissing"], "overslaan")

    def test_geslaagde_niet_idempotente_stap_krijgt_nooit_herdraai_noot(self):
        result = self._log([_entry("stap-002", "geslaagd")], _profiel(2, niet_idempotent={"stap-002"}))
        beslissing = result["stappen"]["stap-002"]
        self.assertEqual(beslissing["beslissing"], "overslaan")
        self.assertIn("nooit herdraaien", beslissing["noot"])

    def test_gefaalde_stap_wordt_heraangeboden(self):
        result = self._log([_entry("stap-003", "gefaald")], _profiel(3))
        self.assertEqual(result["stappen"]["stap-003"]["beslissing"], "heraanbieden")

    def test_review_ok_wacht_op_ratificatie_zonder_herdraai(self):
        result = self._log([_entry("stap-002", "review_ok_wacht_ratificatie")], _profiel(3))
        beslissing = result["stappen"]["stap-002"]
        self.assertEqual(beslissing["beslissing"], "overslaan")
        self.assertIn("ratificatie", beslissing["noot"].lower())

    def test_herziening_nodig_wordt_heraangeboden(self):
        """Gat-review 3 sept: deze status ontstaat in taak 5, maar de afbeelding
        bestaat vanaf de geboorte van de functie — geen mazen."""
        result = self._log([_entry("stap-001", "herziening_nodig")], _profiel(2))
        self.assertEqual(result["stappen"]["stap-001"]["beslissing"], "heraanbieden")

    def test_stap_zonder_logregel_wordt_uitgevoerd(self):
        result = self._log([_entry("stap-001", "geslaagd")], _profiel(3))
        self.assertEqual(result["stappen"]["stap-003"]["beslissing"], "uitvoeren")

    def test_onbekende_status_wordt_nooit_stilzwijgend_overgeslagen(self):
        result = self._log([_entry("stap-001", "status-onbestaand")], _profiel(2))
        beslissing = result["stappen"]["stap-001"]
        self.assertEqual(beslissing["beslissing"], "heraanbieden")
        self.assertTrue(beslissing["noot"])

    def test_laaste_entry_wint_append_only(self):
        result = self._log([_entry("stap-001", "gefaald"), _entry("stap-001", "geslaagd")], _profiel(2))
        self.assertEqual(result["stappen"]["stap-001"]["beslissing"], "overslaan")


class TestHerstartpunt(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.pad = Path(self._tmp.name) / "logboek.json"

    def tearDown(self):
        self._tmp.cleanup()

    def _log(self, entries: list[dict]) -> dict:
        self.pad.write_text(json.dumps(entries), encoding="utf-8")
        return reconstructie(self.pad, _profiel(2))

    def test_zonder_mijlpaal_is_het_herstartpunt_de_start(self):
        self.assertEqual(self._log([_entry("stap-001", "geslaagd")])["herstartpunt"], "start")

    def test_laatste_bevestigde_mijlpaal_is_het_herstartpunt(self):
        mijlpaal = {"type": "mijlpaal", "stap": "mijlpaal-start", "status": "bevestigd",
                    "bewijs": "bevestigd door de mens", "tijdstip": "2026-09-03T19:00:00+00:00"}
        result = self._log([mijlpaal, _entry("stap-001", "geslaagd")])
        self.assertEqual(result["herstartpunt"]["stap"], "mijlpaal-start")
        self.assertEqual(result["herstartpunt"]["tijdstip"], mijlpaal["tijdstip"])


class TestCorruptLogboek(unittest.TestCase):
    def test_corrupt_json_geeft_foutstatus_geen_crash(self):
        with tempfile.TemporaryDirectory() as tmp:
            pad = Path(tmp) / "logboek.json"
            pad.write_text("{half geschreven", encoding="utf-8")
            result = reconstructie(pad, _profiel(2))
            self.assertEqual(result["fout"], "corrupt_logboek")
            self.assertNotIn("stappen", result)

    def test_afwezig_logboek_is_een_frisse_start(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = reconstructie(Path(tmp) / "ontbreekt.json", _profiel(2))
            self.assertIsNone(result["fout"])
            self.assertEqual(result["herstartpunt"], "start")
            self.assertTrue(all(s["beslissing"] == "uitvoeren" for s in result["stappen"].values()))


if __name__ == "__main__":
    unittest.main()
