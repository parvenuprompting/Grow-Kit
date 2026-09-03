"""Fase 6.1 — adapter: hervat, taak en het mijlpaal-protocol.

Regels:
- `hervat` zonder bevestiging: reconstructie-overzicht (beslissingen per stap
  + herstartpunt + restdraai); mét bevestiging: restdraai via de motor.
  Profiel komt uit het geboortebewijs, of expliciet als invoer-veld.
- `taak` zonder bevestiging: lijst mét geldigheid-vlag; mét bevestiging +
  taak_id: poort → motor → gebeurtenissen (via de kern — één bron).
- Mijlpaal (beslissing 7, fase 6.1): bevestigde plant van een mijlpaal-profiel
  retourneert het §11.4-blok en voert NIETS uit; pas met
  `mijlpaal_bevestigd: true` draait de motor — stateless, twee calls.
"""
import contextlib
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
import uuid
from pathlib import Path
from unittest import mock

REPO = Path(__file__).parent.parent
ADAPTER = REPO / "adapter.py"


class Basis(unittest.TestCase):
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
            env={**os.environ}, cwd=str(REPO), timeout=120)
        try:
            uit = json.loads(resultaat.stdout)
        except json.JSONDecodeError:
            uit = {"_rauw": resultaat.stdout}
        return resultaat.returncode, uit, resultaat.stderr

    def _boom(self, naam: str = "boom", logboek: list | None = None) -> Path:
        doel = Path(self._tmp.name) / naam
        doel.mkdir(parents=True)
        (doel / "geboortebewijs.json").write_text(json.dumps({
            "boom_id": str(uuid.uuid4()), "profiel": "tweede-brein", "machine": "mac",
            "locatie": str(doel.resolve()),
            "geplant_op": "2026-09-04T00:00:00+00:00"}), encoding="utf-8")
        entries = logboek if logboek is not None else []
        (doel / "logboek.json").write_text(json.dumps(entries), encoding="utf-8")
        return doel


def _entry(stap: str, status: str) -> dict:
    return {"stap": stap, "status": status, "bewijs": "test",
            "tijdstip": "2026-09-04T00:00:00+00:00"}


class TestHervat(Basis):
    def test_lijst_zonder_bevestiging_wijzigt_niets(self):
        doel = self._boom(logboek=[_entry("stap-001", "geslaagd"),
                                   _entry("stap-003", "gefaald")])
        voor = (doel / "logboek.json").read_text(encoding="utf-8")
        code, uit, _ = self.roep("hervat", {"doel": str(doel)})
        self.assertEqual(code, 0)
        self.assertTrue(uit["data"]["bevestiging_vereist"])
        self.assertEqual(uit["data"]["restdraai"],
                         ["stap-002", "stap-003", "stap-004", "stap-005",
                          "stap-006", "stap-007", "stap-008"])
        self.assertEqual(uit["data"]["stappen"]["stap-001"]["beslissing"], "overslaan")
        self.assertEqual(uit["data"]["stappen"]["stap-003"]["beslissing"], "heraanbieden")
        self.assertEqual((doel / "logboek.json").read_text(encoding="utf-8"), voor)

    def test_bevestigde_restdraai_draait_de_rest(self):
        # eerst écht planten (bestanden + volwaardig geboortebewijs), daarna het
        # logboek terugbrengen naar een crash na stap-001
        doel = self._boom()
        code, uit, _ = self.roep("plant", {"profiel": "tweede-brein", "doel": str(doel),
                                           "bevestig": True, "brein": "geen"})
        self.assertEqual(code, 0, uit)
        entries = json.loads((doel / "logboek.json").read_text(encoding="utf-8"))
        (doel / "logboek.json").write_text(json.dumps(
            [e for e in entries if e["stap"] == "stap-001"]), encoding="utf-8")
        code, uit, _ = self.roep("hervat", {"doel": str(doel), "bevestig": True})
        self.assertEqual(code, 0, uit)
        stappen = uit["data"]["stappen"]
        self.assertEqual(len([s for s in stappen if s["id"] == "stap-001"]), 1)  # niet herdraaid
        self.assertIn("wacht_op_mens", [s["status"] for s in stappen])           # stap-008
        entries = json.loads((doel / "logboek.json").read_text(encoding="utf-8"))
        self.assertEqual(len([e for e in entries if e["stap"] == "stap-001"]), 1)

    def test_niets_te_hervatten(self):
        doel = self._boom(logboek=[_entry(f"stap-{i:03d}", "geslaagd") for i in range(1, 9)])
        code, uit, _ = self.roep("hervat", {"doel": str(doel), "bevestig": True})
        self.assertEqual(code, 0)
        self.assertIn("niets te hervatten", uit["data"]["melding"].lower())

    def test_zonder_geboortebewijs_is_nette_fout_met_profiel_uitweg(self):
        doel = Path(self._tmp.name) / "kaal"
        doel.mkdir()
        (doel / "logboek.json").write_text("[]", encoding="utf-8")
        code, uit, _ = self.roep("hervat", {"doel": str(doel)})
        self.assertEqual(code, 1)
        self.assertIn("geboortebewijs", uit["fout"].lower())
        code, uit, _ = self.roep("hervat", {"doel": str(doel), "profiel": "tweede-brein",
                                            "bevestig": True})
        self.assertEqual(code, 0)                            # expliciet profiel lost het op

    def test_corrupt_logboek_is_nette_fout(self):
        doel = self._boom()
        (doel / "logboek.json").write_text("{half", encoding="utf-8")
        code, uit, _ = self.roep("hervat", {"doel": str(doel)})
        self.assertEqual(code, 1)
        self.assertIn("corrupt", uit["fout"].lower())


class TestTaak(Basis):
    def setUp(self):
        super().setUp()
        self.doel = self._boom()
        self.takenlijst = self.doel / "takenlijst.json"
        self.takenlijst.write_text(json.dumps([
            {"id": "taak-001", "titel": "kweek", "commando": "echo KWEEK-OK",
             "bewijs": {"type": "shell_check", "commando": "echo KWEEK-OK",
                        "verwacht_substr": "KWEEK-OK"}},
            {"id": "taak-002", "titel": "zonder bewijs"},
        ]), encoding="utf-8")

    def test_lijst_toont_geldigheid_zonder_uit_te_voeren(self):
        code, uit, _ = self.roep("taak", {"doel": str(self.doel)})
        self.assertEqual(code, 0)
        taken = uit["data"]["taken"]
        geldig = {t["id"]: t["geldig"] for t in taken}
        self.assertEqual(geldig, {"taak-001": True, "taak-002": False})
        self.assertFalse((self.doel / "taken-logboek.json").exists())

    def test_bevestigde_uitvoering_van_een_geldige_taak(self):
        code, uit, _ = self.roep("taak", {"doel": str(self.doel), "bevestig": True,
                                          "taak_id": "taak-001"})
        self.assertEqual(code, 0, uit)
        self.assertEqual(uit["data"]["status"], "geslaagd")
        gebeurtenissen = json.loads((self.doel / "taken-logboek.json").read_text(encoding="utf-8"))
        self.assertEqual([e["status"] for e in gebeurtenissen], ["bezig", "geslaagd"])

    def test_ongeldige_taak_is_poort_weigering(self):
        code, uit, _ = self.roep("taak", {"doel": str(self.doel), "bevestig": True,
                                          "taak_id": "taak-002"})
        self.assertEqual(code, 1)
        self.assertIn("bewijs", uit["fout"].lower())
        gebeurtenissen = json.loads((self.doel / "taken-logboek.json").read_text(encoding="utf-8"))
        self.assertEqual(gebeurtenissen[-1]["status"], "geweigerd")

    def test_onbekende_taak_id_is_nette_fout(self):
        code, uit, _ = self.roep("taak", {"doel": str(self.doel), "bevestig": True,
                                          "taak_id": "bestaat-niet"})
        self.assertEqual(code, 1)
        self.assertIn("bestaat niet", uit["fout"].lower())


class TestMijlpaalProtocol(Basis):
    """Beslissing 7/7a: twee stateless calls — blok tonen, dan bevestigen."""

    def _groot_profiel(self):
        return {"profiel": "groot-boom",
                "stappen": [{"id": f"stap-{i:03d}", "idempotent": True,
                             "commando": f"echo OK-{i}",
                             "bewijs": {"type": "shell_check", "commando": f"echo OK-{i}",
                                        "verwacht_substr": f"OK-{i}"}}
                            for i in range(1, 11)]}

    def test_bevestigde_plant_wacht_op_mijlpaal_bevestiging(self):
        import adapter
        doel = Path(self._tmp.name) / "groot"
        invoer = {"profiel": "groot-boom", "doel": str(doel),
                  "bevestig": True, "brein": "geen"}
        with mock.patch.object(adapter, "_laad_profiel", return_value=self._groot_profiel()), \
                contextlib.redirect_stdout(io.StringIO()):
            uit = adapter.cmd_plant(invoer)
        self.assertEqual(uit["data"]["status"], "wacht_op_mijlpaal_bevestiging")
        self.assertIn("Wat ik begrepen heb", uit["data"]["mijlpaal_blok"])
        self.assertIn("Wat hierna komt", uit["data"]["mijlpaal_blok"])
        self.assertFalse(doel.exists())                       # niets uitgevoerd

    def test_met_mijlpaal_bevestiging_draait_de_motor(self):
        import adapter
        doel = Path(self._tmp.name) / "groot"
        invoer = {"profiel": "groot-boom", "doel": str(doel),
                  "bevestig": True, "brein": "geen", "mijlpaal_bevestigd": True}
        with mock.patch.object(adapter, "_laad_profiel", return_value=self._groot_profiel()), \
                contextlib.redirect_stdout(io.StringIO()):
            uit = adapter.cmd_plant(invoer)
        self.assertTrue(uit["ok"])
        self.assertEqual(len(uit["data"]["stappen"]), 10)     # 10 geslaagde stappen
        self.assertTrue((doel / "logboek.json").exists())     # de motor heeft gelopen


if __name__ == "__main__":
    unittest.main()
