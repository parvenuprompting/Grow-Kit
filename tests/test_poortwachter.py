#!/usr/bin/env python3
"""Tests: de Poortwachter — getypeerde beslisser vóór de LLM (1 okt 2026).

Ontwerp volgt de review van Claude (1 okt): drie trappen in plaats van twee.
1. Regels eerst — gratis en 100% voorspelbaar. @naam-mentions en
   machine-alerts van eigen scripts hebben geen model nodig.
2. Classifier alleen voor vrije tekst van buiten.
3. LLM bij twijfel.

Harde regels die deze tests vastleggen:
- Machine-alerts en security-meldingen gaan NOOIT door een probabilistisch
  filter. De handhaver is de router zelf (bron=script slaat trap 2 over).
- Ruis wordt nooit weggegooid, alleen gedegradeerd en gelogd (append-only).
- Drempel per klasse, niet één drempel: "urgent als ruis" is veel erger dan
  "ruis als urgent", dus ruis vraagt meer zekerheid dan urgent.
- Een vast percentage (5%) van de zekere gevallen gaat alsnog naar de LLM
  (audit), anders ziet niemand de zelfverzekerde fouten.
- Zonder classifier: nooit stil gokken, altijd naar de LLM.
"""
import json
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).parent.parent
sys.path.insert(0, str(REPO))

from kern import growkit_poortwachter as pw


class TestTrap1Regels(unittest.TestCase):
    """Trap 1: deterministische regels, geen model."""

    def test_mention_routeert_naar_die_agent(self):
        b = pw.poort({"tekst": "@vigil kun je de logs nalopen?"}, bron="mens")
        self.assertEqual(b["laag"], pw.LAAG_REGEL)
        self.assertEqual(b["route"], "vigil")
        self.assertIsNone(b["confidence"])

    def test_mention_roept_nooit_de_classifier_aan(self):
        aangeroepen = []

        def vals_aangeroepen(*_a, **_k):
            aangeroepen.append(1)
            return ("ruis", 0.99)

        b = pw.poort({"tekst": "@libra wat kost het vandaag?"}, bron="mens",
                     classificeerder=vals_aangeroepen)
        self.assertEqual(aangeroepen, [])
        self.assertEqual(b["laag"], pw.LAAG_REGEL)

    def test_mention_van_onbekende_naam_valt_terug_zonder_crash(self):
        b = pw.poort({"tekst": "@onbekende_agent doe iets"}, bron="mens")
        self.assertEqual(b["laag"], pw.LAAG_LLM)
        self.assertEqual(b["route"], "llm")

    def test_script_alert_gaat_nooit_door_het_filter(self):
        aangeroepen = []

        def vals_aangeroepen(*_a, **_k):
            aangeroepen.append(1)
            return ("ruis", 0.99)

        b = pw.poort({"tekst": "POORT-WACHTER: nieuwe open poort 8080",
                      "ernst": "urgent"}, bron="script",
                     classificeerder=vals_aangeroepen)
        self.assertEqual(b["laag"], pw.LAAG_REGEL)
        self.assertEqual(b["route"], "direct")
        self.assertEqual(b["klasse"], "urgent")
        self.assertEqual(aangeroepen, [], "machine-alerts mogen nooit gefilterd worden")

    def test_script_alert_wordt_nooit_gedegradeerd_tot_ruis(self):
        def alles_ruis(*_a, **_k):
            return ("ruis", 0.99)

        b = pw.poort({"tekst": "STILLE WAKER: wachtrij 40 min stil",
                      "ernst": "urgent"}, bron="script",
                     classificeerder=alles_ruis)
        self.assertTrue(b["gedegradeerd"] is False)
        self.assertEqual(b["route"], "direct")


class TestTrap2Classifier(unittest.TestCase):
    """Trap 2: classifier voor vrije tekst van buiten."""

    def test_zekere_urgentie_wordt_afgehandeld_zonder_llm(self):
        b = pw.poort({"tekst": "Mijn betaling is mislukt, dit moet nu"},
                     bron="mens", classificeerder=lambda t: ("urgent", 0.95))
        self.assertEqual(b["laag"], pw.LAAG_CLASSIFIER)
        self.assertEqual(b["klasse"], "urgent")
        self.assertEqual(b["route"], "afgehandeld")
        self.assertFalse(b["audit"])

    def test_twijfel_gaat_naar_de_llm(self):
        b = pw.poort({"tekst": "hmm vaag bericht"}, bron="mens",
                     classificeerder=lambda t: ("normaal", 0.40))
        self.assertEqual(b["laag"], pw.LAAG_LLM)
        self.assertEqual(b["route"], "llm")

    def test_zonder_classifier_nooit_stil_gokken(self):
        b = pw.poort({"tekst": "een gewoon bericht"}, bron="mens")
        self.assertEqual(b["laag"], pw.LAAG_LLM)
        self.assertEqual(b["route"], "llm")
        self.assertIn("geen classifier", b["reden"])


class TestDrempelPerKlasse(unittest.TestCase):
    """Asymmetrische kosten: ruis vraagt meer zekerheid dan urgent."""

    def test_ruis_drempel_is_strenger_dan_urgent_drempel(self):
        d = pw.STANDAARD_DREMPELS
        self.assertGreater(d["ruis"], d["urgent"])

    def test_ruis_met_midconfidence_gaat_naar_de_llm_niet_de_prullenbak(self):
        b = pw.poort({"tekst": "ok" * 50}, bron="mens",
                     classificeerder=lambda t: ("ruis", 0.80))
        self.assertEqual(b["laag"], pw.LAAG_LLM, "0.80 is te weinig zekerheid voor ruis")

    def test_ruis_met_hoge_zekerheid_wordt_gedegradeerd_maar_bewaard(self):
        with tempfile.TemporaryDirectory() as tmp:
            pad = Path(tmp) / "poortwachter.jsonl"
            b = pw.poort({"tekst": "ok" * 50}, bron="mens",
                         classificeerder=lambda t: ("ruis", 0.97),
                         logboek=pad)
            self.assertTrue(b["gedegradeerd"])
            self.assertEqual(b["route"], "gedegradeerd")
            regels = [json.loads(l) for l in pad.read_text(encoding="utf-8").splitlines()]
            self.assertEqual(len(regels), 1, "ruis moet bewaard blijven, niet weggegooid")
            self.assertEqual(regels[0]["klasse"], "ruis")


class TestAuditSteekproef(unittest.TestCase):
    """De filter kan zijn eigen zelfverzekerde fouten niet zien."""

    def test_een_op_twintig_zekere_gevallen_gaat_alsnog_naar_de_llm(self):
        b = pw.poort({"tekst": "gewone vraag"}, bron="mens",
                     classificeerder=lambda t: ("normaal", 0.99),
                     audit_teller=20)
        self.assertEqual(b["laag"], pw.LAAG_LLM)
        self.assertTrue(b["audit"])
        self.assertIn("audit", b["reden"])

    def test_geen_audit_buiten_de_steekproef(self):
        b = pw.poort({"tekst": "gewone vraag"}, bron="mens",
                     classificeerder=lambda t: ("normaal", 0.99),
                     audit_teller=21)
        self.assertEqual(b["laag"], pw.LAAG_CLASSIFIER)
        self.assertFalse(b["audit"])


class TestSpoor(unittest.TestCase):
    """Elk besluit laat een append-only spoor achter."""

    def test_besluit_bevat_laag_route_en_reden(self):
        b = pw.poort({"tekst": "@codex log dit"}, bron="mens")
        for veld in ("laag", "route", "klasse", "confidence", "reden",
                     "audit", "gedegradeerd", "tijdstip"):
            self.assertIn(veld, b)

    def test_logboek_is_append_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            pad = Path(tmp) / "poortwachter.jsonl"
            pw.poort({"tekst": "@vigil een"}, bron="mens", logboek=pad)
            pw.poort({"tekst": "@libra twee"}, bron="mens", logboek=pad)
            regels = pad.read_text(encoding="utf-8").splitlines()
            self.assertEqual(len(regels), 2)


if __name__ == "__main__":
    unittest.main()
