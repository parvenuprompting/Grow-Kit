"""Testen voor de Amnesia-kern (kern/growkit_amnesia.py).

Inbouw van Amnesia Protocol Lite (parvenuprompting/amnesia-protocol-lite)
als GrowKit-kernmodule: lokale detectoren, menselijke review (accepteren /
negeren / aanpassen), typegebonden markers (EMAIL_1) en een synthetische
tweede laag met fictieve waarden. Alles lokaal, stdlib-only.

Kernprincipes die hier verankerd worden:
- Dezelfde waarde krijgt binnen één sessie altijd hetzelfde token.
- Laag 2 ziet alleen markers, nooit de bronwaarden.
- Review beslist: niets wordt automatisch vervangen.
- Overlapresolutie: hoogste vertrouwen wint, anders langste match.
"""
import unittest

from kern import growkit_amnesia as am


class TestDetectoren(unittest.TestCase):
    def test_email_wordt_gevonden(self):
        v = am.detecteer("Mail jansen@voorbeeld.nl even")
        email = [x for x in v if x["type"] == "email"]
        self.assertEqual(len(email), 1)
        self.assertEqual(email[0]["waarde"], "jansen@voorbeeld.nl")

    def test_telefoon_mobiel_nl(self):
        v = am.detecteer("Bel 0612345678 of 06 - 12345678")
        types = {x["type"] for x in v}
        self.assertIn("telefoon", types)

    def test_iban_met_mod97(self):
        # geldig test-IBAN (mod-97 = 1)
        v = am.detecteer("Rekening NL91ABNA0417164300 sluiten")
        iban = [x for x in v if x["type"] == "iban"]
        self.assertEqual(len(iban), 1)

    def test_ongeldig_iban_krijgt_lage_zekerheid(self):
        v = am.detecteer("NL00ABNA0000000000")
        iban = [x for x in v if x["type"] == "iban"]
        if iban:
            self.assertLess(iban[0]["zekerheid"], 0.5)

    def test_bsn_elfproef_geldig(self):
        v = am.detecteer("BSN 111222333")
        bsn = [x for x in v if x["type"] == "bsn"]
        self.assertEqual(len(bsn), 1)

    def test_bsn_elfproef_ongeldig_geweigerd(self):
        v = am.detecteer("nummer 123456789")
        bsn = [x for x in v if x["type"] == "bsn"]
        if bsn:
            self.assertLess(bsn[0]["zekerheid"], 0.5)

    def test_context_klantnummer(self):
        v = am.detecteer("klantnummer: 883746")
        klant = [x for x in v if x["type"] == "klantnummer"]
        self.assertEqual(len(klant), 1)
        self.assertEqual(klant[0]["waarde"], "883746")

    def test_context_api_key(self):
        v = am.detecteer("password = supergeheim123")
        geheim = [x for x in v if x["type"] == "geheim"]
        self.assertEqual(len(geheim), 1)
        self.assertEqual(geheim[0]["waarde"], "supergeheim123")

    def test_link_wordt_gevonden(self):
        v = am.detecteer("zie https://voorbeeld.nl/pagina voor info")
        link = [x for x in v if x["type"] == "link"]
        self.assertEqual(len(link), 1)

    def test_adres_met_straatnaam(self):
        v = am.detecteer("woning op Dorpsstraat 42 in Utrecht")
        adr = [x for x in v if x["type"] == "adres"]
        self.assertTrue(adr)

    def test_overlap_hoogste_zekerheid_wint(self):
        # 'klantnummer: 883746' — de context-match (0.98) moet winnen van
        # een eventueel breder/beneerbaar patroon op hetzelfde stuk tekst.
        v = am.detecteer("klantnummer: 883746")
        klant = [x for x in v if x["waarde"] == "883746"]
        self.assertEqual(len(klant), 1)
        self.assertEqual(klant[0]["type"], "klantnummer")

    def test_te_grote_tekst_wordt_geweigerd(self):
        with self.assertRaises(ValueError):
            am.detecteer("x" * (am.MAX_INVOER_LENGTE + 1))


class TestTerminalDetectie(unittest.TestCase):
    def test_jwt_wordt_gevonden(self):
        tekst = ("token eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0."
                 "SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJVadQssw5c")
        v = am.detecteer_terminal(tekst)
        self.assertIn("jwt", {x["type"] for x in v})

    def test_aws_key(self):
        v = am.detecteer_terminal("key AKIAIOSFODNN7EXAMPLE")
        self.assertIn("apikey", {x["type"] for x in v})

    def test_github_token(self):
        v = am.detecteer_token("ghp_" + "a" * 36)
        self.assertIn("apikey", {x["type"] for x in v})

    def test_private_key_blok(self):
        tekst = ("-----BEGIN RSA PRIVATE KEY-----\nMIIEow...\n"
                 "-----END RSA PRIVATE KEY-----")
        v = am.detecteer_terminal(tekst)
        self.assertIn("privatekey", {x["type"] for x in v})

    def test_git_remote_met_credentials(self):
        v = am.detecteer_terminal("git@github.com:org/geheim-repo.git")
        self.assertIn("gitremote", {x["type"] for x in v})

    def test_credential_url(self):
        v = am.detecteer_terminal("postgres://user:pw@host:5432/db")
        self.assertIn("credentialurl", {x["type"] for x in v})

    def test_accountpad(self):
        v = am.detecteer_terminal("log in /Users/tiendo/verborgen-map")
        self.assertIn("account", {x["type"] for x in v})


class TestMarkering(unittest.TestCase):
    """Markers: zelfde waarde = zelfde token binnen de sessie."""

    def test_geaccepteerde_waarden_krijgen_tokens(self):
        v = am.detecteer("Mail jansen@voorbeeld.nl, mail pieter@voorbeeld.nl")
        goedgekeurd = [{**x, "besluit": "geaccepteerd"}
                       for x in v if x["type"] == "email"]
        tokens = am.bouw_markers(goedgekeurd)
        zelf = am.veilige_tekst(
            "Mail jansen@voorbeeld.nl, mail pieter@voorbeeld.nl", goedgekeurd, tokens)
        self.assertNotIn("jansen@", zelf)
        self.assertIn("EMAIL_1", zelf)
        self.assertIn("EMAIL_2", zelf)

    def test_zelfde_waarde_krijgt_zelfde_token(self):
        tekst = "mail jansen@voorbeeld.nl en nog eens jansen@voorbeeld.nl"
        v = [{**x, "besluit": "geaccepteerd"}
             for x in am.detecteer(tekst) if x["type"] == "email"]
        tokens = am.bouw_markers(v)
        zelf = am.veilige_tekst(tekst, v, tokens)
        self.assertEqual(zelf.count("EMAIL_1"), 2)

    def test_genegeerde_waarden_blijven_staan(self):
        tekst = "mail jansen@voorbeeld.nl"
        v = am.detecteer(tekst)
        genegeerd = [{**x, "besluit": "genegeerd"} for x in v]
        tokens = am.bouw_markers(genegeerd)
        zelf = am.veilige_tekst(tekst, genegeerd, tokens)
        self.assertIn("jansen@voorbeeld.nl", zelf)

    def test_aangepaste_waarde_gebruikt_de_nieuwe_waarde(self):
        tekst = "klantnummer: 883746"
        v = am.detecteer(tekst)
        aangepast = [{**x, "besluit": "aangepast", "waarde": "447291"} for x in v]
        tokens = am.bouw_markers(aangepast)
        zelf = am.veilige_tekst(tekst, aangepast, tokens)
        self.assertIn("CUSTOMER_1", zelf)
        self.assertNotIn("883746", zelf)


class TestSynthetischeLaag(unittest.TestCase):
    """Laag 2 ziet alleen markers en maakt er fictieve waarden van."""

    def test_marker_wordt_gparsed(self):
        v = am.parse_markers("Contact EMAIL_1 en CUSTOMER_1")
        self.assertEqual(len(v), 2)
        types = {x["type"] for x in v}
        self.assertIn("email", types)
        self.assertIn("klantnummer", types)

    def test_synthetic_email_is_echt_een_email(self):
        vervanging = am.synthetische_waarde("email", "EMAIL_1", zaad=42)
        self.assertIn("@", vervanging)

    def test_synthetic_klantnummer_is_cijfers(self):
        vervanging = am.synthetische_waarde("klantnummer", "CUSTOMER_1", zaad=42)
        self.assertTrue(vervanging.isdigit())

    def test_zelfde_zaad_geeft_zelfde_uitkomst(self):
        a = am.synthetische_waarde("email", "EMAIL_1", zaad=7)
        b = am.synthetische_waarde("email", "EMAIL_1", zaad=7)
        self.assertEqual(a, b)

    def test_synthetic_tekst_vervangt_alle_markers(self):
        veilig = "Mail EMAIL_1 over klant CUSTOMER_1"
        mark = am.parse_markers(veilig)
        kaart = am.bouw_synthetische_map(mark, zaad=42)
        resultaat = am.vervang_markers(veilig, kaart)
        self.assertNotIn("EMAIL_1", resultaat)
        self.assertNotIn("CUSTOMER_1", resultaat)
        self.assertIn("@", resultaat)


class TestSessiegebondenMapping(unittest.TestCase):
    """Mapping leeft in de sessie; elke nieuwe sessie start leeg."""

    def test_nieuwe_sessie_andere_synthetic(self):
        """Tokennamen (EMAIL_1) zijn stabiel; wat per sessie verandert is
        de synthetische invulling in laag 2 (mapping sessiegebonden)."""
        veilig = "mail EMAIL_1"
        m1 = am.bouw_synthetische_map(am.parse_markers(veilig), zaad=1)
        m2 = am.bouw_synthetische_map(am.parse_markers(veilig), zaad=2)
        self.assertNotEqual(m1["EMAIL_1"], m2["EMAIL_1"])


if __name__ == "__main__":
    unittest.main()
