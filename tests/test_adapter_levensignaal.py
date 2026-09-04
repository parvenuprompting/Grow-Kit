"""Slice 2 — live status per boom (docs/ROADMAP-SLICES.md).

Nieuw adapter-commando `levensignaal`: per boom de levende waarheid uit
groei/logboek.json — nooit zelf-rapportage van de agent of de loop.

Contract:
- Invoer: {"doel": "<boom-pad>"}.
- OK-data: {"levensignaal": {...}} met:
    {"boom_id": str|None,
     "taak_actief": bool,            # run bezig volgens het logboek
     "faalcontract": "groen"|"rood"|"gestopt"|"rust",
     "laatste_bewijs_tijdstip": str|None,
     "laatste_stap": {"stap","status","tijdstip"}|None,
     "laatste_mijlpaal_faal": {...}|None,
     "melding": str|None}
- Faalcontract-afleiding, puur uit logboek-entries (append-only):
    - laatste motor-stap heeft status 'gefaald' of 'onduidelijk' → "rood"
    - laatste taak-gebeurtenis heeft status 'gefaald'          → "rood"
    - een geslaagde/geratificeerde stap komt ná de faal        → "groen"
    - logboek leeg of alleen geboorte                          → "rust"
  "gestopt" wordt NIET uit het logboek afgeleid: een crash laat geen entry
  achter — dat ziet de app aan het ontbreken van een run-latch (zie onder).
- Run-latch (crash-detectie): de loop schrijft bij aanvang van een run een
  entry {"type": "run", "status": "gestart", "pid": ...} en bij normal
  einde {"type": "run", "status": "beeindigd"}. Lees de laatste run-entry:
    - "gestart" en het pid leeft niet meer → "gestopt" (crash/herstart nodig)
    - "gestart" en het pid leeft           → taak_actief = True
- Corrupt logboek → nette fout (mens), nooit auto-repareren.
- Geen logboek → ok met levensignaal in "rust" (lege boom, geen crash).
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


class LevensignaalBasis(unittest.TestCase):
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
            [sys.executable, str(ADAPTER), "levensignaal"],
            input=json.dumps(invoer), capture_output=True, text=True,
            env={**os.environ}, cwd=str(REPO), timeout=120)
        try:
            uit = json.loads(resultaat.stdout)
        except json.JSONDecodeError:
            uit = {"_rauw": resultaat.stdout}
        return resultaat.returncode, uit, resultaat.stderr

    def _boom(self, naam: str = "boom", entries: list[dict] | None = None) -> Path:
        doel = Path(self._tmp.name) / naam
        doel.mkdir(parents=True, exist_ok=True)
        (doel / "geboortebewijs.json").write_text(json.dumps({
            "boom_id": f"boom-{naam}", "profiel": "dev-werkplaats",
            "machine": "test", "locatie": str(doel),
            "geplant_op": "2026-09-04T09:00:00+00:00"}), encoding="utf-8")
        if entries is not None:
            (doel / "logboek.json").write_text(json.dumps(entries), encoding="utf-8")
        return doel

    def _sig(self, uit: dict) -> dict:
        return uit["data"]["levensignaal"]


class LevensignaalRust(LevensignaalBasis):
    def test_geen_logboek_is_rust(self):
        doel = self._boom(entries=None)
        code, uit, _ = self.roep({"doel": str(doel)})
        self.assertEqual(code, 0)
        sig = self._sig(uit)
        self.assertEqual(sig["faalcontract"], "rust")
        self.assertFalse(sig["taak_actief"])
        self.assertIsNone(sig["laatste_bewijs_tijdstip"])

    def test_alleen_geboorte_is_rust(self):
        doel = self._boom(entries=[{"tijdstip": "2026-09-04T09:00:00+00:00",
                                    "type": "geboorte", "tekst": "geplant"}])
        _, uit, _ = self.roep({"doel": str(doel)})
        sig = self._sig(uit)
        self.assertEqual(sig["faalcontract"], "rust")
        self.assertIsNone(sig["laatste_bewijs_tijdstip"])

    def test_corrupt_logboek_nette_fout(self):
        doel = self._boom()
        (doel / "logboek.json").write_text("{kapot", encoding="utf-8")
        code, uit, _ = self.roep({"doel": str(doel)})
        self.assertEqual(code, 1)
        self.assertFalse(uit["ok"])
        self.assertIn("corrupt", uit["fout"])

    def test_geen_doel_is_nette_fout(self):
        code, uit, _ = self.roep({"doel": str(Path(self._tmp.name) / "niet Bestaat")})
        self.assertEqual(code, 1)
        self.assertFalse(uit["ok"])


class LevensignaalFaalcontract(LevensignaalBasis):
    def test_faal_stap_is_rood(self):
        doel = self._boom(entries=[
            {"stap": "taak-001", "status": "geslaagd",
             "bewijs": "shell_check: zocht OK, kreeg OK", "tijdstip": "2026-09-04T09:05:00+00:00"},
            {"stap": "taak-002", "status": "gefaald",
             "bewijs": "shell_check: zocht OK, kreeg ''", "tijdstip": "2026-09-04T09:10:00+00:00"},
        ])
        _, uit, _ = self.roep({"doel": str(doel)})
        sig = self._sig(uit)
        self.assertEqual(sig["faalcontract"], "rood")
        self.assertEqual(sig["laatste_stap"]["stap"], "taak-002")
        self.assertEqual(sig["laatste_bewijs_tijdstip"], "2026-09-04T09:10:00+00:00")

    def test_tak_faal_is_rood(self):
        doel = self._boom(entries=[
            {"type": "taak", "taak": "t-1", "status": "gefaald",
             "bewijs": "geen bewijs", "tijdstip": "2026-09-04T09:10:00+00:00"},
        ])
        _, uit, _ = self.roep({"doel": str(doel)})
        self.assertEqual(self._sig(uit)["faalcontract"], "rood")

    def test_geslaagd_na_faal_is_groen(self):
        doel = self._boom(entries=[
            {"stap": "taak-001", "status": "gefaald",
             "bewijs": "kapot", "tijdstip": "2026-09-04T09:10:00+00:00"},
            {"stap": "taak-001", "status": "geslaagd",
             "bewijs": "hersteld", "tijdstip": "2026-09-04T09:20:00+00:00"},
        ])
        _, uit, _ = self.roep({"doel": str(doel)})
        sig = self._sig(uit)
        self.assertEqual(sig["faalcontract"], "groen")
        self.assertEqual(sig["laatste_stap"]["status"], "geslaagd")

    def test_mijlpaal_gaat_voor_laagste_recente_stap(self):
        """laatste_mijlpaal_faal blijft de laatste mijlpaal-óf faal tonen
        (één bron met status_data) — ook als er daarna nog stappen kwamen."""
        doel = self._boom(entries=[
            {"stap": "mijlpaal-start", "status": "mijlpaal",
             "bewijs": "drie taken bewezen", "tijdstip": "2026-09-04T09:00:00+00:00"},
            {"stap": "taak-009", "status": "geslaagd",
             "bewijs": "ok", "tijdstip": "2026-09-04T09:30:00+00:00"},
        ])
        _, uit, _ = self.roep({"doel": str(doel)})
        sig = self._sig(uit)
        self.assertEqual(sig["laatste_mijlpaal_faal"]["stap"], "mijlpaal-start")
        self.assertEqual(sig["faalcontract"], "groen")


class LevensignaalRunLatch(LevensignaalBasis):
    def test_run_gestart_pid_leeft_is_actief(self):
        doel = self._boom(entries=[
            {"type": "run", "status": "gestart", "pid": os.getpid(),
             "tijdstip": "2026-09-04T09:00:00+00:00"},
        ])
        _, uit, _ = self.roep({"doel": str(doel)})
        sig = self._sig(uit)
        self.assertTrue(sig["taak_actief"])

    def test_run_gestart_pid_dood_is_gestopt(self):
        """Crash-detectie: latch 'gestart' zonder levend pid → 'gestopt'."""
        doel = self._boom(entries=[
            {"type": "run", "status": "gestart", "pid": 2147483000,
             "tijdstip": "2026-09-04T09:00:00+00:00"},
            {"stap": "taak-001", "status": "geslaagd",
             "bewijs": "ok", "tijdstip": "2026-09-04T09:01:00+00:00"},
        ])
        _, uit, _ = self.roep({"doel": str(doel)})
        sig = self._sig(uit)
        self.assertEqual(sig["faalcontract"], "gestopt")
        self.assertFalse(sig["taak_actief"])

    def test_run_beeindigd_is_niet_actief(self):
        doel = self._boom(entries=[
            {"type": "run", "status": "gestart", "pid": os.getpid(),
             "tijdstip": "2026-09-04T09:00:00+00:00"},
            {"type": "run", "status": "beeindigd",
             "tijdstip": "2026-09-04T09:30:00+00:00"},
        ])
        _, uit, _ = self.roep({"doel": str(doel)})
        sig = self._sig(uit)
        self.assertFalse(sig["taak_actief"])
        self.assertEqual(sig["faalcontract"], "rust")

    def test_crash_na_faal_toont_gestopt(self):
        """'gestopt' wint van een oudere faal — de run staat stil, dat is het
        nieuws. De oude faal blijft zichtbaar in laatste_stap."""
        doel = self._boom(entries=[
            {"stap": "taak-002", "status": "gefaald",
             "bewijs": "kapot", "tijdstip": "2026-09-04T09:10:00+00:00"},
            {"type": "run", "status": "gestart", "pid": 2147483000,
             "tijdstip": "2026-09-04T09:20:00+00:00"},
        ])
        _, uit, _ = self.roep({"doel": str(doel)})
        sig = self._sig(uit)
        self.assertEqual(sig["faalcontract"], "gestopt")
        self.assertEqual(sig["laatste_stap"]["status"], "gefaald")


if __name__ == "__main__":
    unittest.main()
