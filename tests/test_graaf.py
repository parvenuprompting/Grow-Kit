"""Fase A+ — tests voor de knowledge-graph: het brein als kaart.

Bewijsvruchten:
- graaf-draaglast: manifest → knopen (alle documenten) + verbindingen
  (sectie-hubs, gelijkgetitelde koppelingen) — alle 438 documenten erin
- zoom-pad is deterministisch: elk knooppunt is bereikbaar vanaf het centrum
- lees-route: één document ophalen via pad (alleen-lezen SSH cat)
"""
import json
import unittest
from pathlib import Path

from kern import growkit_graaf as gg


class TestGraaf(unittest.TestCase):
    def test_knopen_uit_manifest(self):
        manifest = {"documenten": [
            {"pad": "inbox/a.md", "titel": "A", "sectie": "inbox", "regels": 10},
            {"pad": "kennis/b.md", "titel": "B", "sectie": "kennis", "regels": 5},
            {"pad": "INDEX.md", "titel": "INDEX", "sectie": "root", "regels": 69},
        ]}
        graaf = gg.bouw_knopen(manifest)
        # 3 documenten + 2 sectie-hubs (root is geen hub nodig)
        namen = [k["id"] for k in graaf["knopen"]]
        self.assertIn("doc:inbox/a.md", namen)
        self.assertIn("hub:inbox", namen)
        self.assertIn("doc:INDEX.md", namen)

    def test_verbindingen_doc_naar_hub(self):
        manifest = {"documenten": [
            {"pad": "inbox/a.md", "titel": "A", "sectie": "inbox", "regels": 1},
            {"pad": "kennis/b.md", "titel": "B", "sectie": "kennis", "regels": 1},
        ]}
        graaf = gg.bouw_knopen(manifest)
        paren = {(e["bron"], e["doel"]) for e in graaf["verbindingen"]}
        self.assertIn(("doc:inbox/a.md", "hub:inbox"), paren)
        self.assertIn(("doc:kennis/b.md", "hub:kennis"), paren)
        # hubs onderling verbonden met het centrum
        self.assertIn(("hub:inbox", "centrum"), paren)

    def test_alle_documenten_bereikbaar(self):
        manifest = {"documenten": [
            {"pad": f"s{i}/d{i}.md", "titel": f"D{i}", "sectie": f"s{i}", "regels": 1}
            for i in range(20)
        ]}
        graaf = gg.bouw_knopen(manifest)
        bereikbaar = set()
        grens = ["centrum"]
        while grens:
            n = grens.pop()
            if n in bereikbaar:
                continue
            bereikbaar.add(n)
            for e in graaf["verbindingen"]:
                if e["bron"] == n:
                    grens.append(e["doel"])
                elif e["doel"] == n:
                    grens.append(e["bron"])
        doc_ids = {k["id"] for k in graaf["knopen"]}
        self.assertTrue(doc_ids.issubset(bereikbaar), "niet elk document bereikbaar")

    def test_grootte_blijft_hanteerbaar(self):
        """438 documenten + hubs: het antwoord blijft compact (JSON < 1 MB)."""
        manifest = {"documenten": [
            {"pad": f"s{i%14}/d{i}.md", "titel": f"D{i}", "sectie": f"s{i%14}",
             "regels": 1} for i in range(438)]}
        graaf = gg.bouw_knopen(manifest)
        self.assertLess(len(json.dumps(graaf)), 1_000_000)
        # 438 documenten + 14 hubs + centrum + 6 functies
        self.assertEqual(len(graaf["knopen"]), 438 + 14 + 1 + 6)


if __name__ == "__main__":
    unittest.main()
