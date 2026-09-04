"""Slice 6 — nachtfabriek-modus (docs/ROADMAP-SLICES.md).

De app als avond-controller van de autonome nachtronde. Nieuwe
adapter-commando's:

- `nachtplan`: stel de nachtronde voor een boom samen — puur lezend concept
    {"doel": ..., "taken": [taak-ids], "brein_pad"?}
  zonder "bevestig": {"concept": ..., "bevestiging_vereist": true, "plan": {...}}
  met    "bevestig": true: het plan wordt append-only weggeschreven naar
  groei/nachtplan.json (per boom). Geen poort-vrije uitvoering: het plan is
  een opdracht aan het harnas, nooit een directe uitvoering.

- `nachtstatus`: lees het plan + de uitvoeringsgeschiedenis
    {"doel": ...}
  → {"plan": {...}|None, "rondes": [{start, einde?, geslaagd?, taken}]|None,
     "levensignaal": {...}}  (één bron met Slice 2)

- `nachtronde`: voer één geplande ronde uit — het harnas zelf, niet de app:
    {"doel": ..., "bevestig": true}
  Voor elke taak in het plan: poort eerst (valideer_taak), dan de bestaande
  taak-kern. Append-only rondverslag in groei/nachtrondes.json. Geen retries,
  geen stilzwijgend overslaan: een faal eindigt de ronde (faalcontract) en
  wordt gerapporteerd. Ronde zonder plan of zonder bevestiging → geweigerd.
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

_GELDIGE_TAAK = {
    "id": "taak-nacht-1", "titel": "kweekbestand",
    "commando": "printf x > kweek-nacht.txt && echo KWEEK-OK",
    "bewijs": {"type": "shell_check",
               "commando": "test -f kweek-nacht.txt && echo KWEEK-OK",
               "verwacht_substr": "KWEEK-OK"},
}


class NachtBasis(unittest.TestCase):
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

    def _boom(self, naam: str = "boom", taken: list[dict] | None = None) -> Path:
        doel = Path(self._tmp.name) / naam
        doel.mkdir(parents=True, exist_ok=True)
        (doel / "geboortebewijs.json").write_text(json.dumps({
            "boom_id": f"boom-{naam}", "profiel": "dev-werkplaats",
            "machine": "test", "locatie": str(doel),
            "geplant_op": "2026-09-04T09:00:00+00:00"}), encoding="utf-8")
        (doel / "logboek.json").write_text(json.dumps([
            {"stap": "taak-001", "status": "geslaagd", "bewijs": "ok",
             "tijdstip": "2026-09-04T09:05:00+00:00"}]), encoding="utf-8")
        if taken:
            (doel / "takenlijst.json").write_text(json.dumps(taken), encoding="utf-8")
        return doel


class NachtPlan(NachtBasis):
    def test_concept_zonder_bevestiging_schrijft_niets(self):
        doel = self._boom(taken=[_GELDIGE_TAAK])
        code, uit, _ = self.roep("nachtplan", {"doel": str(doel),
                                               "taken": ["taak-nacht-1"]})
        self.assertEqual(code, 0)
        self.assertTrue(uit["data"]["bevestiging_vereist"])
        self.assertFalse((doel / "nachtplan.json").exists())

    def test_plan_met_bevestiging_wordt_append_only_weggeschreven(self):
        doel = self._boom(taken=[_GELDIGE_TAAK])
        code, uit, _ = self.roep("nachtplan", {"doel": str(doel),
                                               "taken": ["taak-nacht-1"],
                                               "bevestig": True})
        self.assertEqual(code, 0)
        plan = json.loads((doel / "nachtplan.json").read_text(encoding="utf-8"))
        self.assertEqual(plan["taken"], ["taak-nacht-1"])
        self.assertIn("aangemaakt", plan)

    def test_herschrijven_geweigerd_nooit_overschrijven(self):
        doel = self._boom(taken=[_GELDIGE_TAAK])
        self.roep("nachtplan", {"doel": str(doel), "taken": ["taak-nacht-1"],
                                "bevestig": True})
        code, uit, _ = self.roep("nachtplan", {"doel": str(doel),
                                               "taken": ["taak-nacht-1"],
                                               "bevestig": True})
        self.assertEqual(code, 1)
        self.assertIn("nooit overschrijven", uit["fout"].lower())

    def test_onbekende_taak_in_plan_geweigerd(self):
        doel = self._boom(taken=[_GELDIGE_TAAK])
        code, uit, _ = self.roep("nachtplan", {"doel": str(doel),
                                               "taken": ["bestaat-niet"],
                                               "bevestig": True})
        self.assertEqual(code, 1)
        self.assertFalse((doel / "nachtplan.json").exists())

    def test_taak_zonder_bewijs_kan_niet_in_het_plan(self):
        doel = self._boom(taken=[{"id": "taak-leeg", "titel": "zonder bewijs"}])
        code, uit, _ = self.roep("nachtplan", {"doel": str(doel),
                                               "taken": ["taak-leeg"],
                                               "bevestig": True})
        self.assertEqual(code, 1)
        self.assertIn("bewijs", uit["fout"].lower())


class NachtRonde(NachtBasis):
    def test_ronde_zonder_plan_geweigerd(self):
        doel = self._boom(taken=[_GELDIGE_TAAK])
        code, uit, _ = self.roep("nachtronde", {"doel": str(doel), "bevestig": True})
        self.assertEqual(code, 1)
        self.assertIn("plan", uit["fout"].lower())

    def test_ronde_zonder_bevestiging_geweigerd(self):
        doel = self._boom(taken=[_GELDIGE_TAAK])
        self.roep("nachtplan", {"doel": str(doel), "taken": ["taak-nacht-1"],
                                "bevestig": True})
        code, uit, _ = self.roep("nachtronde", {"doel": str(doel)})
        self.assertEqual(code, 0)
        self.assertTrue(uit["data"]["bevestiging_vereist"])
        # concept alleen: niets uitgevoerd
        self.assertFalse((doel / "kweek-nacht.txt").exists())

    def test_ronde_voert_taken_uit_en_logt_append_only(self):
        doel = self._boom(taken=[_GELDIGE_TAAK])
        self.roep("nachtplan", {"doel": str(doel), "taken": ["taak-nacht-1"],
                                "bevestig": True})
        code, uit, _ = self.roep("nachtronde", {"doel": str(doel), "bevestig": True})
        self.assertEqual(code, 0)
        self.assertTrue((doel / "kweek-nacht.txt").exists())
        rondes = json.loads((doel / "nachtrondes.json").read_text(encoding="utf-8"))
        self.assertEqual(len(rondes), 1)
        self.assertEqual(rondes[0]["geslaagd"], True)
        # run-latch (Slice 2): gestart + beeindigd in het boom-logboek
        entries = json.loads((doel / "logboek.json").read_text(encoding="utf-8"))
        runs = [e["status"] for e in entries if e.get("type") == "run"]
        self.assertIn("gestart", runs)
        self.assertIn("beeindigd", runs)

    def test_faalcontract_eindigt_de_ronde_geen_retries(self):
        faal_taak = {"id": "taak-faal", "titel": "faalt",
                     "commando": "exit 1",
                     "bewijs": {"type": "shell_check",
                                "commando": "test -f nooit-bestand.txt",
                                "verwacht_substr": "X"}}
        doel = self._boom(taken=[faal_taak, _GELDIGE_TAAK])
        self.roep("nachtplan", {"doel": str(doel),
                                "taken": ["taak-faal", "taak-nacht-1"],
                                "bevestig": True})
        code, uit, _ = self.roep("nachtronde", {"doel": str(doel), "bevestig": True})
        self.assertEqual(code, 2)                     # faalcontract: exit 2
        rondes = json.loads((doel / "nachtrondes.json").read_text(encoding="utf-8"))
        self.assertEqual(rondes[0]["geslaagd"], False)
        # geen retries: taak-faal precies één keer geprobeerd
        zelfde = [r for r in rondes[0]["taken"] if r["taak"] == "taak-faal"]
        self.assertEqual(len(zelfde), 1)
        self.assertEqual(zelfde[0]["status"], "gefaald")
        # taak na de faal is niet meer uitgevoerd (ronde eindigt)
        self.assertFalse((doel / "kweek-nacht.txt").exists())


class NachtStatus(NachtBasis):
    def test_status_zonder_plan(self):
        doel = self._boom()
        code, uit, _ = self.roep("nachtstatus", {"doel": str(doel)})
        self.assertEqual(code, 0)
        self.assertIsNone(uit["data"]["plan"])
        self.assertIsNone(uit["data"]["rondes"])
        self.assertIn("levensignaal", uit["data"])

    def test_status_met_plan_en_ronde(self):
        doel = self._boom(taken=[_GELDIGE_TAAK])
        self.roep("nachtplan", {"doel": str(doel), "taken": ["taak-nacht-1"],
                                "bevestig": True})
        self.roep("nachtronde", {"doel": str(doel), "bevestig": True})
        code, uit, _ = self.roep("nachtstatus", {"doel": str(doel)})
        self.assertEqual(code, 0)
        self.assertEqual(uit["data"]["plan"]["taken"], ["taak-nacht-1"])
        self.assertEqual(len(uit["data"]["rondes"]), 1)
        self.assertEqual(uit["data"]["rondes"][0]["geslaagd"], True)


if __name__ == "__main__":
    unittest.main()
