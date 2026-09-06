"""Tests voor de KairOS netwerkmonitor (fase 1).

De monitor bewijst verificatie-eis 2: geen verkeer naar externe
AI-aanbieders tijdens normale werking. Hij leest een JSON-verkeersbestand
(netstat/lsof-uitvoer) en een Ollama-taglijst, en oordeelt.
"""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.kairos import netwerkmonitor as nm


class TestExterneAanbieders(unittest.TestCase):
    def test_bekende_aanbieder_wordt_gevangen(self):
        regels = [
            "tcp 10.0.0.2:54321 -> 104.18.7.123:443 (api.openai.com)",
        ]
        bevindingen = nm.scan_verkeersregels(regels)
        self.assertTrue(any(b["ernst"] == "ALARM" for b in bevindingen))

    def test_lokale_verbindingen_alarmeren_niet(self):
        regels = [
            "tcp 127.0.0.1:54321 -> 127.0.0.1:11434 (localhost)",
            "tcp 10.0.0.2:22 -> 192.168.1.50:51000 (thuisnetwerk)",
        ]
        bevindingen = nm.scan_verkeersregels(regels)
        self.assertEqual([b for b in bevindingen if b["ernst"] == "ALARM"], [])

    def test_onbekende_host_geeft_waarschuwing_geen_alarm(self):
        regels = ["tcp 10.0.0.2:55555 -> 1.2.3.4:443 (voorbeeld.example)"]
        bevindingen = nm.scan_verkeersregels(regels)
        alarmen = [b for b in bevindingen if b["ernst"] == "ALARM"]
        waarschuwingen = [b for b in bevindingen if b["ernst"] == "WAARSCHUWING"]
        self.assertEqual(alarmen, [])
        self.assertEqual(len(waarschuwingen), 1)

    def test_leeg_verkeer_is_ok(self):
        self.assertEqual(nm.scan_verkeersregels([]), [])


class TestOllamaModellen(unittest.TestCase):
    def test_cloud_model_is_externe_afhankelijkheid(self):
        tags = {"models": [{"name": "glm-4.6:cloud"}, {"name": "gemma3:4b"}]}
        bevindingen = nm.scan_ollama_tags(tags)
        alarmen = [b for b in bevindingen if b["ernst"] == "ALARM"]
        self.assertEqual(len(alarmen), 1)
        self.assertIn("glm-4.6:cloud", alarmen[0]["melding"])

    def test_local_models_schone_taglijst(self):
        tags = {"models": [{"name": "gemma3:4b"}, {"name": "gemma3:1b"}]}
        bevindingen = nm.scan_ollama_tags(tags)
        alarmen = [b for b in bevindingen if b["ernst"] == "ALARM"]
        self.assertEqual(alarmen, [])

    def test_ollama_onbereikbaar_is_waarschuwing(self):
        bevindingen = nm.scan_ollama_tags(None)
        waarschuwingen = [b for b in bevindingen if b["ernst"] == "WAARSCHUWING"]
        self.assertEqual(len(waarschuwingen), 1)


class TestOordeelEnVorm(unittest.TestCase):
    def test_alarm_maakt_ok_onwaar(self):
        self.assertFalse(nm.oordeel([
            {"ernst": "ALARM", "melding": "x", "bron": "verkeer"}]))
        self.assertTrue(nm.oordeel([
            {"ernst": "WAARSCHUWING", "melding": "x", "bron": "verkeer"}]))
        self.assertTrue(nm.oordeel([]))

    def test_rapport_is_machine_toetsbaar(self):
        rapport = nm.rapport(
            oordeel=True,
            bevindingen=[{"ernst": "WAARSCHUWING", "melding": "m", "bron": "v"}])
        zelfde = json.loads(json.dumps(rapport))  # moet rond JSON kunnen
        self.assertIn("ok", zelfde)
        self.assertIn("bevindingen", zelfde)
        self.assertIn("datum", zelfde)

    def test_eindoordeel_integreert_alle_bronnen(self):
        with tempfile.TemporaryDirectory() as tmp:
            verkeer = Path(tmp) / "verkeer.json"
            verkeer.write_text(json.dumps([
                "tcp 10.0.0.2:1 -> 1.2.3.4:443 (api.openai.com)"]))
            with patch.object(nm, "_lees_ollama_tags", return_value=None):
                rapport = nm.eindoordeel(verkeer_pad=verkeer)
        self.assertFalse(rapport["ok"])  # openai in het verkeer = alarm
