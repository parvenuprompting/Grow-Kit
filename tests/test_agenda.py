"""Testen voor de Agenda-kern (kern/growkit_agenda.py).

De agenda verzamelt alles dat VASTLIGT qua toekomstig werk uit
bestaande bronnen (geen nieuwe backend):
- Mac-cron (launchd/hermes cron jobs.json)
- VPS-cron (crontab -l via SSH)
- GrowKit-taken (takenlijst per boom)
- Ratificaties / goedkeuringen (wachtende mens-momenten)

Deterministisch: de adapter levert feiten, geen interpretatie. Elk
item: {bron, titel, schema, soort, detail}. Fouten per bron geïsoleerd
(een onbereikbare bron = één "onbekend"-item, geen crash).
"""
import json
import unittest
from unittest import mock

from kern import growkit_agenda as ag


class TestCronParse(unittest.TestCase):
    def test_cronregel_elke_minuut(self):
        r = ag._cron_schema("*/5 * * * *", "secmon")
        self.assertEqual(r, "elke 5 minuten")

    def test_cronregel_dagelijks_ochtend(self):
        r = ag._cron_schema("0 8 * * *", "secmon-digest")
        self.assertEqual(r, "dagelijks om 08:00")

    def test_cronregel_avond(self):
        r = ag._cron_schema("0 21 * * *", "sessiedoc")
        self.assertEqual(r, "dagelijks om 21:00")

    def test_cronregel_wekelijks(self):
        r = ag._cron_schema("0 9 * * 1", "weektaak")
        self.assertEqual(r, "wekelijks op maandag om 09:00")

    def test_cronregel_onbekend_toont_ruw(self):
        r = ag._cron_schema("30 4 1,15 * *", "tweeweklijks")
        self.assertIn("30 4 1,15 * *", r)

    def test_hermes_cron_expr(self):
        r = ag._cron_schema("0 20 * * *", "brain-sync")
        self.assertEqual(r, "dagelijks om 20:00")


class TestHermesCron(unittest.TestCase):
    def test_jobs_json_wordt_genormaliseerd(self):
        data = {"jobs": [
            {"id": "88b498a7", "name": "Dagelijks skills-overzicht",
             "schedule": {"kind": "cron", "expr": "0 18 * * *",
                          "display": "0 18 * * *"}},
            {"id": "31ea179b", "name": "VPS sync-log check",
             "schedule": {"kind": "once",
                          "run_at": "2026-09-03T08:30:00+02:00"}},
        ]}
        with mock.patch.object(ag, "_hermes_jobs_bestand",
                               return_value=data):
            items = ag._bron_hermes_cron()
        self.assertEqual(len(items), 2)
        self.assertEqual(items[0]["bron"], "cron (Mac · hermes)")
        self.assertIn("18:00", items[0]["schema"])
        self.assertEqual(items[1]["soort"], "eenmalig")

    def test_ontbrekend_bestand_leegt_bron(self):
        with mock.patch.object(ag, "_hermes_jobs_bestand", return_value=None):
            self.assertEqual(ag._bron_hermes_cron(), [])


class TestVpsCron(unittest.TestCase):
    def test_ssh_uitvoer_wordt_regels(self):
        uit = ("*/5 * * * * sudo secmon\n"
               "0 8 * * * sudo secmon-digest\n"
               "* * * * * /usr/bin/python3 /root/agentchat-poller.py")
        items = ag._vps_cron_uit_uitvoer(uit)
        self.assertEqual(len(items), 3)
        self.assertEqual(items[0]["bron"], "cron (VPS)")
        self.assertIn("agentchat-poller", items[2]["titel"])

    def test_foute_ssh_geeft_onbekend_item(self):
        items = ag._vps_cron_uit_code(255)
        self.assertEqual(len(items), 1)
        self.assertIn("onbekend", items[0]["schema"].lower())


class TestMensMomenten(unittest.TestCase):
    def test_ratificaties_wachten_op_jou(self):
        met_data = {"doel": "/tmp/x"}
        # we mocken de adapter-aanroepen in de verzamelfunctie
        with mock.patch.object(ag, "_bron_ratificaties",
                               return_value=[
                                   {"bron": "ratificatie", "soort": "wacht op jou",
                                    "titel": "Boom X · stap 3",
                                    "schema": "wacht op jou", "detail": met_data}]):
            items = ag.verzamel()
        rat = [i for i in items if i["bron"] == "ratificatie"]
        self.assertEqual(len(rat), 1)
        self.assertEqual(rat[0]["soort"], "wacht op jou")


class TestVerzamel(unittest.TestCase):
    def test_verzamel_levert_lijst_met_alle_soorten(self):
        with mock.patch.object(ag, "_bron_hermes_cron",
                               return_value=[{"bron": "cron (Mac · hermes)",
                                              "soort": "herhalend",
                                              "titel": "skills-overzicht",
                                              "schema": "dagelijks om 18:00",
                                              "detail": ""}]), \
             mock.patch.object(ag, "_bron_vps_cron",
                               return_value=[{"bron": "cron (VPS)",
                                              "soort": "herhalend",
                                              "titel": "agentchat-poller",
                                              "schema": "elke 1 minuut",
                                              "detail": ""}]), \
             mock.patch.object(ag, "_bron_mens_momenten",
                               return_value=[{"bron": "ratificatie",
                                              "soort": "wacht op jou",
                                              "titel": "Boom X",
                                              "schema": "wacht op jou",
                                              "detail": ""}]):
            items = ag.verzamel()
    # (asserties buiten de with om de mocks te laten sluiten)
        bronnen = {i["bron"] for i in items}
        self.assertIn("cron (Mac · hermes)", bronnen)
        self.assertIn("cron (VPS)", bronnen)
        self.assertIn("ratificatie", bronnen)


if __name__ == "__main__":
    unittest.main()
