"""Tests voor growkit_besluiten — Slice B: besluiten-tijdlijn (voor de app).

Bron: besluiten.md — één regel per besluit:
  [BSL-xxx] Titel | status: <status> | dd-mm-jjjj | bron: inbox/<bestand>
De module parseert regels naar dicts (injecteerbare lezer, offline testbaar).
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from kern import growkit_besluiten as bl

VOORBEELD = """---
titel: "besluiten"
---

# Besluiten-register

[BSL-001] PLAN-EERST-regel | status: besloten | 08-09-2026 | bron: inbox/a.md
[BSL-002] Licentie MIT | status: besloten | 07-09-2026 | bron: inbox/b.md
geen besluit-regel
[BSL-038] TestLock actief | status: open | 10-09-2026 | bron: inbox/c.md
[BSL-002] Licentie MIT | status: herzien | 09-09-2026 | bron: inbox/b2.md
"""


class TestParseerRegel(unittest.TestCase):
    def test_geldige_regel(self):
        d = bl.parseer_regel("[BSL-001] Titel hier | status: besloten | 08-09-2026 | bron: inbox/a.md")
        self.assertEqual(d["id"], "BSL-001")
        self.assertEqual(d["titel"], "Titel hier")
        self.assertEqual(d["status"], "besloten")
        self.assertEqual(d["datum"], "08-09-2026")
        self.assertEqual(d["bron"], "inbox/a.md")

    def test_geen_regel_geeft_none(self):
        self.assertIsNone(bl.parseer_regel("gewone tekst"))
        self.assertIsNone(bl.parseer_regel(""))


class TestTijdlijn(unittest.TestCase):
    def test_nieuwste_eerst_op_datum(self):
        tijdlijn = bl.tijdlijn(VOORBEELD)
        self.assertEqual(tijdlijn[0]["id"], "BSL-038")  # 10-09
        self.assertEqual(tijdlijn[-1]["id"], "BSL-002")  # 07-09

    def test_herziene_versie_overschrijft_oudere_status(self):
        tijdlijn = bl.tijdlijn(VOORBEELD)
        bsl2 = [d for d in tijdlijn if d["id"] == "BSL-002"]
        # twee regels, nieuwste datum is leidend in de tijdlijn; herziene status blijft zichtbaar
        self.assertEqual(len(bsl2), 2)
        self.assertEqual(bsl2[0]["status"], "herzien")

    def test_status_filter(self):
        tijdlijn = bl.tijdlijn(VOORBEELD, status="besloten")
        self.assertTrue(all(d["status"] == "besloten" for d in tijdlijn))
        self.assertEqual(len(tijdlijn), 2)

    def test_frontmatter_en_koppen_overgeslagen(self):
        tijdlijn = bl.tijdlijn(VOORBEELD)
        self.assertTrue(all(d["id"].startswith("BSL-") for d in tijdlijn))


if __name__ == "__main__":
    unittest.main()
