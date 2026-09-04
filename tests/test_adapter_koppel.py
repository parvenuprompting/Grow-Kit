"""Slice 5 — breinkoppeling: meerdere bomen registreren bij één gedeeld brein
vanuit de app, met de harde drift-guard (docs/ROADMAP-SLICES.md, §13).

Nieuwe adapter-commando's:
- `koppel`: registratie van een boom bij het brein via het geboortebewijs.
    {"doel": "<boom-pad>", "brein_pad": "<brein-pad>" | afwezig = bekend brein}
  Regels (§13, overgenomen van de bestaande kern):
    - ongeldig of ontbrekend geboortebewijs → weigering, niets geregistreerd
    - boom staat al actief in het register → weigering (geen dubbele geboorte)
    - brein onbereikbaar → nette fout (mens), geen fallback naar 'nieuw brein'
  Na succes: de oerwoud-staat wordt weggeschreven (sla_brein_pad) zodat de
  app daarna bomen/inbox/status uit hetzelfde brein leest.

- `driftguard`: het drift-guard-rapport van een brein — wat reist er wél en
    niet tussen bomen en brein. Puur lezend, voor de app als uitleg/audit:
    {"reist_mee": [...], "blijft_lokaal": [...], "bomen": <aantal>,
     "brein_pad": str}
  De guard zelf is hard in de code (stuur_voorstellen reist alleen VOORSTEL-
  bestanden; omgevingsstaat blijft per boom); dit commando maakt de regels
  zichtbaar zonder ze te veranderen.

Reeds bewezen gedrag dat hier NIET verandert (alleen her-bewezen via de
adapter): append-only register, geen overschrijven, drift-guard op doorstroom.
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


class KoppelBasis(unittest.TestCase):
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
        brein.mkdir(parents=True, exist_ok=True)
        (brein / "geboortebewijs.json").write_text(json.dumps({
            "boom_id": f"brein-{naam}", "profiel": "tweede-brein",
            "machine": "test", "locatie": str(brein),
            "geplant_op": "2026-09-01T09:00:00+00:00"}), encoding="utf-8")
        return brein

    def _boom(self, naam: str = "boom-a") -> Path:
        doel = Path(self._tmp.name) / naam
        doel.mkdir(parents=True, exist_ok=True)
        (doel / "geboortebewijs.json").write_text(json.dumps({
            "boom_id": f"boom-{naam}", "profiel": "dev-werkplaats",
            "machine": "test", "locatie": str(doel),
            "geplant_op": "2026-09-04T09:00:00+00:00"}), encoding="utf-8")
        (doel / "logboek.json").write_text(json.dumps([
            {"tijdstip": "2026-09-04T09:00:00+00:00", "type": "geboorte",
             "tekst": "geplant"}]), encoding="utf-8")
        return doel

    def _register(self, brein: Path) -> Path:
        return brein / "register" / "bomen.json"


class Koppel(KoppelBasis):
    def test_koppeling_registreert_en_slaat_staat_op(self):
        brein = self._brein()
        boom = self._boom()
        code, uit, _ = self.roep("koppel", {"doel": str(boom), "brein_pad": str(brein)})
        self.assertEqual(code, 0)
        # geregistreerd in het register
        register = json.loads(self._register(brein).read_text(encoding="utf-8"))
        self.assertEqual(len([e for e in register if e.get("boom_id") == "boom-boom-a"]), 1)
        # oerwoud-staat weggeschreven: daarna leest `bomen` dit brein
        code, uit, _ = self.roep("bomen", {})
        self.assertEqual(code, 0)
        self.assertEqual(len(uit["data"]["bomen"]), 1)

    def test_dubbele_koppeling_geweigerd(self):
        brein = self._brein()
        boom = self._boom()
        self.roep("koppel", {"doel": str(boom), "brein_pad": str(brein)})
        n_voor = len(json.loads(self._register(brein).read_text(encoding="utf-8")))
        code, uit, _ = self.roep("koppel", {"doel": str(boom), "brein_pad": str(brein)})
        self.assertEqual(code, 1)
        self.assertFalse(uit["ok"])
        n_na = len(json.loads(self._register(brein).read_text(encoding="utf-8")))
        self.assertEqual(n_voor, n_na)          # append-only: niets bijgeschreven

    def test_ongeldig_bewijs_geweigerd(self):
        brein = self._brein()
        boom = self._boom()
        (boom / "geboortebewijs.json").write_text("{}", encoding="utf-8")  # missende velden
        code, uit, _ = self.roep("koppel", {"doel": str(boom), "brein_pad": str(brein)})
        self.assertEqual(code, 1)
        self.assertFalse(self._register(brein).exists())

    def test_onbereikbaar_brein_nette_fout_geen_fallback(self):
        boom = self._boom()
        code, uit, _ = self.roep("koppel", {"doel": str(boom),
                                            "brein_pad": str(Path(self._tmp.name) / "weg")})
        self.assertEqual(code, 1)
        self.assertFalse(uit["ok"])

    def test_koppeling_zonder_expliciet_brein_gebruikt_bekend_brein(self):
        brein = self._brein()
        from kern import growkit_oerwoud
        growkit_oerwoud.sla_brein_pad(brein)
        boom = self._boom()
        code, uit, _ = self.roep("koppel", {"doel": str(boom)})
        self.assertEqual(code, 0)
        self.assertTrue(self._register(brein).exists())


class DriftGuard(KoppelBasis):
    def test_driftguard_rapporteert_regels(self):
        brein = self._brein()
        code, uit, _ = self.roep("driftguard", {"brein_pad": str(brein)})
        self.assertEqual(code, 0)
        data = uit["data"]
        # wat reist mee: alleen gemarkeerde VOORSTELLEN
        self.assertTrue(any("VOORSTEL" in item for item in data["reist_mee"]))
        # wat blijft lokaal: omgevingsstaat
        self.assertTrue(any("pad" in item.lower() or "sleutel" in item.lower() or "poort" in item.lower()
                            for item in data["blijft_lokaal"]))
        self.assertEqual(data["brein_pad"], str(brein))

    def test_driftguard_telt_gekoppelde_bomen(self):
        brein = self._brein()
        boom = self._boom()
        self.roep("koppel", {"doel": str(boom), "brein_pad": str(brein)})
        code, uit, _ = self.roep("driftguard", {"brein_pad": str(brein)})
        self.assertEqual(uit["data"]["bomen"], 1)

    def test_driftguard_zonder_brein_nette_fout(self):
        code, uit, _ = self.roep("driftguard", {})
        self.assertEqual(code, 1)
        self.assertFalse(uit["ok"])


class DoorstroomNaKoppeling(KoppelBasis):
    """De complete lus: koppel → VOORSTEL sturen → curate. Eén brein, meerdere
    bomen, drift-guard actief — precies de route die de app straks bedient."""

    def test_volle_lus_van_boom_naar_brein_inbox(self):
        brein = self._brein()
        boom = self._boom()
        self.roep("koppel", {"doel": str(boom), "brein_pad": str(brein)})
        (brein / "inbox").mkdir(exist_ok=True)   # §13: brein-inbox is vereiste
        # VOORSTEL in de boom-inbox; drift-guard: alleen dit reist
        (boom / "inbox").mkdir()
        (boom / "inbox" / "VOORSTEL-test-1.md").write_text("inzicht", encoding="utf-8")
        (boom / "geheim.txt").write_text("blijft thuis", encoding="utf-8")
        code, uit, _ = self.roep("stuur", {"doel": str(boom), "brein_pad": str(brein)})
        self.assertEqual(code, 0)
        # aangekomen in de brein-inbox met boom-id-prefix
        aangekomen = list((brein / "inbox").glob("VOORSTEL-boom-boom-a-*"))
        self.assertEqual(len(aangekomen), 1)
        # drift-guard: geheim.txt reisde NIET mee
        self.assertFalse((brein / "inbox" / "geheim.txt").exists())
        self.assertFalse((brein / "geheim.txt").exists())
        # en de boom-inbox heeft zijn kopie nog (niets verplaatst uit de boom)


if __name__ == "__main__":
    unittest.main()
