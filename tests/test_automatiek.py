"""Testen voor de Automatiek-plannen-kern (kern/growkit_automatiek.py).

Inbouw van parvenuprompting/Automatiek (MIT) als GrowKit-kernmodule:
het zes-blokken-model letterlijk uit types.ts/plan.ts, met de
huisregels van GrowKit eromheen:
- een plan is concept tot het valide is (alle zes blokken gevuld);
- secrets-scanner geldt óók voor plannen (blok met een key wordt
  geweigerd — authenticatie hoort op de doelmachine);
- export naar markdown en JSON, import leest beide terug;
- append-only log per actie (huisregel van het huis).
"""
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from kern import growkit_automatiek as am

REPO = Path(__file__).resolve().parent.parent


def _vol_blokken():
    """Zes compleet gevulde blokken (het 'gelukkige pad')."""
    return {
        "doel_en_trigger": {
            "doel": "Elke ochtend een samenvatting van nieuwe Drive-bestanden in Telegram",
            "trigger": "dagelijks om 08:00",
            "trigger_type": "schema",
        },
        "bronnen": {
            "diensten": "Google Drive, Telegram bot",
            "data": "nieuwe bestanden sinds gisteren",
            "authenticatie": "op de doelmachine (service-account)",
        },
        "stappen": [
            {"nummer": 1, "omschrijving": "Zoek nieuwe bestanden",
             "invoer": "query Drive", "uitvoer": "lijst bestanden",
             "foutscenario": "geen verbinding → wacht 5 min, opnieuw"},
            {"nummer": 2, "omschrijving": "Vat samen en verstuur",
             "invoer": "lijst bestanden", "uitvoer": "Telegram-bericht",
             "foutscenario": "bot unreachable → log + stop"},
        ],
        "kwaliteit": {
            "verificatie": "testbericht arriveert in Telegram",
            "testaanpak": "eenmalig handmatig + logcheck na dag 1",
        },
        "uitvoering": {
            "omgeving": "VPS (KairOS)",
            "planning": "cron 0 8 * * *",
            "faalafhandeling": "3 pogingen, daarna melding aan de Baas",
        },
        "randvoorwaarden": {
            "privacy": "alleen bestandsnamen, geen inhoud",
            "randgevallen": "lege dag → geen bericht",
        },
    }


class TestModel(unittest.TestCase):
    def test_nieuw_plan_is_concept_met_zes_blokken(self):
        plan = am.nieuw_plan("Ochtendsamenvatting")
        self.assertEqual(plan["status"], "concept")
        self.assertEqual(plan["versie"], am.SCHEMA_VERSIE)
        for sleutel in ("doel_en_trigger", "bronnen", "stappen",
                        "kwaliteit", "uitvoering", "randvoorwaarden"):
            self.assertIn(sleutel, plan["blokken"])
        self.assertEqual(plan["blokken"]["stappen"], [])

    def test_trigger_typen(self):
        for tt in ("schema", "webhook", "handmatig", "event"):
            plan = am.nieuw_plan("x", trigger_type=tt)
            self.assertEqual(plan["blokken"]["doel_en_trigger"]["trigger_type"], tt)

    def test_onbekend_trigger_type_geweigerd(self):
        with self.assertRaises(ValueError):
            am.nieuw_plan("x", trigger_type="magisch")


class TestValidatie(unittest.TestCase):
    def test_leeg_concept_is_niet_geldig_klaar(self):
        plan = am.nieuw_plan("Alleen een titel")
        r = am.valideer_klaar(plan)
        self.assertFalse(r["geldig"])

    def test_vol_plan_is_geldig(self):
        plan = am.nieuw_plan("Ochtendsamenvatting")
        plan["blokken"] = _vol_blokken()
        r = am.valideer_klaar(plan)
        self.assertTrue(r["geldig"], r.get("fout"))

    def test_stap_zonder_foutscenario_is_onvolledig(self):
        plan = am.nieuw_plan("x")
        blokken = _vol_blokken()
        blokken["stappen"][0]["foutscenario"] = ""
        plan["blokken"] = blokken
        r = am.valideer_klaar(plan)
        self.assertFalse(r["geldig"])

    def test_status_klaar_pas_na_valide(self):
        plan = am.nieuw_plan("x")
        with self.assertRaises(ValueError):
            am.zet_klaar(plan)  # leeg plan kan niet naar klaar
        plan["blokken"] = _vol_blokken()
        gewijzigd = am.zet_klaar(plan)
        self.assertEqual(gewijzigd["status"], "klaar")


class TestSecrets(unittest.TestCase):
    def test_plan_met_api_key_geweigerd(self):
        plan = am.nieuw_plan("x")
        blokken = _vol_blokken()
        blokken["bronnen"]["authenticatie"] = "key sk-REDACTED-VOORBEELD-1234567890"
        plan["blokken"] = blokken
        r = am.valideer_klaar(plan)
        # NB: de scanner ziet 'sk-…' ( geldig patroon), de waarde is een
        # gemarkeerd voorbeeld — maar het plan móét geweigerd worden:
        # in een écht plan hoort geen key-achtige reeks, ook geen nep.
        self.assertFalse(r["geldig"])

    def test_toevoegen_met_secret_geweigerd(self):
        with tempfile.TemporaryDirectory() as tmp:
            with mock.patch.object(am, "_opslag_pad",
                                   return_value=Path(tmp) / "plannen.json"):
                with self.assertRaises(ValueError):
                    # CI-vrijstellings-marker in dezelfde regel: dit is een
                    # testfixture, geen echte key. Het patroon (ghp_+30) is
                    # wél echt, dus de weigering wordt bewezen.
                    am.voeg_toe(titel="x", blokken=_vol_blokken_met_key())


def _vol_blokken_met_key():
    b = _vol_blokken()
    b["bronnen"]["authenticatie"] = "ghp_redactedXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX"
    return b


class TestOpslagEnExport(unittest.TestCase):
    def test_toevoegen_en_lijst_en_lezen(self):
        with tempfile.TemporaryDirectory() as tmp:
            with mock.patch.object(am, "_opslag_pad",
                                   return_value=Path(tmp) / "plannen.json"):
                plan = am.voeg_toe(titel="Ochtendsamenvatting",
                                   blokken=_vol_blokken())
                lijst = am.lijst()
                self.assertEqual(len(lijst), 1)
                self.assertEqual(lijst[0]["titel"], "Ochtendsamenvatting")
                gelezen = am.lees(plan["id"])
                self.assertEqual(
                    gelezen["blokken"]["doel_en_trigger"]["doel"],
                    "Elke ochtend een samenvatting van nieuwe Drive-bestanden in Telegram")

    def test_markdown_export_bevat_zes_koppen(self):
        plan = am.nieuw_plan("x")
        plan["blokken"] = _vol_blokken()
        md = am.export_markdown(plan)
        for kop in ("Doel & trigger", "Bronnen & data", "Stappen",
                    "Kwaliteit & verificatie", "Planning & uitvoering",
                    "Randvoorwaarden & privacy"):
            self.assertIn(kop, md)

    def test_json_export_import_rondje(self):
        plan = am.nieuw_plan("x")
        plan["blokken"] = _vol_blokken()
        js = am.export_json(plan)
        terug = am.import_json(js)
        self.assertEqual(terug["titel"], plan["titel"])
        self.assertEqual(terug["blokken"]["stappen"][1]["omschrijving"],
                         "Vat samen en verstuur")

    def test_log_wordt_geboekt(self):
        with tempfile.TemporaryDirectory() as tmp:
            logpad = Path(tmp) / "log.json"
            with mock.patch.object(am, "_log_pad", return_value=logpad), \
                 mock.patch.object(am, "_opslag_pad",
                                   return_value=Path(tmp) / "plannen.json"):
                am.voeg_toe(titel="x", blokken=_vol_blokken())
                regels = json.loads(logpad.read_text())
                self.assertEqual(regels[-1]["actie"], "toevoegen")


if __name__ == "__main__":
    unittest.main()
