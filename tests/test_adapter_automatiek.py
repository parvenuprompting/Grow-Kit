"""Adapter-tests voor Automatiek: plannen via de JSON-CLI.

De KairOS-koppeling (één zin → KairOS maakt een voorstel via de
wachtrij) zit in cmd_automatiekvoorstel: die legt een bericht met
bron=automatiek in de wachtrij — de poller + SOUL van KairOS doen de
rest. De adapter zelf interpreteert niets (huisregel).
"""
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import adapter
from kern import growkit_automatiek as am
from kern import growkit_agenttaak as at


def _vol_blokken():
    return {
        "doel_en_trigger": {"doel": "ochtendsamenvatting", "trigger": "08:00",
                            "trigger_type": "schema"},
        "bronnen": {"diensten": "Drive, Telegram", "data": "nieuwe bestanden",
                    "authenticatie": "op de doelmachine"},
        "stappen": [{"nummer": 1, "omschrijving": "zoek", "invoer": "q",
                     "uitvoer": "lijst", "foutscenario": "herhaal"}],
        "kwaliteit": {"verificatie": "bericht arriveert", "testaanpak": "handmatig"},
        "uitvoering": {"omgeving": "VPS", "planning": "cron",
                       "faalafhandeling": "3 pogingen"},
        "randvoorwaarden": {"privacy": "alleen namen", "randgevallen": "lege dag"},
    }


class TestAutomatiekAdapter(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        tmp = Path(self._tmp.name)
        p1 = mock.patch.object(am, "_opslag_pad",
                               return_value=tmp / "plannen.json")
        p2 = mock.patch.object(am, "_log_pad", return_value=tmp / "log.json")
        p1.start(); p2.start()
        self.addCleanup(p1.stop); self.addCleanup(p2.stop)

    def test_toevoegen_via_adapter(self):
        uit = adapter.COMMANDOS["automatiektoevoegen"](
            {"titel": "Ochtend", "blokken": _vol_blokken()})
        self.assertTrue(uit["ok"])
        self.assertIn(uit["data"]["plan"]["status"], ("concept", "klaar"))

    def test_lijst_leeg_is_nette_lijst(self):
        uit = adapter.COMMANDOS["automatieklijst"]({})
        self.assertTrue(uit["ok"])
        self.assertEqual(uit["data"]["plannen"], [])

    def test_lees_verplicht_id(self):
        with self.assertRaises(adapter.AdapterFout):
            adapter.COMMANDOS["automatieklees"]({})

    def test_zet_klaar_weigert_leeg_plan_nettelijk(self):
        plan = am.voeg_toe(titel="x", blokken={})
        with self.assertRaises(adapter.AdapterFout):
            adapter.COMMANDOS["automatiekstatus"]({"id": plan["id"],
                                                   "klaar": True})

    def test_export_markdown(self):
        plan = am.voeg_toe(titel="x", blokken=_vol_blokken())
        uit = adapter.COMMANDOS["automatiekexport"](
            {"id": plan["id"], "formaat": "markdown"})
        self.assertIn("# x", uit["data"]["inhoud"])
        self.assertIn("Doel & trigger", uit["data"]["inhoud"])

    def test_voorgestel_plant_bericht_in_kairos_wachtrij(self):
        # bron=automatiek bericht belandt in de wachtrij van kairos
        # (gevangen via de uitvoerder-parameter van agenttaak.verstuur)
        gevangen = {}

        def nep_uitvoerder(commando, stdin, timeout):
            gevangen["stdin"] = json.loads(stdin)
            return 0, ""

        with mock.patch.object(at, "_standaard_uitvoerder", nep_uitvoerder), \
             mock.patch.object(at, "verstuur", wraps=lambda agent, taak_id,
                               titel, *, contract=None, van="",
                               uitvoerder=None, timeout=20:
                               {"ok": True, "data": {"taak_id": taak_id}}
                               ) as verstuur_spy:
            # We spy niet om het resultaat maar om de doorlopende args te
            # vangen: echte verstuur is al gemocked, dus roep direct de
            # adapter en lees de gevangen call-args.
            uit = adapter.COMMANDOS["automatiekvoorstel"](
                {"wens": "elke ochtend Drive-samenvatting in Telegram",
                 "van": "Tiëndo"})
        self.assertTrue(uit["ok"])
        args, kwargs = verstuur_spy.call_args
        self.assertEqual(args[0], "kairos")
        self.assertIn("Drive-samenvatting", args[2])
        self.assertEqual(kwargs.get("van"), "Tiëndo")

    def test_voorstel_zonder_wens_geweigerd(self):
        with self.assertRaises(adapter.AdapterFout):
            adapter.COMMANDOS["automatiekvoorstel"]({"wens": "  "})


if __name__ == "__main__":
    unittest.main()
