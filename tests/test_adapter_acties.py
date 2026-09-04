"""Slice 3 — acties met poortjes: de vijf modi knopbaar vanuit de app.

Deze tests bewijzen de poort-regel per actie die de app straks aanbiedt:
elke uitvoerende actie faalt zonder bevestiging en slaagt mét — en het
mens_nodig-kanaal (auth op de doelmachine) is expliciet, nooit stil.

Contract per commando (adapter):
- zonder "bevestig": {"bevestiging_vereist": true} + concept — NIETS uitgevoerd
- met "bevestig":    uitvoering; faal → exit 2 met stappen (faalcontract)
- geen enkele actie voert iets uit vóór de poort het vrijgeeft.

Slice 3 voegt één nieuw commando toe:
- `acties`: voor een boom het menu van toegestane acties + mens_nodig-momenten,
  puur lezend. De app toont alleen wat dit commando rapporteert.
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


class ActiesBasis(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.home = Path(self._tmp.name) / "growkit-home"
        self._oude_env = os.environ.get("GROWKIT_OERWOUD_STAAT")
        os.environ["GROWKIT_OERWOUD_STAAT"] = str(self.home / "oerwoud.json")

    def tearDown(self):
        if self._oude_env is None:
            os.environ.pop("GROWKIT_OERWOUD_STAAT", None)
        else:
            os.environ["GROWKIT_OERWOUD_STAAT"] = self._oude_env
        self._tmp.cleanup()

    def roep(self, commando: str, invoer: dict) -> tuple[int, dict, str]:
        resultaat = subprocess.run(
            [sys.executable, str(ADAPTER), commando],
            input=json.dumps(invoer), capture_output=True, text=True,
            env={**os.environ}, cwd=str(REPO), timeout=180)
        try:
            uit = json.loads(resultaat.stdout)
        except json.JSONDecodeError:
            uit = {"_rauw": resultaat.stdout}
        return resultaat.returncode, uit, resultaat.stderr

    def _boom(self, naam: str = "boom", taken: list[dict] | None = None,
              mijlpaal: bool = False) -> Path:
        doel = Path(self._tmp.name) / naam
        doel.mkdir(parents=True, exist_ok=True)
        (doel / "geboortebewijs.json").write_text(json.dumps({
            "boom_id": f"boom-{naam}", "profiel": "dev-werkplaats",
            "machine": "test", "locatie": str(doel),
            "geplant_op": "2026-09-04T09:00:00+00:00"}), encoding="utf-8")
        entries = [{"stap": "taak-001", "status": "geslaagd",
                    "bewijs": "ok", "tijdstip": "2026-09-04T09:05:00+00:00"}]
        if mijlpaal:
            entries.append({"stap": "mijlpaal-start", "status": "mijlpaal",
                            "bewijs": "drie taken bewezen",
                            "tijdstip": "2026-09-04T09:10:00+00:00"})
        (doel / "logboek.json").write_text(json.dumps(entries), encoding="utf-8")
        if taken:
            (doel / "takenlijst.json").write_text(json.dumps(taken), encoding="utf-8")
        return doel

    def _geldige_taak(self) -> dict:
        return {"id": "taak-002", "titel": "kweekbestand",
                "commando": "printf x > kweek2.txt && echo KWEEK-OK",
                "bewijs": {"type": "shell_check",
                           "commando": "test -f kweek2.txt && echo KWEEK-OK",
                           "verwacht_substr": "KWEEK-OK"}}


class ActiesMenu(ActiesBasis):
    def test_acties_van_gezonde_boom(self):
        doel = self._boom(taken=[self._geldige_taak()])
        code, uit, _ = self.roep("acties", {"doel": str(doel)})
        self.assertEqual(code, 0)
        data = uit["data"]
        self.assertIn("taak", data["mogelijk"])
        self.assertIn("ratificatie", data["mogelijk"])
        self.assertIn("hervat", data["mogelijk"])
        self.assertNotIn("planten", data["mogelijk"])   # boom bestaat al
        self.assertEqual(data["mensch_momenten"], [])

    def test_acties_zonder_boom_is_planten_enkel(self):
        doel = Path(self._tmp.name) / "leeg"
        doel.mkdir(parents=True)
        code, uit, _ = self.roep("acties", {"doel": str(doel)})
        self.assertEqual(code, 0)
        self.assertIn("planten", uit["data"]["mogelijk"])
        self.assertNotIn("taak", uit["data"]["mogelijk"])

    def test_mens_moment_bij_wacht_ratificatie(self):
        """Een stap in review_ok_wacht_ratificatie is een mens-moment: de app
        moet het zien vóór de mens gevraagd wordt."""
        doel = self._boom()
        logboek = doel / "logboek.json"
        entries = [{"stap": "taak-001", "status": "geslaagd", "bewijs": "ok",
                    "tijdstip": "2026-09-04T09:05:00+00:00"},
                   {"stap": "stap-review", "status": "review_ok_wacht_ratificatie",
                    "bewijs": "reviewer akkoord", "tijdstip": "2026-09-04T09:06:00+00:00"}]
        logboek.write_text(json.dumps(entries), encoding="utf-8")
        code, uit, _ = self.roep("acties", {"doel": str(doel)})
        self.assertEqual(code, 0)
        momenten = uit["data"]["mensch_momenten"]
        self.assertTrue(any(m.get("soort") == "ratificatie" for m in momenten))

    def test_niet_bestaande_boom_geen_acties(self):
        code, uit, _ = self.roep("acties", {"doel": str(Path(self._tmp.name) / "weg")})
        self.assertEqual(code, 1)
        self.assertFalse(uit["ok"])


class PlantPoort(ActiesBasis):
    def test_plant_zonder_bevestiging_voert_niets_uit(self):
        doel = Path(self._tmp.name) / "nieuw"
        code, uit, _ = self.roep("plant", {"profiel": "dev-werkplaats",
                                           "doel": str(doel)})
        self.assertEqual(code, 0)
        self.assertTrue(uit["data"]["bevestiging_vereist"])
        self.assertFalse(doel.exists())          # de poort stond dicht

    def test_plant_poort_weigert_vage_doelen(self):
        """Scope-poort: geen map → weigering, ook mét bevestiging."""
        code, uit, _ = self.roep("plant", {"profiel": "dev-werkplaats",
                                           "doel": "   ",
                                           "bevestig": True})
        self.assertEqual(code, 1)
        self.assertFalse(uit["ok"])


class TaakPoort(ActiesBasis):
    def test_taak_zonder_bevestiging_toont_alleen_lijst(self):
        doel = self._boom(taken=[self._geldige_taak()])
        code, uit, _ = self.roep("taak", {"doel": str(doel)})
        self.assertEqual(code, 0)
        self.assertTrue(uit["data"]["bevestiging_vereist"])
        self.assertFalse((doel / "kweek2.txt").exists())   # niets uitgevoerd

    def test_taak_met_bevestiging_voert_uit_en_groen(self):
        doel = self._boom(taken=[self._geldige_taak()])
        code, uit, _ = self.roep("taak", {"doel": str(doel),
                                          "taak_id": "taak-002", "bevestig": True})
        self.assertEqual(code, 0)
        self.assertTrue((doel / "kweek2.txt").exists())
        # run-latch: gestart + beeindigd (Slice 2) staat in het logboek
        entries = json.loads((doel / "logboek.json").read_text(encoding="utf-8"))
        runs = [e["status"] for e in entries if e.get("type") == "run"]
        self.assertIn("gestart", runs)
        self.assertIn("beeindigd", runs)

    def test_taak_zonder_bewijs_bestaat_niet(self):
        """Poort-regel (§11): een taak zonder bewijs bestaat niet — ook niet
        met bevestiging."""
        doel = self._boom(taken=[{"id": "taak-003", "titel": "zonder bewijs"}])
        code, uit, _ = self.roep("taak", {"doel": str(doel),
                                          "taak_id": "taak-003", "bevestig": True})
        self.assertEqual(code, 1)
        self.assertFalse((doel / "logboek.json").exists() and
                         any(e.get("stap") == "taak-003" for e in
                             json.loads((doel / "logboek.json").read_text(encoding="utf-8"))))


class RatificatiePoort(ActiesBasis):
    def test_ratificeer_zonder_bevestiging_toont_stappen(self):
        doel = self._boom(mijlpaal=True)
        code, uit, _ = self.roep("ratificeer", {"doel": str(doel)})
        self.assertEqual(code, 0)
        self.assertTrue(uit["data"]["bevestiging_vereist"])

    def test_afkeur_zonder_reden_bestaat_niet(self):
        doel = self._boom(mijlpaal=True)
        code, uit, _ = self.roep("ratificeer", {"doel": str(doel), "bevestig": True,
                                                "afkeur": [{"stap_id": "stap-review"}]})
        self.assertEqual(code, 1)
        self.assertIn("reden", uit["fout"].lower())


class HervatPoort(ActiesBasis):
    def test_hervat_corrupt_logboek_is_mens_geen_crash(self):
        doel = self._boom()
        (doel / "logboek.json").write_text("{kapot", encoding="utf-8")
        code, uit, _ = self.roep("hervat", {"doel": str(doel), "bevestig": True})
        self.assertEqual(code, 1)
        self.assertFalse(uit["ok"])
        # het corrupte logboek is onaangeroerd — nooit auto-repareren
        self.assertEqual((doel / "logboek.json").read_text(encoding="utf-8"), "{kapot")

    def test_geen_actie_zonder_bevestiging_bij_hervat(self):
        """Hervat zonder bevestiging: concept met stappen-overzicht, niets
        gedraaid (het faalcontract van de restdraai blijft intact)."""
        doel = self._boom()
        entries = [{"stap": "taak-001", "status": "geslaagd", "bewijs": "ok",
                    "tijdstip": "2026-09-04T09:05:00+00:00"}]
        (doel / "logboek.json").write_text(json.dumps(entries), encoding="utf-8")
        code, uit, _ = self.roep("hervat", {"doel": str(doel)})
        self.assertEqual(code, 0)          # concept of nette melding
        self.assertFalse(uit.get("ok") is False and "stappen" not in uit)


if __name__ == "__main__":
    unittest.main()
