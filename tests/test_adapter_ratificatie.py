"""Adapter-ratificatie (fase 6, taak 3): lijst, goedkeuring, afkeur mét reden.

Regels:
- Zonder bevestiging: alleen de lijst wachtende stappen — niets gewijzigd.
- Met bevestiging: "geratificeerd" per stap; afkeur-entries dragen de reden
  expliciet in de logboek-entry (audit-punt 1); afkeur zonder reden is een
  schema-fout; afkeur van een niet-wachtende stap wordt geweigerd.
"""
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).parent.parent
ADAPTER = REPO / "adapter.py"


def _entry(stap: str, status: str) -> dict:
    return {"stap": stap, "status": status, "bewijs": f"{stap} {status}",
            "tijdstip": "2026-09-03T20:00:00+00:00"}


class RatificeerBasis(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.home = Path(self._tmp.name) / "growkit-home"
        self._oude_env = os.environ.get("GROWKIT_OERWOUD_STAAT")
        os.environ["GROWKIT_OERWOUD_STAAT"] = str(self.home / "oerwoud.json")
        self.doel = Path(self._tmp.name) / "boom"
        self.doel.mkdir()
        self.logboek = self.doel / "logboek.json"
        self.origineel = [
            _entry("stap-001", "geslaagd"),
            _entry("stap-002", "review_ok_wacht_ratificatie"),
            _entry("stap-003", "review_ok_wacht_ratificatie"),
        ]
        self.logboek.write_text(json.dumps(self.origineel), encoding="utf-8")

    def tearDown(self):
        if self._oude_env is None:
            os.environ.pop("GROWKIT_OERWOUD_STAAT", None)
        else:
            os.environ["GROWKIT_OERWOUD_STAAT"] = self._oude_env
        self._tmp.cleanup()

    def roep(self, invoer: dict) -> tuple[int, dict, str]:
        resultaat = subprocess.run(
            [sys.executable, str(ADAPTER), "ratificeer"],
            input=json.dumps(invoer), capture_output=True, text=True,
            env={**os.environ}, cwd=str(REPO), timeout=60)
        try:
            uit = json.loads(resultaat.stdout)
        except json.JSONDecodeError:
            uit = {"_rauw": resultaat.stdout}
        return resultaat.returncode, uit, resultaat.stderr


class TestLijstModus(RatificeerBasis):
    def test_lijst_zonder_bevestiging_wijzigt_niets(self):
        code, uit, _ = self.roep({"doel": str(self.doel)})
        self.assertEqual(code, 0)
        self.assertTrue(uit["ok"])
        self.assertEqual(uit["data"]["stappen"], ["stap-002", "stap-003"])
        self.assertEqual(json.loads(self.logboek.read_text(encoding="utf-8")),
                         self.origineel)

    def test_geen_wachtende_stappen_geeft_lege_lijst(self):
        self.logboek.write_text(json.dumps([_entry("stap-001", "geslaagd")]), encoding="utf-8")
        code, uit, _ = self.roep({"doel": str(self.doel)})
        self.assertEqual(code, 0)
        self.assertEqual(uit["data"]["stappen"], [])


class TestBevestiging(RatificeerBasis):
    def test_bevestiging_ratificeert_alle_wachtende(self):
        code, uit, _ = self.roep({"doel": str(self.doel), "bevestig": True})
        self.assertEqual(code, 0)
        entries = json.loads(self.logboek.read_text(encoding="utf-8"))
        self.assertEqual(entries[:3], self.origineel)           # append-only
        geratificeerd = [e for e in entries if e.get("type") == "ratificatie"]
        self.assertEqual([e["stap"] for e in geratificeerd], ["stap-002", "stap-003"])
        self.assertTrue(all(e["status"] == "geratificeerd" for e in geratificeerd))

    def test_afkeur_met_reden_landt_in_het_logboek(self):
        """Audit-punt 1: de reden die de UI verzamelt komt expliciet in de entry."""
        code, uit, _ = self.roep({"doel": str(self.doel), "bevestig": True,
                                  "afkeur": [{"stap_id": "stap-002",
                                              "reden": "de naam klopt niet met de bedoeling"}]})
        self.assertEqual(code, 0)
        entries = json.loads(self.logboek.read_text(encoding="utf-8"))
        afkeur = [e for e in entries if e.get("type") == "ratificatie"]
        self.assertEqual(len(afkeur), 1)
        self.assertEqual(afkeur[0]["stap"], "stap-002")
        self.assertEqual(afkeur[0]["status"], "herziening_nodig")
        self.assertIn("de naam klopt niet met de bedoeling", afkeur[0]["bewijs"])
        self.assertIn("stap-003", afkeur[0]["bewijs"])          # doorloop-vermelding
        nog_wachtend = [e for e in entries
                        if e["stap"] == "stap-003" and e["status"] == "review_ok_wacht_ratificatie"]
        self.assertEqual(len(nog_wachtend), 1)                  # rest blijft wachten

    def test_afkeur_zonder_reden_is_schema_fout(self):
        code, uit, _ = self.roep({"doel": str(self.doel), "bevestig": True,
                                  "afkeur": [{"stap_id": "stap-002"}]})
        self.assertEqual(code, 1)
        self.assertIn("reden", uit["fout"].lower())
        self.assertEqual(json.loads(self.logboek.read_text(encoding="utf-8")),
                         self.origineel)                        # niets gewijzigd

    def test_afkeur_van_niet_wachtende_stap_wordt_geweigerd(self):
        code, uit, _ = self.roep({"doel": str(self.doel), "bevestig": True,
                                  "afkeur": [{"stap_id": "stap-001", "reden": "x"}]})
        self.assertEqual(code, 1)
        self.assertIn("wacht", uit["fout"].lower())
        self.assertEqual(json.loads(self.logboek.read_text(encoding="utf-8")),
                         self.origineel)


if __name__ == "__main__":
    unittest.main()
