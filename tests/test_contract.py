"""Fase 3 — tests voor het taak-contract: de zes Automatiek-bouwblokken.

Bewijsvruchten:
- een taak kan als compleet contract worden opgesteld (6 blokken)
- doel + verificatie zijn verplicht; de rest mag (nog) leeg zijn
- secrets-scanner: een taak met een key/token/wachtwoord wordt GEWEIGERD —
  authenticatie hoort op de doelmachine, nooit in het plan (Automatiek-regel)
- markdown-export is leesbaar en bevat de blokken
- de verstuurde taak draagt het contract mee
"""
import json
import tempfile
import unittest
from pathlib import Path

from kern import growkit_contract as gc


class TestTaakContract(unittest.TestCase):
    def test_compleet_contract_met_zes_blokken(self):
        c = gc.maak(doel="Dagelijkse samenvatting in Telegram",
                    bronnen="IMAP, Telegram Bot API",
                    stappen="1. lees mail 2. vat samen 3. verstuur",
                    verificatie="shell_check: telegram bevestigt aflevering",
                    planning="VPS, elke ochtend 07:00, faal → melding",
                    privacy="geen inhoud loggen, alleen koppen")
        self.assertTrue(c["ok"])
        self.assertEqual(len(c["data"]["blokken"]), 6)

    def test_doel_en_verificatie_verplicht(self):
        r = gc.maak(doel="", verificatie="")
        self.assertFalse(r["ok"])
        self.assertIn("doel", r["fout"].lower())
        r2 = gc.maak(doel="x", verificatie="")
        self.assertFalse(r2["ok"])
        self.assertIn("verificatie", r2["fout"].lower())

    def test_secrets_worden_geweigerd(self):
        voorbeelden = [
            ("doel", "gebruik key sk-ant-api03-abcdef1234567890abcdef"),
            ("stappen", "wachtwoord=P@ssw0rd123 inloggen"),
            ("bronnen", "token ghp_ABCDEF1234567890abcdefABCDEF12 in header"),
            ("privacy", "API-key 8885940728:AAHAinEMmjQze44pl_aL7AvOEj5DUFY0Tic"),
        ]
        for veld, waarde in voorbeelden:
            kwargs = {"doel": "x", "verificatie": "y"}
            kwargs[veld] = waarde
            r = gc.maak(**kwargs)
            self.assertFalse(r["ok"], f"{veld} werd toegelaten: {waarde}")
            self.assertIn("secret", r["fout"].lower())

    def test_markdown_export_leesbaar(self):
        c = gc.maak(doel="Dagelijkse samenvatting",
                    verificatie="telegram bevestigt aflevering")
        md = gc.markdown(c["data"])
        self.assertIn("## 01", md)  # genummerde blokken
        self.assertIn("Dagelijkse samenvatting", md)
        self.assertIn("## 06", md)

    def test_verstuurde_taak_draagt_contract(self):
        """E2E-stijl: agenttaak met contract neemt de 6 blokken mee in de JSON."""
        from kern import growkit_agenttaak as at

        class NepSSH:
            def __init__(self): self.bestand = {}
            def __call__(self, cmd, stdin, timeout):
                self.bestand = json.loads(stdin or "{}")
                return 0, ""

        nep = NepSSH()
        c = gc.maak(doel="Check schijfruimte",
                    verificatie="df -h toont >10% vrij",
                    planning="VPS, eenmalig")
        self.assertTrue(c["ok"])
        r = at.verstuur("vigil", "taak-ctr-1", "Check schijfruimte",
                        contract=c["data"], uitvoerder=nep)
        self.assertTrue(r["ok"])
        self.assertIn("contract", nep.bestand)
        self.assertEqual(len(nep.bestand["contract"]["blokken"]), 6)


if __name__ == "__main__":
    unittest.main()
