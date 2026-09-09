"""Tests voor growkit_besluitenzaal — Slice: besluitenzaal-kamer (optie C, KairOS 9 sept).

Rendert de 'wacht op de Baas'-kamer uit register + voorstellen-wachtrij:
- ONBEVESTIGD/open besluiten uit besluiten-index.md (sectie na de ONBEVESTIGD-kop)
- voorstellen-wachtrij: *.md met max 3 opties + 1 aanbeveling
- HTML-output in fabriek-huisstijl, kamervolgorde: wacht-op-baas → register → hartslag (aanroeper beslist)
Offline: alle bronnen als tekst/lijst binnen, geen bestands-I/O in de kern.
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from kern import growkit_besluitenzaal as bz

INDEX_TEKST = """---
titel: "besluiten index"
---

BEVESTIGD:
  [BSL-001] PLAN-EERST-regel | 08-09
  [BSL-002] Licentie MIT | 07-09

ONBEVESTIGD (gemeld, nog niet gecureerd — NIET als groen licht; vraag de Baas):
  [BSL-099] Testbesluit wacht | 09-09
"""

VOORSTEL_TEKST = """# Titel van voorstel
Geadviseerd door: KairOS
Optie A: doe dit
Optie B: laat het
Aanbeveling: A"""


class TestOnbevestigdUitIndex(unittest.TestCase):
    def test_pakt_regels_onder_onbevestigd_kop(self):
        wacht = bz.onbevestigd_uit_index(INDEX_TEKST)
        self.assertEqual(len(wacht), 1)
        self.assertIn("BSL-099", wacht[0])

    def test_bevestigd_blijft_buiten_wacht(self):
        wacht = bz.onbevestigd_uit_index(INDEX_TEKST)
        self.assertFalse(any("BSL-001" in r for r in wacht))

    def test_leeg_register_geen_wacht(self):
        self.assertEqual(bz.onbevestigd_uit_index("BEVESTIGD:\n  [BSL-001] x | 08-09"), [])


class TestVoorstelParsing(unittest.TestCase):
    def test_opties_en_aanbeveling_gepakt(self):
        v = bz.parseer_voorstel(VOORSTEL_TEKST, "2026-09-09-test.md")
        self.assertEqual(v["titel"], "Titel van voorstel")
        self.assertEqual(len(v["opties"]), 2)
        self.assertIn("A", v["aanbeveling"])

    def test_te_veel_opties_wordt_afgekeurd(self):
        tekst = VOORSTEL_TEKST + "\nOptie C: meer\nOptie D: te veel"
        v = bz.parseer_voorstel(tekst, "x.md")
        self.assertFalse(v["geldig"])  # max 3 opties is HARD

    def test_zonder_aanbeveling_ongeldig(self):
        tekst = "# T\nOptie A: x\nOptie B: y"
        v = bz.parseer_voorstel(tekst, "x.md")
        self.assertFalse(v["geldig"])


class TestRender(unittest.TestCase):
    def test_kamer_toont_wacht_en_register(self):
        html = bz.render(
            index_tekst=INDEX_TEKST,
            voorstellen=[bz.parseer_voorstel(VOORSTEL_TEKST, "x.md")],
            bevestigd=["[BSL-001] PLAN-EERST-regel | 08-09"],
        )
        self.assertIn("BSL-099", html)          # wacht op de Baas
        self.assertIn("Titel van voorstel", html)  # voorstellen-wachtrij
        self.assertIn("BSL-001", html)          # register eronder

    def test_leeg_wacht_geeft_rustige_staat(self):
        html = bz.render(index_tekst="", voorstellen=[], bevestigd=[])
        self.assertIn("niets wacht", html)

    def test_huisstijl_kleuren_aanwezig(self):
        html = bz.render(index_tekst=INDEX_TEKST, voorstellen=[], bevestigd=[])
        self.assertIn("#F4F1E9", html)  # papier
        self.assertIn("#19202C", html)  # inkt
        self.assertIn("#F2673F", html)  # oranje (wacht-op-baas accent)
        self.assertIn("#D9F65C", html)  # lime (register accent)


if __name__ == "__main__":
    unittest.main()
