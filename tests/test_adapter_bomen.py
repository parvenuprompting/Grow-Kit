"""Boom-kiezer (Slice 1): nieuw adapter-commando `bomen`.

Contract (Slice 1 uit docs/ROADMAP-SLICES.md):
- `bomen` neemt optioneel `register_pad` (pad naar bomen.json van het brein).
  Zonder register_pad: de per-machine oerwoud-staat raadplegen; geen bekend
  brein → ok met een lege lijst + melding (de app toont 'geen brein gekoppeld').
- Geen register-bestand → leeg oerwoud (zelfde als lees_register).
- Corrupt register → nette fouttekst (mens), nooit auto-repareren.
- Per boom: de recentste status uit het register (append-only, geen mutatie):
  {"boom_id", "profiel", "machine", "locatie", "geplant_op", "status",
   "status_tijdstip", "is_brein"}.
- Deregistreerde bomen worden wél getoond met status 'deregistratie' — de
  app mag ze zien, maar labelt ze als inactief.
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

_BREIN_BEWIJS = {
    "boom_id": "brein-11111111",
    "profiel": "tweede-brein",
    "machine": "breinmachine",
    "locatie": "/tmp/brein",
    "geplant_op": "2026-09-01T09:00:00+00:00",
}


class BomenBasis(unittest.TestCase):
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

    def _brein(self, naam: str = "brein") -> Path:
        brein = Path(self._tmp.name) / naam
        brein.mkdir(parents=True)
        (brein / "geboortebewijs.json").write_text(
            json.dumps(_BREIN_BEWIJS), encoding="utf-8")
        return brein

    def _register(self, brein: Path) -> Path:
        return brein / "register" / "bomen.json"

    def _boom_bewijs(self, doel: Path, boom_id: str = "boom-22222222",
                     locatie: str | None = None) -> Path:
        """Schrijf een geldig geboortebewijs en een logboek, zoals fase 5
        dat na de plant achterlaat."""
        doel.mkdir(parents=True, exist_ok=True)
        bewijs = {
            "boom_id": boom_id,
            "profiel": "dev-werkplaats",
            "machine": "testmachine",
            "locatie": locatie or str(doel),
            "geplant_op": "2026-09-03T10:00:00+00:00",
        }
        (doel / "geboortebewijs.json").write_text(json.dumps(bewijs), encoding="utf-8")
        (doel / "logboek.json").write_text(
            json.dumps([{"tijdstip": "2026-09-03T10:00:00+00:00", "type": "geboorte",
                         "tekst": "boom geplant"}]), encoding="utf-8")
        return doel / "geboortebewijs.json"


class BomenLeegEnFout(BomenBasis):
    def test_geen_brein_bekend(self):
        """Geen oerwoud-staat → ok, lege lijst + melding."""
        code, uit, _ = self.roep("bomen", {})
        self.assertEqual(code, 0)
        self.assertTrue(uit["ok"])
        self.assertEqual(uit["data"]["bomen"], [])
        self.assertIn("melding", uit["data"])

    def test_bekend_brein_zonder_register(self):
        """Bekend brein, maar nog geen bomen.json → leeg oerwoud."""
        self._brein()
        from kern import growkit_oerwoud
        growkit_oerwoud.sla_brein_pad(Path(self._tmp.name) / "brein")
        code, uit, _ = self.roep("bomen", {})
        self.assertEqual(code, 0)
        self.assertTrue(uit["ok"])
        self.assertEqual(uit["data"]["bomen"], [])

    def test_corrupt_register_nette_fout(self):
        brein = self._brein()
        from kern import growkit_oerwoud
        growkit_oerwoud.sla_brein_pad(brein)
        reg = self._register(brein)
        reg.parent.mkdir(parents=True, exist_ok=True)
        reg.write_text("{kapot", encoding="utf-8")
        code, uit, _ = self.roep("bomen", {})
        self.assertEqual(code, 1)
        self.assertFalse(uit["ok"])
        self.assertIn("corrupt", uit["fout"])

    def test_onbereikbaar_brein_nette_fout(self):
        """Staat wijst naar een verdwenen brein → nette fout, geen lege lijst."""
        from kern import growkit_oerwoud
        growkit_oerwoud.sla_brein_pad(Path(self._tmp.name) / "weg")
        code, uit, _ = self.roep("bomen", {})
        self.assertEqual(code, 1)
        self.assertFalse(uit["ok"])


class BomenLijst(BomenBasis):
    def test_expliciet_register_pad(self):
        """Met register_pad: bomen uit het register, recentste status per boom."""
        brein = self._brein()
        doel = Path(self._tmp.name) / "boom-a"
        bewijs = self._boom_bewijs(doel)
        from kern import growkit_oerwoud
        growkit_oerwoud.meld_geboorte(self._register(brein), bewijs, is_brein=False)
        code, uit, _ = self.roep("bomen", {"register_pad": str(self._register(brein))})
        self.assertEqual(code, 0)
        bomen = uit["data"]["bomen"]
        self.assertEqual(len(bomen), 1)
        boom = bomen[0]
        self.assertEqual(boom["boom_id"], "boom-22222222")
        self.assertEqual(boom["profiel"], "dev-werkplaats")
        self.assertEqual(boom["status"], "geboorte")
        self.assertEqual(boom["machine"], "testmachine")
        self.assertNotIn("is_brein", boom)

    def test_meerdere_bomen_en_brein_vlag(self):
        brein = self._brein()
        from kern import growkit_oerwoud
        growkit_oerwoud.meld_geboorte(self._register(brein),
                                      brein / "geboortebewijs.json", is_brein=True)
        bewijs_b = self._boom_bewijs(Path(self._tmp.name) / "boom-b", boom_id="boom-33333333")
        growkit_oerwoud.meld_geboorte(self._register(brein), bewijs_b)
        code, uit, _ = self.roep("bomen", {"register_pad": str(self._register(brein))})
        self.assertEqual(code, 0)
        bomen = {b["boom_id"]: b for b in uit["data"]["bomen"]}
        self.assertEqual(len(bomen), 2)
        self.assertTrue(bomen["brein-11111111"]["is_brein"])
        self.assertEqual(bomen["boom-33333333"]["status"], "geboorte")

    def test_deregistratie_tonen_als_inactief(self):
        brein = self._brein()
        from kern import growkit_oerwoud
        bewijs = self._boom_bewijs(Path(self._tmp.name) / "boom-c")
        growkit_oerwoud.meld_geboorte(self._register(brein), bewijs)
        growkit_oerwoud.meld_deregistratie(self._register(brein), "boom-22222222", "niet meer nodig")
        code, uit, _ = self.roep("bomen", {"register_pad": str(self._register(brein))})
        self.assertEqual(code, 0)
        boom = uit["data"]["bomen"][0]
        self.assertEqual(boom["status"], "deregistratie")
        self.assertIn("inactief", boom)

    def test_register_via_bekend_brein(self):
        """Zonder register_pad, met bekend brein in de oerwoud-staat."""
        brein = self._brein()
        from kern import growkit_oerwoud
        growkit_oerwoud.sla_brein_pad(brein)
        bewijs = self._boom_bewijs(Path(self._tmp.name) / "boom-d")
        from kern import growkit_oerwoud
        growkit_oerwoud.meld_geboorte(self._register(brein), bewijs)
        code, uit, _ = self.roep("bomen", {})
        self.assertEqual(code, 0)
        self.assertEqual(len(uit["data"]["bomen"]), 1)

    def test_status_tijdstip_aanwezig(self):
        brein = self._brein()
        bewijs = self._boom_bewijs(Path(self._tmp.name) / "boom-e")
        from kern import growkit_oerwoud
        growkit_oerwoud.meld_geboorte(self._register(brein), bewijs)
        _, uit, _ = self.roep("bomen", {"register_pad": str(self._register(brein))})
        boom = uit["data"]["bomen"][0]
        self.assertIn("status_tijdstip", boom)
        self.assertTrue(boom["status_tijdstip"])


if __name__ == "__main__":
    unittest.main()
