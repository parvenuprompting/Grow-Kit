"""Testen voor de verbeterde antwoord/redenatie-scheiding (bugfix 6 sept).

Geval uit de praktijk: het model zet soms zijn hele hardop-denken (incl.
Engelse meta-regels) ín de output en het échte antwoord aan het eind.
Vóór de fix: antwoord = ruwe lap (EN+NL door elkaar), redenatie = klein
staartje. Na de fix: antwoord = het Nederlandse eindblok, redenatie =
alles ervoor.
"""
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from kern.growkit_agentchat import zuiver_antwoord, redenatie_uit, splits_antwoord_redenatie


RUW = (
    "The user (Tiëndo) says: \"Nieuwe poller test: zeg hallo en denk hardop kort\" — a new\n"
    " poller test: say hello and think out loud briefly.\n"
    "This is a direct message to me (CLI), not the Telegram group. It's a test. I should\n"
    " respond briefly in Dutch, say hallo, and \"think out loud\" briefly — meaning a short\n"
    " reflection. Keep it short and concrete per preferences.\n"
    "No skill needed really — agent-brain-curation is for bookings/commits in the agent\n"
    "-brain repo, not relevant here. This is just a test ping.\n"
    "Let me just reply: hallo, short hardop-denken: this looks like a poller test via new\n"
    " delivery channel; I received it in the CLI session; nothing to curate; standing by\n"
    ".\n"
    "Keep it kort.\n"
    "Hallo Tiëndo.\n"
    "Hardop, kort:\n"
    "1. Dit lijkt een test van een nieuwe poller-levering — bericht komt binnen als directe instructie in mijn CLI-sessie.\n"
    "2. Niets te cureren, niets te boeken in het brein; dit is puur bereikbaarheid.\n"
    "3. Zenders staan aan: ik reageer, dus de pijplijn werkt.\n"
    "Klaar voor de volgende test."
)


class TestSplits(unittest.TestCase):
    def test_splits_scheidt_en_denk_van_nl_antwoord(self):
        red, antw = splits_antwoord_redenatie(RUW)
        self.assertIn("The user", red)            # Engelse meta-regels → redenatie
        self.assertIn("Let me just reply", red)
        self.assertIn("Hallo Tiëndo.", antw)      # Nederlandse eindtekst → antwoord
        self.assertIn("Klaar voor de volgende test.", antw)
        self.assertNotIn("The user", antw)        # geen Engelse meta in het antwoord

    def test_zuiver_gebruikt_de_splits(self):
        self.assertEqual(zuiver_antwoord(RUW),
                         splits_antwoord_redenatie(RUW)[1])

    def test_redenatie_gebruikt_de_splits(self):
        self.assertEqual(redenatie_uit(RUW),
                         splits_antwoord_redenatie(RUW)[0])

    def test_puur_nederlands_blijft_intact(self):
        tekst = "Hallo Tiëndo. Alles draait."
        red, antw = splits_antwoord_redenatie(tekst)
        self.assertIsNone(red)
        self.assertEqual(antw, tekst)

    def test_box_uitvoer_werkt_nog_steeds(self):
        rauw = ("╭─ ☤ Hermes ──╮\nDenkwerk.\n╰──────────────╯\nPuur antwoord.\n"
                "Resume this session with:\n  hermes --resume x")
        red, antw = splits_antwoord_redenatie(rauw)
        self.assertEqual(antw, "Puur antwoord.")
        self.assertEqual(red, "Denkwerk.")

    def test_geen_en_markers_geen_crash(self):
        red, antw = splits_antwoord_redenatie("")
        self.assertIsNone(red)
        self.assertEqual(antw, "")


if __name__ == "__main__":
    unittest.main()
