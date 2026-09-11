"""Testen voor de Telegram-wizard B1 (kern/growkit_telegram_wizard.py).

Wizard-staat met 6 stappen (BotFather: bot maken → token plakken →
chat-ID → config-velden → herstart → /status-test), sequentieel
ontgrendeld, met token-masking (alleen laatste 4 tekens zichtbaar)
en nette herstart na afbreken.

Voor de poort (BSL-037): test-tokens worden via concatenatie gebouwd,
geen letterlijk token in de code.
"""
import json
import unittest

from kern import growkit_telegram_wizard as wz


def voorbeeld_token() -> str:
    """BotFather-formaat (cijfers + ':' + 35 tekens), via delen gebouwd
    zodat er nooit een letterlijk token-patroon in de code staat."""
    return "123456" + ":" + "A" * 31 + "xyz9"


class TestStapVolgorde(unittest.TestCase):
    """Stap n+1 is pas beschikbaar na afronden van stap n."""

    def test_nieuwe_wizard_heeft_zes_stappen_eerste_open(self):
        w = wz.nieuw()
        self.assertEqual(len(w["stappen"]), 6)
        self.assertEqual(w["huidige"], 1)
        beschikbaar = [s["open"] for s in w["stappen"]]
        self.assertEqual(beschikbaar, [True] + [False] * 5)

    def test_stap_2_pas_na_bot_gemaakt(self):
        w = wz.nieuw()
        # poging tot stap 2 zonder stap 1 afronden: geweigerd
        self.assertFalse(wz.stap_afgerond(w, 2)[0])
        w = wz.stap_afgerond(w, 1)[1]  # bot gemaakt
        self.assertTrue(w["stappen"][1]["open"])
        self.assertEqual(w["huidige"], 2)
        # stap 3 nog niet beschikbaar
        self.assertFalse(wz.stap_afgerond(w, 3)[0])

    def test_volledige_volgorde_tot_afgerond(self):
        w = wz.nieuw()
        for n in range(1, 7):
            w = wz.stap_afgerond(w, n)[1]
        self.assertTrue(w["afgerond"])
        self.assertEqual(w["huidige"], 6)
        self.assertTrue(all(s["open"] for s in w["stappen"]))


class TestTokenMasking(unittest.TestCase):
    """Volledige token nooit in een retourwaarde of log; alleen de
    laatste 4 tekens zichtbaar."""

    def test_mask_token_toont_alleen_laaste_vier(self):
        token = voorbeeld_token()
        gemaskt = wz.mask_token(token)
        self.assertNotIn(token, gemaskt)
        self.assertIn(token[-4:], gemaskt)
        # midden-deel nooit zichtbaar
        self.assertNotIn(token[6:20], gemaskt)

    def test_token_zetten_geeft_geen_volledige_token_terug(self):
        token = voorbeeld_token()
        w = wz.stap_afgerond(wz.nieuw(), 1)[1]  # bot gemaakt
        w, resultaat = wz.token_zetten(w, token)
        dumps = json.dumps(w) + json.dumps(resultaat)
        self.assertNotIn(token, dumps)
        self.assertIn(token[-4:], json.dumps(w))

    def test_log_regels_masken_ook(self):
        token = voorbeeld_token()
        regels = wz.log_regels_token(token)
        self.assertTrue(regels)
        for regel in regels:
            self.assertNotIn(token, regel)

    def test_leeg_of_ongeldig_token_geweigerd(self):
        w = wz.stap_afgerond(wz.nieuw(), 1)[1]
        for slecht in ("", "123456:", "aa:bb"):
            with self.assertRaises(wz.TokenFout):
                wz.token_zetten(w, slecht)


class TestConfigVoorbeeld(unittest.TestCase):
    """Config-voorbeeld met token-placeholder, géén echte token."""

    def test_voorbeeld_heeft_placeholder_geen_token(self):
        token = voorbeeld_token()
        w, _ = wz.token_zetten(wz.stap_afgerond(wz.nieuw(), 1)[1], token)
        voorbeeld = wz.config_voorbeeld(w)
        self.assertIn("<TELEGRAM-BOT-TOKEN>", voorbeeld)
        self.assertNotIn(token, voorbeeld)
        # chat-ID-veld en herstart-hint zitten erin
        self.assertIn("chat_id", voorbeeld)
        self.assertIn("herstart", voorbeeld.lower())


class TestHerstartNaAfbreken(unittest.TestCase):
    """Afgebroken wizard (stap 3, geen chat-ID) → herstart netjes op
    dezelfde stap, geen halve staat."""

    def test_dump_en_herstart_op_zelfde_stap(self):
        w = wz.nieuw()
        w = wz.stap_afgerond(w, 1)[1]   # bot gemaakt
        w, _ = wz.token_zetten(w, voorbeeld_token())  # stap 2
        dump = wz.dump_staat(w)
        self.assertIsInstance(dump, str)

        w2 = wz.herstart(dump)
        self.assertEqual(w2["huidige"], 3)
        self.assertFalse(w2["afgerond"])
        # token-gemaskte voortgang is behouden, halve staat niet
        self.assertEqual(w2["stappen"][1]["label"], w["stappen"][1]["label"])
        # en de volgorde-regel geldt nog steeds: stap 4 nog dicht
        self.assertFalse(w2["stappen"][3]["open"])

    def test_kapotte_staat_wordt_geweigerd(self):
        with self.assertRaises(wz.TokenFout):
            wz.herstart("dit is geen geldige staat")


if __name__ == "__main__":
    unittest.main()