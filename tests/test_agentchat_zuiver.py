"""Testen voor zuiver_antwoord — Hermes CLI-meuk uit agentantwoorden.

Aanleiding 6 sept: de poller slaatte de ruwe terminal-uitvoer op
(query-echo, init-regels, ☤ Hermes-box, resume-commando's, sessie-stats).
De draad toonde toen één grote terminal in plaats van het antwoord.
"""
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from kern.growkit_agentchat import zuiver_antwoord


class TestZuiverAntwoord(unittest.TestCase):
    """Het pure antwoord overleeft, de CLI-meuk niet."""

    def test_box_met_hermes_header(self):
        rauw = (
            "Query: Hallo?\n"
            "Initializing agent...\n"
            "╭─ ☤ Hermes ───────────────╮\n"
            "Hé Tiëndo. Codex hier.\n"
            "╰──────────────────────────╯\n"
        )
        self.assertEqual(zuiver_antwoord(rauw), "Hé Tiëndo. Codex hier.")

    def test_box_met_meerregelig_antwoord(self):
        rauw = (
            "╭─ ☤ Hermes ─────╮\n"
            "Eerste regel.\n"
            "Tweede regel.\n"
            "╰────────────────╯\n"
            "Resume this session with:\n"
            "  hermes --resume 123 -p codex\n"
        )
        self.assertEqual(zuiver_antwoord(rauw), "Eerste regel.\nTweede regel.")

    def test_zonder_box_maar_met_sessie_stats(self):
        rauw = (
            "Query: test\n"
            "Initializing agent...\n"
            "Prima, draait.\n"
            "Resume this session with:\n"
            "  hermes --resume abc -p kairos\n"
            "Session: abc\n"
            "Duration: 20s\n"
            "Messages: 2 (1 user, 0 tool calls)\n"
        )
        self.assertEqual(zuiver_antwoord(rauw), "Prima, draait.")

    def test_pure_tekst_blijft_onaangetast(self):
        self.assertEqual(zuiver_antwoord("Gewoon een antwoord."), "Gewoon een antwoord.")

    def test_leeg_blijft_leeg(self):
        self.assertEqual(zuiver_antwoord(""), "")

    def test_geen_hermes_in_resultaat(self):
        rauw = "╭─ ☤ Hermes ──╮\nHalloor.\n╰─────────────╯\nhermes --resume x"
        resultaat = zuiver_antwoord(rauw)
        self.assertNotIn("Hermes", resultaat)
        self.assertNotIn("hermes", resultaat)


if __name__ == "__main__":
    unittest.main()
