"""Adapter-contract (fase 6, taak 4): bedienaar, niet machthebber.

Regels:
- De adapter bevat geen shell-uitvoering en geen subprocess — hij roept
  uitsluitend kern-functies aan (geen gedupliceerde poort/motor-logica).
- Vrije tekst in verplichte velden kan nooit als commando landen.
- Geen secrets (reviewconfig-inhoud) in de uitvoer.
- Stateless: identieke concept-aanroepen geven identieke output.
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
BRON = ADAPTER.read_text(encoding="utf-8")


class TestBronScan(unittest.TestCase):
    def test_geen_shell_of_subprocess_in_de_adapter(self):
        for verboden in ("subprocess", "os.system", "shell=True", "os.popen"):
            self.assertNotIn(verboden, BRON,
                             f"de adapter mag nooit '{verboden}' bevatten — hij roept kern aan")

    def test_geen_gedupliceerde_poort_of_motor_logica(self):
        for verboden in ("def beoordeel_invoer", "def voer_uit", "def voer_stap_uit",
                         "def controleer", "json_valid", "shell_check"):
            self.assertNotIn(verboden, BRON,
                             f"'{verboden}' hoort in kern/ — de adapter dupliceert geen logica")

    def test_adapter_roept_de_kern_aan(self):
        self.assertIn("from kern", BRON)


class TestVrijeTekstIsGeenCommando(unittest.TestCase):
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
            env={**os.environ}, cwd=str(REPO), timeout=60)
        try:
            uit = json.loads(resultaat.stdout)
        except json.JSONDecodeError:
            uit = {"_rauw": resultaat.stdout}
        return resultaat.returncode, uit, resultaat.stderr

    def test_shell_meta_in_profielnaam_landt_nooit_in_een_shell(self):
        pwn = Path(self._tmp.name) / "pwn-marker"
        kwaadaardig = f"niet-een-profiel; touch {pwn}"
        code, uit, _ = self.roep("plant", {"profiel": kwaadaardig,
                                           "doel": str(Path(self._tmp.name) / "boom")})
        self.assertEqual(code, 1)
        self.assertIn("onbekend profiel", uit["fout"].lower())
        self.assertFalse(pwn.exists())                       # er is nooit een shell geweest

    def test_shell_meta_in_doel_is_gewoon_een_pad_en_wordt_niet_uitgevoerd(self):
        vreemd_doel = Path(self._tmp.name) / "echo GEHACKT; touch marker"
        code, uit, _ = self.roep("plant", {"profiel": "tweede-brein",
                                           "doel": str(vreemd_doel)})
        self.assertEqual(code, 0)                            # concept-modus
        self.assertTrue(uit["data"]["bevestiging_vereist"])
        self.assertFalse(vreemd_doel.exists())               # niets aangemaakt of uitgevoerd

    def test_shell_meta_in_profielnaam_bij_bevestiging_landt_nooit_in_een_shell(self):
        pwn = Path(self._tmp.name) / "pwn-marker-2"
        kwaadaardig = f"tweede-brein; touch {pwn}"
        code, uit, _ = self.roep("plant", {"profiel": kwaadaardig,
                                           "doel": str(Path(self._tmp.name) / "boom"),
                                           "bevestig": True})
        self.assertEqual(code, 1)
        self.assertIn("onbekend profiel", uit["fout"].lower())
        self.assertFalse(pwn.exists())


class TestGeenSecrets(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.home = Path(self._tmp.name) / "growkit-home"
        self._oude_env = os.environ.get("GROWKIT_OERWOUD_STAAT")
        os.environ["GROWKIT_OERWOUD_STAAT"] = str(self.home / "oerwoud.json")
        self._rc = REPO / "reviewconfig.json"
        self._had_rc = self._rc.exists()
        self._backup = self._rc.read_text(encoding="utf-8") if self._had_rc else None
        self._rc.write_text(json.dumps({
            "rollen": {"reviewer": {"type": "cli", "commando": "echo geslaagd",
                                    "interne-notitie": "SECRETS-TOKEN-7X"}}}), encoding="utf-8")
        self.doel = Path(self._tmp.name) / "boom"
        self.doel.mkdir()
        (self.doel / "geboortebewijs.json").write_text(json.dumps({
            "boom_id": "x", "profiel": "tweede-brein", "machine": "mac",
            "locatie": str(self.doel), "geplant_op": "2026-09-03T20:00:00+00:00"}),
            encoding="utf-8")
        (self.doel / "logboek.json").write_text("[]", encoding="utf-8")

    def tearDown(self):
        if self._had_rc:
            self._rc.write_text(self._backup, encoding="utf-8")
        else:
            self._rc.unlink()
        if self._oude_env is None:
            os.environ.pop("GROWKIT_OERWOUD_STAAT", None)
        else:
            os.environ["GROWKIT_OERWOUD_STAAT"] = self._oude_env
        self._tmp.cleanup()

    def test_reviewconfig_inhoud_komt_nooit_in_de_uitvoer(self):
        scenarios = [("status", {"doel": str(self.doel)}),
                      ("profielen", {}),
                      ("plant", {"profiel": "tweede-brein",
                                 "doel": str(Path(self._tmp.name) / "nieuw")})]
        for commando, invoer in scenarios:
            resultaat = subprocess.run(
                [sys.executable, str(ADAPTER), commando],
                input=json.dumps(invoer), capture_output=True, text=True,
                env={**os.environ}, cwd=str(REPO), timeout=60)
            self.assertNotIn("SECRETS-TOKEN-7X", resultaat.stdout, f"lekkage bij {commando}")
            self.assertNotIn("SECRETS-TOKEN-7X", resultaat.stderr, f"lekkage bij {commando}")


class TestStateless(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.home = Path(self._tmp.name) / "growkit-home"
        self._oude_env = os.environ.get("GROWKIT_OERWOUD_STAAT")
        os.environ["GROWKIT_OERWOUD_STAAT"] = str(self.home / "oerwoud.json")
        self.doel = Path(self._tmp.name) / "boom"

    def tearDown(self):
        if self._oude_env is None:
            os.environ.pop("GROWKIT_OERWOUD_STAAT", None)
        else:
            os.environ["GROWKIT_OERWOUD_STAAT"] = self._oude_env
        self._tmp.cleanup()

    def test_identieke_concept_aanroepen_geven_identieke_output(self):
        resultaten = []
        for _ in range(2):
            resultaat = subprocess.run(
                [sys.executable, str(ADAPTER), "plant"],
                input=json.dumps({"profiel": "tweede-brein", "doel": str(self.doel)}),
                capture_output=True, text=True, env={**os.environ}, cwd=str(REPO), timeout=60)
            resultaten.append(resultaat.stdout)
        self.assertEqual(resultaten[0], resultaten[1])       # geen verborgen sessie
        self.assertFalse(self.doel.exists())                 # nog steeds niets uitgevoerd


if __name__ == "__main__":
    unittest.main()
