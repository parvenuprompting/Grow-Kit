"""De drie voorbeeldopdrachten (advies 5): lokaal, zonder VPS, met echt bewijs.

Wat hier wordt vastgehouden:
- er zijn precies drie voorbeelden, elk met een eigen plan én een mens-stap;
- geen enkel voorbeeldcommando raakt een VPS of internet;
- elk voorbeeld draait echt van concept → bevestiging → uitvoering → bewijs → oordeel,
  en levert de bestanden op die het belooft.
"""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from kern import growkit_opdrachten as op
from kern import growkit_voorbeelden as vb
from kern.growkit_bewijs import BEWIJS_TYPES
from kern.growkit_motor import vervang_growkit_pad
from seed import laad_profielen

REPO = Path(__file__).resolve().parents[1]
VERWACHT = ["documentenoverzicht", "projectcontrole", "terugkerend-rapport"]


def profiel_van(naam: str) -> dict:
    return next(p for p in laad_profielen() if p["profiel"] == naam)


class VoorbeeldenContract(unittest.TestCase):
    def test_precies_drie_voorbeelden_met_plan_en_mensstap(self):
        voorbeelden = vb.voorbeelden()
        self.assertEqual([v["id"] for v in voorbeelden], VERWACHT)
        for v in voorbeelden:
            self.assertTrue(v["titel"], v["id"])
            self.assertTrue(v["uitleg"], v["id"])
            self.assertTrue(v["criteria"], v["id"])
            self.assertGreaterEqual(v["stappen"], 3, v["id"])
            self.assertGreaterEqual(v["mens_stappen"], 1, v["id"])

    def test_geen_enkel_voorbeeld_raakt_een_vps_of_internet(self):
        for profiel in vb.voorbeeld_profielen():
            self.assertEqual(vb.externe_aanroepen(profiel), [], profiel["profiel"])

    def test_elk_bewijs_is_een_bekend_type(self):
        for profiel in vb.voorbeeld_profielen():
            for stap in profiel["stappen"]:
                if stap.get("mens_nodig"):
                    continue
                self.assertIn(stap["bewijs"]["type"], BEWIJS_TYPES,
                              f"{profiel['profiel']}/{stap['id']}")

    def test_voorbeelden_staan_niet_in_de_bewezen_profielenlijst(self):
        """Een voorbeeld is geen bewezen vorm: de picker blijft eerlijk."""
        from seed import laad_profielen as laad
        self.assertEqual([p["profiel"] for p in laad() if p.get("status") == "voorbeeld"],
                         VERWACHT)


class VoorbeeldenUitvoering(unittest.TestCase):
    """Elk voorbeeld draait echt door de kern, in een eigen tijdelijke map."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        patch.object(op, "_root", return_value=Path(self.tmp.name)).start()
        self.addCleanup(patch.stopall)

    def _draai(self, naam: str) -> tuple[dict, Path]:
        profiel = vervang_growkit_pad(profiel_van(naam), REPO)
        criteria = profiel["voorbeeld"]["criteria"]
        dossier = op.nieuw(profiel["voorbeeld"]["titel"], criteria, profiel,
                           REPO / "profielen" / naam / "sjablonen")
        with self.assertRaises(ValueError):
            op.uitvoeren(dossier["id"], dossier["plan_hash"])          # zonder bevestiging
        dossier = op.uitvoeren(dossier["id"], dossier["plan_hash"], True)
        return dossier, Path(dossier["doel"])

    def test_elk_voorbeeld_levert_bestand_bewijs_en_mensmoment(self):
        verwachte_bestanden = {
            "documentenoverzicht": ["overzicht/overzicht.md", "overzicht/markdown-aantal.txt",
                                    "overzicht/markdown-lijst.txt"],
            "projectcontrole": ["controle/controle.md", "controle/kernbestanden.txt",
                                "controle/basis.txt"],
            "terugkerend-rapport": ["rapport/rapport.md", "rapport/datum.txt",
                                    "rapport/scriptbestanden.txt"],
        }
        for naam in VERWACHT:
            dossier, doel = self._draai(naam)
            self.assertEqual(dossier["status"], "wacht_op_mens", naam)
            self.assertTrue(dossier["rapport"]["technisch_gecontroleerd"], naam)
            self.assertFalse(dossier["rapport"]["mens_goedgekeurd"], naam)
            machine = [s for s in dossier["rapport"]["stappen"]
                       if s.get("controle") != "mens_verificatie"]
            self.assertTrue(machine, naam)
            self.assertTrue(all(s["technisch"] == "geslaagd" for s in machine),
                            f"{naam}: {machine}")
            for bestand in verwachte_bestanden[naam]:
                self.assertTrue((doel / bestand).exists(), f"{naam}: {bestand} ontbreekt")
            # en dan beslist de mens — geen automatische goedkeuring
            dossier = op.beoordeel(dossier["id"], True, "Nagekeken en akkoord")
            self.assertEqual(dossier["status"], "goedgekeurd", naam)
            # het eindresultaat is vastgelegd als acceptatie (apart van stap-bewijs);
            # de stap-voor-stap 'mens'-kolom blijft bewust 'niet_goedgekeurd' voor
            # machine-stappen — dat is precies het onderscheid van advies 3.
            logboek = json.loads((doel / "logboek.json").read_text(encoding="utf-8"))
            self.assertIn("goedgekeurd",
                          [e.get("status") for e in logboek if e.get("type") == "acceptatie"], naam)

    def test_afwijzen_geeft_geen_goedkeuring(self):
        """Afwijzen bij het mens-moment zet de stap op herziening, niet op akkoord."""
        dossier, doel = self._draai("projectcontrole")
        dossier = op.beoordeel(dossier["id"], False, "Het rapport mist de bronvermelding")
        self.assertEqual(dossier["status"], "gepauzeerd")
        self.assertFalse(dossier["rapport"]["mens_goedgekeurd"])
        logboek = json.loads((doel / "logboek.json").read_text(encoding="utf-8"))
        self.assertIn("herziening_nodig", [e.get("status") for e in logboek])


class VoorbeeldenViaAdapter(unittest.TestCase):
    """De app haalt de voorbeelden op via de adapter — geen tweede lijst in Swift."""

    def test_adapteractie_voorbeelden_geeft_de_drie_met_plan(self):
        import adapter

        uit = adapter.cmd_opdrachten({"actie": "voorbeelden"})
        self.assertTrue(uit["ok"])
        voorbeelden = uit["data"]["voorbeelden"]
        self.assertEqual([v["id"] for v in voorbeelden], VERWACHT)
        for v in voorbeelden:
            self.assertTrue(v["titel"] and v["criteria"], v["id"])
            # het profiel dat de app straks aan 'nieuw' meegeeft, moet echt bestaan
            self.assertEqual(profiel_van(v["profiel"])["profiel"], v["profiel"])

    def test_onbekende_actie_blijft_een_nette_fout(self):
        import adapter

        with self.assertRaises(adapter.AdapterFout):
            adapter.cmd_opdrachten({"actie": "bestaat-niet"})
