#!/usr/bin/env python3
"""Tests: actuele modellen ophalen via de adapter (models-commando).

De lijst komt van de provider (OpenRouter /models, geen sleutel nodig)
met een lokale cache (15 min) zodat de dropdown snel opent. Fail-open:
bij netwerkfout antwoordt de adapter met een cache of een nette melding —
nooit een crash.
"""
import json
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).parent.parent
sys.path.insert(0, str(REPO))

from kern import growkit_openrouter as gom


class TestModelsParser(unittest.TestCase):
    def test_verwerk_api_antwoord(self):
        ruw = {"data": [
            {"id": "openai/gpt-6-astra", "name": "OpenAI: GPT-6 Astra",
             "context_length": 400000, "pricing": {"prompt": "0.000001"}},
            {"id": "z-ai/glm-5.3", "name": "Z-AI: GLM 5.3",
             "context_length": 200000, "pricing": {"prompt": "0.0000005"}},
        ]}
        modellen = gom.verwerk_modellen(ruw)
        self.assertEqual(len(modellen), 2)
        self.assertEqual(modellen[0]["id"], "openai/gpt-6-astra")
        self.assertEqual(modellen[0]["naam"], "OpenAI: GPT-6 Astra")
        self.assertEqual(modellen[0]["context"], 400000)

    def test_leeg_antwoord_geeft_lege_lijst(self):
        self.assertEqual(gom.verwerk_modellen({"data": []}), [])

    def test_ongeldige_ruw_wordt_overgeslagen(self):
        ruw = {"data": [
            {"id": "goed/model", "name": "Goed"},
            {"geen": "id"},
            "onzin",
        ]}
        modellen = gom.verwerk_modellen(ruw)
        self.assertEqual([m["id"] for m in modellen], ["goed/model"])


class TestCache(unittest.TestCase):
    def setUp(self):
        import tempfile
        self.tmp = tempfile.TemporaryDirectory()
        self.cache_pad = Path(self.tmp.name) / "modellen-cache.json"

    def tearDown(self):
        self.tmp.cleanup()

    def test_cache_bewaart_en_leest(self):
        modellen = [{"id": "a/b", "naam": "A B", "context": 1000, "prijs_prompt": 1.0}]
        gom.sla_cache_op(modellen, self.cache_pad)
        gelezen = gom.lees_cache(self.cache_pad, max_leeftijd_minuten=15)
        self.assertEqual(gelezen[0]["id"], "a/b")

    def test_oude_cache_is_verlopen(self):
        import time
        modellen = [{"id": "a/b", "naam": "A B", "context": 1000, "prijs_prompt": 1.0}]
        gom.sla_cache_op(modellen, self.cache_pad)
        # schrijf tijdstip 20 minuten terug
        doc = json.loads(self.cache_pad.read_text(encoding="utf-8"))
        doc["opgehaald"] = "2026-01-01T00:00:00+00:00"
        self.cache_pad.write_text(json.dumps(doc), encoding="utf-8")
        self.assertIsNone(gom.lees_cache(self.cache_pad, max_leeftijd_minuten=15))

    def test_corrupte_cache_is_geen_crash(self):
        self.cache_pad.write_text("{onzin", encoding="utf-8")
        self.assertIsNone(gom.lees_cache(self.cache_pad))


class TestAdapterModels(unittest.TestCase):
    def _roep(self, invoer):
        import io
        from contextlib import redirect_stdout
        import adapter
        buf = io.StringIO()
        code = 0
        with redirect_stdout(buf):
            import sys as s
            s.stdin = io.StringIO(json.dumps(invoer))
            code = adapter.main(["models"]) or 0
        return int(code), json.loads(buf.getvalue().strip())

    def test_models_geeft_ok_of_nette_melding(self):
        code, uit = self._roep({"doel": "/tmp"})
        self.assertEqual(code, 0)
        self.assertTrue(uit["ok"])
        data = uit["data"]
        # live of cache: altijd een lijst; alleen bij falen een leesbare melding
        self.assertIsInstance(data["modellen"], list)
        self.assertIn(data["bron"], ("live", "cache", "onbereikbaar"))
        if data["bron"] == "onbereikbaar":
            self.assertTrue(data.get("melding"))


if __name__ == "__main__":
    unittest.main()
