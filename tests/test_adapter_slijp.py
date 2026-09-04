"""Slice 1 (fase 6.2) — adapter-commando `slijp`: chat-invoer door de Scope-poort.

Contract:
- `{"tekst": "..."}` → {"ok": true, "data": {geaccepteerd, concept|weigering, vragen}}.
- Alle interpretatie blijft in de poort; de adapter voegt niets toe.
- Weigering en acceptatie worden append-only gelogd in het slijper-logboek.
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


class SlijpBasis(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.home = Path(self._tmp.name) / "growkit-home"
        self._oude_env = os.environ.get("GROWKIT_OERWOUD_STAAT")
        self._oude_slijp = os.environ.get("GROWKIT_SLIJPER_LOG")
        os.environ["GROWKIT_OERWOUD_STAAT"] = str(self.home / "oerwoud.json")
        os.environ["GROWKIT_SLIJPER_LOG"] = str(self.home / "slijper-logboek.json")

    def tearDown(self):
        if self._oude_slijp is None:
            os.environ.pop("GROWKIT_OERWOUD_STAAT", None)
        else:
            os.environ["GROWKIT_OERWOUD_STAAT"] = self._oude_env
        if self._oude_slijp is None:
            os.environ.pop("GROWKIT_SLIJPER_LOG", None)
        else:
            os.environ["GROWKIT_SLIJPER_LOG"] = self._oude_slijp
        self._tmp.cleanup()

    def roep(self, commando: str, invoer: dict) -> tuple[int, dict, str]:
        resultaat = subprocess.run(
            [sys.executable, str(ADAPTER), commando],
            input=json.dumps(invoer), capture_output=True, text=True,
            env={**os.environ}, cwd=str(REPO), timeout=60)
        try:
            uit = json.loads(resultaat.stdout)
        except json.JSONDecodeError:
            uit = {"_rauw": resultaat.stdout}
        return resultaat.returncode, uit, resultaat.stderr


class TestSlijp(SlijpBasis):
    def test_geen_tekst_is_nette_fout(self):
        exit_code, uit, _ = self.roep("slijp", {"tekst": ""})
        self.assertEqual(exit_code, 1)
        self.assertFalse(uit["ok"])
        self.assertIn("tekst", uit["fout"])

    def test_vage_prompt_wordt_geweigerd_met_vragen(self):
        exit_code, uit, _ = self.roep("slijp", {"tekst": "doe leuk iets"})
        self.assertEqual(exit_code, 0)
        self.assertTrue(uit["ok"])
        self.assertFalse(uit["data"]["geaccepteerd"])
        self.assertIn("bui", uit["data"]["weigering"])
        self.assertTrue(uit["data"]["vragen"])          # §11.3-vragen
        self.assertEqual(
            {v["vraag"] for v in uit["data"]["vragen"]},
            {"Waar moet het groeien (omgeving)?",
             "Wanneer is het geslaagd (slaag-criterium)?"})

    def test_alle_velden_gevuld_geeft_concept_wacht_op_mens(self):
        exit_code, uit, _ = self.roep("slijp", {
            "tekst": "een tweede brein voor notities",
            "omgeving": "deze machine (lokaal)",
            "slaag_criterium": "structuur bestaat en logboek is leeg"})
        self.assertEqual(exit_code, 0)
        data = uit["data"]
        self.assertTrue(data["geaccepteerd"])
        concept = data["concept"]
        self.assertEqual(concept["status"], "wacht_op_mens")
        self.assertEqual(concept["einddoel"], "een tweede brein voor notities")
        self.assertIn("bron", concept)

    def test_schuring_wordt_append_only_gelogd(self):
        self.roep("slijp", {"tekst": "doe leuk iets"})
        self.roep("slijp", {"tekst": "een tweede brein",
                            "omgeving": "deze machine (lokaal)",
                            "slaag_criterium": "structuur bestaat en logboek is leeg"})
        log = json.loads(self.home.joinpath("slijper-logboek.json").read_text(encoding="utf-8"))
        recente = [e for e in log if e.get("ruw") in
                   ("doe leuk iets", "een tweede brein")]
        self.assertEqual(len(recente), 2)
        self.assertEqual(recente[0]["beslissing"], "geweigerd")
        self.assertEqual(recente[1]["beslissing"], "geaccepteerd_concept")


if __name__ == "__main__":
    unittest.main()
