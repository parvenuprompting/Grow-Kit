"""Tests voor growkit_breinzijk — Trede 1: familie-brein-zoeker als Grow Kit-kernmodule.

De zoeker beantwoordt vragen uit de EIGEN familie-geschiedenis (besluiten, Academy,
curatie) via een lokale embedding-index. Deze tests gebruiken een IN-MEMORY index
(geen API-calls, geen netwerk) zodat ze snel, deterministisch en offline draaien.
"""
import json
import math
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from kern import growkit_breinzoeker as bz


class TestCosine(unittest.TestCase):
    def test_identieke_vectors_scoren_1(self):
        self.assertAlmostEqual(bz.cosine([1, 0, 0], [1, 0, 0]), 1.0)

    def test_orthogonale_vectors_scoren_0(self):
        self.assertAlmostEqual(bz.cosine([1, 0], [0, 1]), 0.0)

    def test_nulvector_geeft_0_geen_crash(self):
        self.assertEqual(bz.cosine([0, 0], [1, 1]), 0.0)


class TestZoekInIndex(unittest.TestCase):
    def setUp(self):
        self.index = {
            "chunks": [
                {"bron": "besluiten.md", "offset": 0, "tekst": "BSL-037 privacy-poort: SOUL's nooit in publieke repo"},
                {"bron": "inbox/academy.md", "offset": 0, "tekst": "Claude-les: eis een eigenaar en een bewijsplek"},
                {"bron": "inbox/kenji.md", "offset": 0, "tekst": "Kenji is de Tegenstem: scherpe kritiek, max 2 reacties"},
            ],
            "vectors": [
                [1.0, 0.0, 0.0],
                [0.0, 1.0, 0.0],
                [0.0, 0.0, 1.0],
            ],
        }

    def test_beste_match_bovenaan(self):
        resultaten = bz.zoek_in_index(self.index, [1.0, 0.0, 0.0], top=3)
        self.assertEqual(resultaten[0]["bron"], "besluiten.md")
        self.assertAlmostEqual(resultaten[0]["score"], 1.0)

    def test_top_limitering(self):
        resultaten = bz.zoek_in_index(self.index, [1.0, 0.0, 0.0], top=2)
        self.assertEqual(len(resultaten), 2)

    def test_min_score_filtert_ruis(self):
        resultaten = bz.zoek_in_index(self.index, [1.0, 0.0, 0.0], top=3, min_score=0.9)
        self.assertEqual(len(resultaten), 1)


class TestIndexBestand(unittest.TestCase):
    def test_ontbrekende_index_geeft_duidelijke_fout(self):
        with self.assertRaises(FileNotFoundError):
            bz.laad_index("/pad/bestaat/niet/index.json")

    def test_index_rondje_lezen(self):
        import tempfile
        idx = {"chunks": [{"bron": "a", "offset": 0, "tekst": "hallo"}],
               "vectors": [[0.1, 0.2]]}
        with tempfile.TemporaryDirectory() as d:
            pad = Path(d) / "index.json"
            pad.write_text(json.dumps(idx))
            gelezen = bz.laad_index(str(pad))
            self.assertEqual(gelezen["chunks"][0]["tekst"], "hallo")


if __name__ == "__main__":
    unittest.main()
