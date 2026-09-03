import json
import tempfile
import unittest
from pathlib import Path

from kern.growkit_motor import voer_uit


def maak_profiel_met_mensstap(review="reviewer"):
    return {
        "profiel": "test",
        "stappen": [
            {
                "id": "stap-001",
                "commando": "echo OK",
                "verwacht": "OK verschijnt",
                "bewijs": {"type": "shell_check", "commando": "echo OK", "verwacht_substr": "OK"},
                "bij_falen": {"alternatief_commando": None, "anders": "roep_mens"},
                "idempotent": True,
            },
            {
                "id": "stap-002",
                "commando": "toon aan de mens",
                "verwacht": "mens bevestigt",
                "bewijs": {"type": "mens_verificatie"},
                "mens_nodig": {"type": "bevestiging", "instructie": "Bevestig de structuur."},
                "bij_falen": {"alternatief_commando": None, "anders": "roep_mens"},
                "idempotent": True,
                "review": review,
            },
            {
                "id": "stap-003",
                "commando": "echo NA",
                "verwacht": "NA verschijnt — bouwt voort op stap-002",
                "bewijs": {"type": "shell_check", "commando": "echo NA", "verwacht_substr": "NA"},
                "bij_falen": {"alternatief_commando": None, "anders": "roep_mens"},
                "idempotent": True,
            },
        ],
    }


CONFIG_GESLAAGD = {"rollen": {"reviewer": {"type": "cli", "commando": "echo geslaagd"}}}
CONFIG_ONDUIDELIJK = {"rollen": {"reviewer": {"type": "cli", "commando": "echo geen-idee"}}}


class TestMotorReview(unittest.TestCase):
    def _run(self, profiel, config):
        with tempfile.TemporaryDirectory() as d:
            doel = Path(d) / "plant"
            doel.mkdir()
            logboek = Path(d) / "logboek.json"
            logboek.write_text("[]", encoding="utf-8")
            ok = voer_uit(profiel, doel, logboek, None, reviewconfig=config)
            entries = json.loads(logboek.read_text(encoding="utf-8"))
            return ok, entries

    def test_reviewer_geslaagd_gaat_door(self):
        ok, entries = self._run(maak_profiel_met_mensstap(), CONFIG_GESLAAGD)
        # motor gaat door: alle 3 stappen zijn verwerkt, en het eindresultaat is True
        self.assertTrue(ok)
        stap2 = entries[1]
        self.assertEqual(stap2["status"], "review_ok_wacht_ratificatie")
        self.assertEqual(stap2["review_rol"], "reviewer")
        self.assertEqual(stap2["review_oordeel"], "geslaagd")
        # stap-003 is ná de ratificatie-status uitgevoerd (doorloop bewezen)
        self.assertEqual(entries[2]["stap"], "stap-003")
        self.assertEqual(entries[2]["status"], "geslaagd")

    def test_reviewer_onduidelijk_is_klassiek_mensmoment(self):
        ok, entries = self._run(maak_profiel_met_mensstap(), CONFIG_ONDUIDELIJK)
        stap2 = entries[1]
        self.assertEqual(stap2["status"], "wacht_op_mens")
        self.assertEqual(stap2["review_oordeel"], "onduidelijk")

    def test_geen_config_is_klassiek_mensmoment(self):
        ok, entries = self._run(maak_profiel_met_mensstap(), None)
        stap2 = entries[1]
        self.assertEqual(stap2["status"], "wacht_op_mens")
        self.assertNotIn("review_oordeel", stap2)

    def test_stap_zonder_reviewveld_onaangetast(self):
        ok, entries = self._run(maak_profiel_met_mensstap(review=None), CONFIG_GESLAAGD)
        stap2 = entries[1]
        self.assertEqual(stap2["status"], "wacht_op_mens")
        self.assertNotIn("review_oordeel", stap2)


if __name__ == "__main__":
    unittest.main()
