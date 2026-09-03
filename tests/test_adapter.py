"""Adapter-grondslag (fase 6, taak 1): machine-leesbaar JSON-protocol.

Contract:
- `python3 adapter.py <commando>` — JSON in via stdin, precies één
  JSON-document uit op stdout; mens-leesbare tekst naar stderr.
- Fouten: {"ok": false, "fout": "<NL>"} met exit 1 — nooit een traceback.
- Onbekend/geen commando → nette fout mét de commando-lijst.
- status: identiteit, register, tellers, laatste mijlpaal/faal als data.
- profielen: bewezen profielen + "uit je brein"-opties.
"""
import json
import os
import subprocess
import sys
import tempfile
import unittest
import uuid
from pathlib import Path

REPO = Path(__file__).parent.parent
ADAPTER = REPO / "adapter.py"


class AdapterBasis(unittest.TestCase):
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

    def roep(self, commando: str, invoer: dict | None = None) -> tuple[int, dict, str]:
        """Roep de adapter aan als echt subprocess; retourneert (exit, json, stderr)."""
        resultaat = subprocess.run(
            [sys.executable, str(ADAPTER), commando],
            input=json.dumps(invoer or {}), capture_output=True, text=True,
            env={**os.environ}, cwd=str(REPO), timeout=60)
        try:
            uit = json.loads(resultaat.stdout)
        except json.JSONDecodeError:
            uit = {"_rauw": resultaat.stdout}
        return resultaat.returncode, uit, resultaat.stderr

    def _boom(self, naam: str = "boom", corrupt_logboek: bool = False) -> Path:
        doel = Path(self._tmp.name) / naam
        doel.mkdir(parents=True)
        (doel / "geboortebewijs.json").write_text(json.dumps({
            "boom_id": str(uuid.uuid4()), "profiel": "tweede-brein", "machine": "mac",
            "locatie": str(doel.resolve()),
            "geplant_op": "2026-09-03T20:00:00+00:00"}), encoding="utf-8")
        if corrupt_logboek:
            (doel / "logboek.json").write_text("{half", encoding="utf-8")
        else:
            (doel / "logboek.json").write_text("[]", encoding="utf-8")
        return doel


class TestStatus(AdapterBasis):
    def test_status_retourneert_identiteit_register_en_tellers(self):
        from kern.growkit_oerwoud import sla_brein_pad
        doel = self._boom("boom")
        brein = Path(self._tmp.name) / "brein"
        brein.mkdir()
        (brein / "register").mkdir()
        boom_id = json.loads((doel / "geboortebewijs.json").read_text(encoding="utf-8"))["boom_id"]
        (brein / "register" / "bomen.json").write_text(json.dumps([
            {"type": "geboorte", "boom_id": boom_id, "profiel": "tweede-brein",
             "machine": "mac", "locatie": str(doel.resolve()),
             "geplant_op": "2026-09-03T20:00:00+00:00", "tijdstip": "2026-09-03T20:00:01+00:00"},
        ]), encoding="utf-8")
        sla_brein_pad(brein)
        code, uit, _ = self.roep("status", {"doel": str(doel)})
        self.assertEqual(code, 0)
        self.assertTrue(uit["ok"])
        self.assertEqual(uit["data"]["identiteit"]["boom_id"], boom_id)
        self.assertEqual(uit["data"]["register"]["status"], "geboorte")
        self.assertEqual(uit["data"]["tellers"], {"wachtend": 0, "verzonden": 0})

    def test_status_zonder_geboortebewijs_is_ok_met_melding(self):
        doel = Path(self._tmp.name) / "leeg"
        doel.mkdir()
        code, uit, _ = self.roep("status", {"doel": str(doel)})
        self.assertEqual(code, 0)
        self.assertTrue(uit["ok"])
        self.assertIn("geen geboortebewijs", uit["data"]["melding"].lower())

    def test_corrupt_logboek_is_nette_fout_zonder_traceback(self):
        doel = self._boom("kapot", corrupt_logboek=True)
        code, uit, stderr = self.roep("status", {"doel": str(doel)})
        self.assertEqual(code, 1)
        self.assertFalse(uit["ok"])
        self.assertIn("corrupt", uit["fout"].lower())
        self.assertIn("adapter:", stderr)                     # mens-leesbaar naar stderr
        self.assertNotIn("Traceback", stderr + json.dumps(uit))

    def test_stdout_is_altijd_geldig_json(self):
        doel = self._boom("boom")
        for commando, invoer in (("status", {"doel": str(doel)}),
                                 ("status", {"doel": str(Path(self._tmp.name) / "niet-een-boom")}),
                                 ("niet-een-commando", {})):
            code, uit, _ = self.roep(commando, invoer)
            self.assertIsInstance(uit, dict, f"stdout geen JSON bij {commando}: {uit}")
            self.assertIn("ok", uit)


class TestProfielen(AdapterBasis):
    def test_profielen_levert_bewezen_profielen(self):
        code, uit, _ = self.roep("profielen", {})
        self.assertEqual(code, 0)
        self.assertTrue(uit["ok"])
        namen = [p["naam"] for p in uit["data"]["profielen"]]
        self.assertIn("tweede-brein", namen)
        self.assertNotIn("autonome-fabriek", namen)           # in-ontwikkeling blijft weg

    def test_profielen_levert_brein_opties_gemarkeerd(self):
        from kern.growkit_oerwoud import sla_brein_pad
        brein = Path(self._tmp.name) / "brein"
        (brein / "projecten" / "logboeken").mkdir(parents=True)
        sla_brein_pad(brein)
        code, uit, _ = self.roep("profielen", {})
        opties = uit["data"]["brein_opties"]
        self.assertIn({"naam": "logboeken", "bron": "uit je brein"}, opties)


class TestContract(AdapterBasis):
    def test_onbekend_commando_is_nette_fout_met_lijst(self):
        code, uit, _ = self.roep("niet-een-commando", {})
        self.assertEqual(code, 1)
        self.assertFalse(uit["ok"])
        self.assertIn("onbekend", uit["fout"].lower())
        self.assertIn("status", uit["fout"])

    def test_geen_commando_is_nette_fout(self):
        resultaat = subprocess.run([sys.executable, str(ADAPTER)],
                                   capture_output=True, text=True,
                                   env={**os.environ}, cwd=str(REPO), timeout=60)
        self.assertEqual(resultaat.returncode, 1)
        uit = json.loads(resultaat.stdout)
        self.assertFalse(uit["ok"])
        self.assertIn("geen commando", uit["fout"].lower())


if __name__ == "__main__":
    unittest.main()
