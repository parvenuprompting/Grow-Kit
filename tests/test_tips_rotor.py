"""ZT-5 — tip-rotor: conditie-tips eerst, geen herhaling vandaag, geen
tips na 23:00, stilte 60 s na gebeurtenis-hero, [N]-placeholders uit
tellers, max 3 'volgende'-wissels per sessie.

Tijd en toeval zijn geïnjecteerd: geen slaap, geen flaky runs.
"""
import unittest
from datetime import datetime, timedelta

from kern import growkit_tips as tips

_NU = datetime(2026, 9, 10, 14, 0, 0)


def _tip(id_, tekst="Tip", conditie=None):
    return {"id": id_, "tekst": tekst, "scherm": "home", "knop": "OK",
            "conditie": conditie}


class VasteKeuze:
    """Injecteerbare 'random': kiest deterministisch de eerste optie."""

    def choice(self, seq):
        return seq[0]


class TestTipRotor(unittest.TestCase):
    def test_geen_tips_na_23u(self):
        self.assertIsNone(tips.kies_tip(
            [_tip("a")], nu=_NU.replace(hour=23, minute=30)))

    def test_stilte_binnen_60s_na_gebeurtenis_hero(self):
        gebeurtenis = _NU - timedelta(seconds=30)
        self.assertIsNone(tips.kies_tip(
            [_tip("a")], nu=_NU, gebeurtenis_op=gebeurtenis))
        # na 60 s mag er weer een tip
        self.assertEqual(tips.kies_tip(
            [_tip("a")], nu=_NU, gebeurtenis_op=_NU - timedelta(seconds=61)
        )["id"], "a")

    def test_laatst_getoond_vandaag_heeft_kans_nul(self):
        self.assertIsNone(tips.kies_tip(
            [_tip("a")], nu=_NU, laatst_getoond={"a": _NU.date()}))

    def test_conditie_tips_voOR_generieke(self):
        generiek = _tip("generiek")
        conditie = _tip("conditie", conditie={"veld": "planten", "min": 2})
        gekozen = tips.kies_tip(
            [generiek, conditie], nu=_NU, tellers={"planten": 3},
            keuze=VasteKeuze())
        self.assertEqual(gekozen["id"], "conditie")

    def test_conditie_niet_voldaan_valt_terug_op_generiek(self):
        generiek = _tip("generiek")
        conditie = _tip("conditie", conditie={"veld": "planten", "min": 5})
        gekozen = tips.kies_tip(
            [generiek, conditie], nu=_NU, tellers={"planten": 1},
            keuze=VasteKeuze())
        self.assertEqual(gekozen["id"], "generiek")

    def test_placeholder_N_uit_teller(self):
        tip = _tip("a", tekst="Je hebt [N] planten")
        gekozen = tips.kies_tip(
            [tip], nu=_NU, tellers={"planten": 7}, keuze=VasteKeuze())
        self.assertEqual(gekozen["tekst"], "Je hebt 7 planten")

    def test_max_drie_volgende_wissels(self):
        self.assertTrue(tips.mag_wisselen(0))
        self.assertTrue(tips.mag_wisselen(2))
        self.assertFalse(tips.mag_wisselen(3))
        self.assertFalse(tips.mag_wisselen(4))

    def test_lege_lijst_geen_crash(self):
        self.assertIsNone(tips.kies_tip([], nu=_NU))


if __name__ == "__main__":
    unittest.main()
