"""Adapter-plant (fase 6, taak 2): concept eerst, uitvoering mét bevestiging.

Regels:
- Zonder bevestiging: alleen het poort-concept — niets uitgevoerd.
- Met bevestiging: motor-run; per stap {id, status, bewijs}; faal → exit 2
  met stappen-overzicht.
- Brein: "auto" werkt direct bij bekend brein; onbekend brein → vragen-
  respons (niets uitgevoerd of geregistreerd); "pad" + brein_pad expliciet;
  "geen" registreert nooit. Onbereikbaar brein → nette fout (mens).
- Beslissing 7: een profiel dat de mijlpaal-drempel raakt wordt netjes
  geweigerd — ook mét bevestiging (fase 6.1).
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


class PlantBasis(unittest.TestCase):
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

    def roep(self, invoer: dict) -> tuple[int, dict, str]:
        resultaat = subprocess.run(
            [sys.executable, str(ADAPTER), "plant"],
            input=json.dumps(invoer), capture_output=True, text=True,
            env={**os.environ}, cwd=str(REPO), timeout=120)
        try:
            uit = json.loads(resultaat.stdout)
        except json.JSONDecodeError:
            uit = {"_rauw": resultaat.stdout}
        return resultaat.returncode, uit, resultaat.stderr

    def _doel(self, naam: str = "boom") -> Path:
        return Path(self._tmp.name) / naam

    def _brein(self, naam: str = "brein") -> Path:
        brein = Path(self._tmp.name) / naam
        brein.mkdir(parents=True)
        (brein / "geboortebewijs.json").write_text(json.dumps({
            "boom_id": str(uuid.uuid4()), "profiel": "tweede-brein", "machine": "mac",
            "locatie": str(brein.resolve()),
            "geplant_op": "2026-09-03T20:00:00+00:00"}), encoding="utf-8")
        return brein


class TestConceptModus(PlantBasis):
    def test_concept_voert_niets_uit(self):
        doel = self._doel()
        code, uit, _ = self.roep({"profiel": "tweede-brein", "doel": str(doel)})
        self.assertEqual(code, 0)
        self.assertTrue(uit["ok"])
        self.assertTrue(uit["data"]["bevestiging_vereist"])
        self.assertFalse(doel.exists())                    # niets geplant

    def test_leeg_doel_is_nette_adapter_weigering(self):
        """Het adapter-contract weigert eerst; de poort-tekst hoort bij de
        interactieve flow — hier is de veldcheck de poort."""
        code, uit, _ = self.roep({"profiel": "tweede-brein", "doel": ""})
        self.assertEqual(code, 1)
        self.assertFalse(uit["ok"])
        self.assertIn("doel", uit["fout"].lower())

    def test_onbekend_profiel_is_nette_fout(self):
        code, uit, _ = self.roep({"profiel": "bestaat-niet", "doel": str(self._doel())})
        self.assertEqual(code, 1)
        self.assertIn("onbekend profiel", uit["fout"].lower())


class TestBevestigdePlant(PlantBasis):
    def test_plant_met_brein_geen_registreert_niet(self):
        doel = self._doel()
        code, uit, _ = self.roep({"profiel": "tweede-brein", "doel": str(doel),
                                  "bevestig": True, "brein": "geen"})
        self.assertEqual(code, 0, uit)
        self.assertTrue(uit["ok"])
        stappen = uit["data"]["stappen"]
        self.assertEqual(len(stappen), 8)
        self.assertEqual(len([s for s in stappen if s["status"] == "geslaagd"]), 7)
        self.assertIn("wacht_op_mens", [s["status"] for s in stappen])
        self.assertEqual(uit["data"]["registratie"], "geen")
        self.assertFalse((self.home / "oerwoud.json").exists())
        bewijs = json.loads((doel / "geboortebewijs.json").read_text(encoding="utf-8"))
        self.assertNotIn("{{", json.dumps(bewijs))          # volgemaakt

    def test_brein_auto_bekend_registreert_zonder_vraag(self):
        brein = self._brein()
        from kern.growkit_oerwoud import sla_brein_pad
        sla_brein_pad(brein)
        doel = self._doel()
        code, uit, _ = self.roep({"profiel": "tweede-brein", "doel": str(doel),
                                  "bevestig": True, "brein": "auto"})
        self.assertEqual(code, 0, uit)
        self.assertEqual(uit["data"]["registratie"], "geregistreerd")
        register = json.loads((brein / "register" / "bomen.json").read_text(encoding="utf-8"))
        self.assertEqual(len(register), 1)

    def test_brein_pad_expliciet_registreert_en_state_bijwerkt(self):
        brein = self._brein()
        doel = self._doel()
        code, uit, _ = self.roep({"profiel": "tweede-brein", "doel": str(doel),
                                  "bevestig": True, "brein": "pad",
                                  "brein_pad": str(brein)})
        self.assertEqual(code, 0, uit)
        register = json.loads((brein / "register" / "bomen.json").read_text(encoding="utf-8"))
        self.assertEqual(len(register), 1)
        staat = json.loads((self.home / "oerwoud.json").read_text(encoding="utf-8"))
        self.assertEqual(Path(staat["brein_pad"]), brein.resolve())

    def test_brein_auto_onbekend_geeft_vragen_respons_niets_uitgevoerd(self):
        """Audit-punt 3: de stateless adapter stelt de brein-vraag als respons —
        en voert en registreert niets."""
        doel = self._doel()
        code, uit, _ = self.roep({"profiel": "tweede-brein", "doel": str(doel),
                                  "bevestig": True, "brein": "auto"})
        self.assertEqual(code, 0)
        self.assertIn("vragen", uit)
        self.assertIn("brein", uit["vragen"][0]["vraag"])
        self.assertFalse(doel.exists())                    # niets uitgevoerd
        self.assertFalse((self.home / "oerwoud.json").exists())  # niets opgeslagen

    def test_brein_onbereikbaar_is_nette_fout(self):
        verdwenen = Path(self._tmp.name) / "verdwenen"
        verdwenen.mkdir()
        from kern.growkit_oerwoud import sla_brein_pad
        sla_brein_pad(verdwenen)
        verdwenen.rmdir()
        doel = self._doel()
        code, uit, _ = self.roep({"profiel": "tweede-brein", "doel": str(doel),
                                  "bevestig": True, "brein": "auto"})
        self.assertEqual(code, 1)
        self.assertIn("niet bereikbaar", uit["fout"])
        self.assertFalse(doel.exists())                    # niets uitgevoerd


class TestFaalEnMijlpaal(PlantBasis):
    """In-process tests met een geïnjecteerd profiel (faal en mijlpaal)."""

    def _verwerk(self, profiel: dict, **extra) -> dict:
        import adapter
        doel = self._doel("inproc")
        invoer = {"profiel": profiel["profiel"], "doel": str(doel),
                  "bevestig": True, "brein": "geen", **extra}
        with mock.patch.object(adapter, "_laad_profiel", return_value=profiel), \
                contextlib.redirect_stdout(io.StringIO()):
            return adapter.cmd_plant(invoer)

    def test_faal_contract_geeft_stappen_overzicht(self):
        faal_profiel = {
            "profiel": "faal-boom",
            "stappen": [{
                "id": "stap-001", "commando": "false", "verwacht": "faalt",
                "bewijs": {"type": "shell_check", "commando": "false", "verwacht_substr": "OK"},
                "bij_falen": {"alternatief_commando": "false", "anders": "roep_mens"},
                "idempotent": True,
            }],
        }
        with self.assertRaises(adapter_adapter_faal()) as ctx:
            self._verwerk(faal_profiel)
        self.assertEqual(len(ctx.exception.stappen), 1)
        self.assertEqual(ctx.exception.stappen[0]["status"], "gefaald")

    def test_mijlpaal_profiel_wordt_net_geweigerd_ook_met_bevestiging(self):
        """Beslissing 7: nooit een stilzwijgende midden-staat — fase 6.1."""
        groot_profiel = {
            "profiel": "groot-boom",
            "stappen": [{"id": f"stap-{i:03d}", "idempotent": True} for i in range(1, 11)],
        }
        with self.assertRaises(adapter_adapter_fout()) as ctx:
            self._verwerk(groot_profiel)
        self.assertIn("mijlpaal", ctx.exception.args[0].lower())


def adapter_adapter_faal():
    import adapter
    return adapter.AdapterFaal


def adapter_adapter_fout():
    import adapter
    return adapter.AdapterFout


class TestExitMapping(PlantBasis):
    def test_faal_wordt_exit_2_met_json(self):
        import adapter
        faal_profiel = {
            "profiel": "faal-boom",
            "stappen": [{
                "id": "stap-001", "commando": "false", "verwacht": "faalt",
                "bewijs": {"type": "shell_check", "commando": "false", "verwacht_substr": "OK"},
                "bij_falen": {"alternatief_commando": "false", "anders": "roep_mens"},
                "idempotent": True,
            }],
        }
        uit_buf = io.StringIO()
        with mock.patch.object(adapter, "_laad_profiel", return_value=faal_profiel), \
                mock.patch.object(adapter.sys, "stdin", io.StringIO(json.dumps({
                    "profiel": "faal-boom", "doel": str(self._doel("inproc")),
                    "bevestig": True, "brein": "geen"}))), \
                contextlib.redirect_stdout(uit_buf):
            code = adapter.main(["plant"])
        self.assertEqual(code, 2)
        uit = json.loads(uit_buf.getvalue())
        self.assertFalse(uit["ok"])
        self.assertEqual(uit["stappen"][0]["status"], "gefaald")


if __name__ == "__main__":
    unittest.main()
