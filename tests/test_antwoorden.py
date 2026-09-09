"""Tests voor growkit_antwoorden — Slice A: agent-antwoorden lezen (voor de app).

Antwoordbestanden liggen op de VPS in agenttaken/<agent>/antwoorden/<taak_id>.json.
De module leest ze via een injecteerbare bestandslezer (zelfde patroon als
growkit_agentstatus), zodat tests offline en deterministisch draaien.
"""
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from kern import growkit_antwoorden as aw


def maak_bestandslezer(bestanden: dict):
    """bestanden: pad -> dict-of-json-raw-string"""
    def lezer(pad: str) -> str:
        if pad not in bestanden:
            raise FileNotFoundError(pad)
        return bestanden[pad]
    return lezer


def maak_lijster(bestanden: dict):
    def lijster(map_pad: str) -> list[str]:
        prefix = map_pad.rstrip("/") + "/"
        return [p for p in bestanden if p.startswith(prefix)]
    return lijster


VOORBEELD_TAAK = {
    "taak_id": "taak-001", "agent": "genius", "bron": "agentchat",
    "bericht": "doe iets", "van": "tiendo",
    "antwoord": "Klaar, Baas.", "status": "afgerond",
    "afgerond_op": "2026-09-10T01:00:00+00:00",
}

VOORBEELD_GEFAALD = {
    "taak_id": "taak-002", "agent": "vigil", "bron": "agentchat",
    "antwoord": "(TAAK GEFAALD — timeout)", "status": "gefaald: timeout_120s",
    "afgerond_op": "2026-09-10T02:00:00+00:00",
}


class TestLeesAntwoord(unittest.TestCase):
    def test_geldig_antwoord_wordt_gelezen(self):
        lezer = maak_bestandslezer({"/x/taak-001.json": json.dumps(VOORBEELD_TAAK)})
        d = aw.lees_antwoord("/x/taak-001.json", lezer)
        self.assertEqual(d["taak_id"], "taak-001")
        self.assertEqual(d["status"], "afgerond")

    def test_corrupt_json_is_nette_fout(self):
        lezer = maak_bestandslezer({"/x/kapot.json": "{dit is geen json"})
        with self.assertRaises(ValueError):
            aw.lees_antwoord("/x/kapot.json", lezer)

    def test_ontbrekend_bestand_is_duidelijke_fout(self):
        lezer = maak_bestandslezer({})
        with self.assertRaises(FileNotFoundError):
            aw.lees_antwoord("/x/bestaat-niet.json", lezer)

    def test_antwoord_zonder_verplichte_velden_wordt_geweigerd(self):
        lezer = maak_bestandslezer({"/x/leeg.json": json.dumps({"hallo": 1})})
        with self.assertRaises(ValueError):
            aw.lees_antwoord("/x/leeg.json", lezer)


class TestLijstAntwoorden(unittest.TestCase):
    def setUp(self):
        self.bestanden = {
            "/root/agenttaken/genius/antwoorden/taak-001.json": json.dumps(VOORBEELD_TAAK),
            "/root/agenttaken/vigil/antwoorden/taak-002.json": json.dumps(VOORBEELD_GEFAALD),
        }

    def test_overzicht_sorteert_nieuwste_eerst(self):
        lijster = maak_lijster(self.bestanden)
        lezer = maak_bestandslezer(self.bestanden)
        overzicht = aw.overzicht_antwoorden(
            ["/root/agenttaken/genius/antwoorden", "/root/agenttaken/vigil/antwoorden"],
            lijster, lezer)
        self.assertEqual(len(overzicht), 2)
        self.assertEqual(overzicht[0]["taak_id"], "taak-002")  # 02:00 > 01:00

    def test_status_filter(self):
        lijster = maak_lijster(self.bestanden)
        lezer = maak_bestandslezer(self.bestanden)
        gefaald = aw.overzicht_antwoorden(
            ["/root/agenttaken/genius/antwoorden", "/root/agenttaken/vigil/antwoorden"],
            lijster, lezer, status="gefaald")
        self.assertEqual(len(gefaald), 1)
        self.assertEqual(gefaald[0]["agent"], "vigil")

    def test_corrupt_bestand_wordt_overgeslagen_niet_crash(self):
        bestanden = dict(self.bestanden)
        bestanden["/root/agenttaken/genius/antwoorden/kapot.json"] = "{kapot"
        lijster = maak_lijster(bestanden)
        lezer = maak_bestandslezer(bestanden)
        overzicht = aw.overzicht_antwoorden(
            ["/root/agenttaken/genius/antwoorden", "/root/agenttaken/vigil/antwoorden"],
            lijster, lezer)
        self.assertEqual(len(overzicht), 2)  # kapotte overgeslagen


if __name__ == "__main__":
    unittest.main()
