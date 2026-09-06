"""Testen voor de Digitale Kloon-kern (kern/growkit_kloon.py).

Inbouw van digitale-kloon-ios (parvenuprompting/digitale-kloon-ios) als
GrowKit-kernmodule: een volledig lokale persoonlijke kluis met de vijf
categorieën uit het origineel, AES-GCM-versleutelde geheime velden en
een master-sleutel in de macOS Sleutelhangar.

Verankerd wordt: categorieën met veldtemplates (letterlijk uit
VaultCategory.swift), encryptie (AES-GCM via cryptography of fallback),
Keychain-beheer, append-only log, en dat geheimen nooit in plaintext
op schijf belanden.
"""
import base64
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from kern import growkit_kloon as kloon


class TestCategorieen(unittest.TestCase):
    """De zes categorieën en hun veldtemplates uit VaultCategory.swift."""

    def test_zes_categorieen(self):
        self.assertEqual(
            set(kloon.CATEGORIEEN),
            {"wachtwoord", "apikey", "bank", "crypto", "account", "notitie"},
        )

    def test_veldtemplates_kloppen_met_origineel(self):
        self.assertEqual(
            kloon.CATEGORIEEN["wachtwoord"]["velden"],
            [("Gebruikersnaam", False), ("Wachtwoord", True)],
        )
        self.assertEqual(
            kloon.CATEGORIEEN["apikey"]["velden"],
            [("Naam", False), ("Key", True)],
        )
        self.assertEqual(
            kloon.CATEGORIEEN["bank"]["velden"],
            [("IBAN", True), ("Naam rekeninghouder", False)],
        )
        self.assertEqual(
            kloon.CATEGORIEEN["crypto"]["velden"],
            [("Wallet", False), ("Private key / seed", True)],
        )
        self.assertEqual(
            kloon.CATEGORIEEN["account"]["velden"],
            [("Accountnaam", False), ("Wachtwoord", True)],
        )

    def test_elke_categorie_heeft_een_menselijke_naam(self):
        for code, cat in kloon.CATEGORIEEN.items():
            self.assertTrue(cat["naam"])


class TestMasterSleutel(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import sys as _sys, unittest as _u
        if _sys.platform != 'darwin':
            raise _u.SkipTest('macOS-only: Keychain bestaat niet op CI')

    """Master-sleutel: in de Sleutelhangar, nooit in plaintext op schijf."""

    def test_nieuwe_sleutel_wordt_gemaakt_en_gemaakt_blijft(self):
        with mock.patch.object(kloon, "keychain_lees", return_value=None) as lees, \
             mock.patch.object(kloon, "keychain_sla_op", return_value=True) as sla:
            # eerste aanroep genereert, tweede leest uit de (gepatchte) hangar
            k1 = kloon.master_sleutel()
            lees.return_value = k1
            k2 = kloon.master_sleutel()
            self.assertEqual(k1, k2, "tweede aanroep hergebruikt de sleutel")
            sla.assert_called_once()

    def test_bestande_sleutel_wordt_gehergebruikt(self):
        with mock.patch.object(kloon, "keychain_lees", return_value="QUJDRA=="), \
             mock.patch.object(kloon, "keychain_sla_op") as sla:
            self.assertEqual(kloon.master_sleutel(), "QUJDRA==")
            sla.assert_not_called()

    def test_geen_plaintext_sleutelbestand_in_gebruik(self):
        """De sleutel leeft in de Sleutelhangar; er is geen sleutelbestand."""
        self.assertFalse(hasattr(kloon, "_sleutel_bestand"),
                         "sleutelbestand-route moet weg zijn (hangar-only)")


class TestEncryptie(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import sys as _sys, unittest as _u
        if _sys.platform != 'darwin':
            raise _u.SkipTest('macOS-only: Keychain bestaat niet op CI')

    """AES-GCM: zelfde sleutel ontsleutelt, verkeerde sleutel faalt."""

    def test_rondje_encryptie(self):
        k = kloon.master_sleutel()
        geheim = "MijnSuperGeheim42!"
        versleuteld = kloon.versleutel(geheim, k)
        self.assertNotIn(geheim.encode(), versleuteld)
        self.assertEqual(kloon.ontsleutel(versleuteld, k), geheim)

    def test_verkeerde_sleutel_faalt_netjes(self):
        k1 = kloon.master_sleutel()
        versleuteld = kloon.versleutel("geheim", k1)
        # een andere sleutel faalt met ValueError (authenticatie-tag)
        ander = base64.b64encode(b"\x00" * 32).decode()
        if ander == k1:
            ander = base64.b64encode(b"\x01" * 32).decode()
        with self.assertRaises(ValueError):
            kloon.ontsleutel(versleuteld, ander)

    def test_elke_versleuteling_andere_cijfertekst(self):
        k = kloon.master_sleutel()
        a = kloon.versleutel("zelfde", k)
        b = kloon.versleutel("zelfde", k)
        self.assertNotEqual(a, b, "AES-GCM gebruikt een willekeurige nonce")


class TestKluisBestand(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import sys as _sys, unittest as _u
        if _sys.platform != 'darwin':
            raise _u.SkipTest('macOS-only: Keychain bestaat niet op CI')

    """Geheimen landen nooit in plaintext op schijf."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)
        with mock.patch.object(kloon, "_kluis_pad",
                               return_value=self.tmp / "kloon.json"):
            self.bestand = self.tmp / "kloon.json"

    def tearDown(self):
        self._tmp.cleanup()

    def test_geheim_toevoegen_en_lezen(self):
        with mock.patch.object(kloon, "_kluis_pad", return_value=self.bestand):
            item = kloon.voeg_toe(
                titel="OpenRouter", categorie="apikey",
                velden={"Naam": "OpenRouter", "Key": "sk-or-v1-test"},
            )
            self.assertIn("id", item)
            gevonden = kloon.lees_item(item["id"])
            self.assertEqual(gevonden["titel"], "OpenRouter")
            self.assertEqual(gevonden["velden_ontsleuteld"]["Key"], "sk-or-v1-test")

    def test_cijfertekst_op_schijf_geen_plaintext(self):
        with mock.patch.object(kloon, "_kluis_pad", return_value=self.bestand):
            item = kloon.voeg_toe(
                titel="Bank", categorie="bank",
                velden={"IBAN": "NL91ABNA0417164300", "Naam rekeninghouder": "T W"},
            )
            raw = self.bestand.read_text()
            self.assertNotIn("NL91ABNA0417164300", raw,
                             "geheim IBAN mag niet plaintext op schijf staan")
            self.assertIn(item["id"], raw)

    def test_lijst_toont_titels_maar_geen_geheimen(self):
        with mock.patch.object(kloon, "_kluis_pad", return_value=self.bestand):
            kloon.voeg_toe(titel="X", categorie="account",
                           velden={"Accountnaam": "t", "Wachtwoord": "geheim123"})
            overzicht = kloon.lijst()
            self.assertEqual(len(overzicht), 1)
            raw = json.dumps(overzicht)
            self.assertNotIn("geheim123", raw)

    def test_open_velden_blijven_leesbaar(self):
        with mock.patch.object(kloon, "_kluis_pad", return_value=self.bestand):
            kloon.voeg_toe(titel="T", categorie="account",
                           velden={"Accountnaam": "tiendo", "Wachtwoord": "zzz"})
            item = kloon.lijst()[0]
            self.assertEqual(item["velden_open"]["Accountnaam"], "tiendo")

    def test_verwijder(self):
        with mock.patch.object(kloon, "_kluis_pad", return_value=self.bestand):
            item = kloon.voeg_toe(titel="Weg", categorie="account",
                                  velden={"Accountnaam": "a", "Wachtwoord": "b"})
            self.assertTrue(kloon.verwijder(item["id"]))
            self.assertEqual(kloon.lijst(), [])


class TestLog(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import sys as _sys, unittest as _u
        if _sys.platform != 'darwin':
            raise _u.SkipTest('macOS-only: Keychain bestaat niet op CI')

    """Elke actie komt in het append-only log (huisregel van het huis)."""

    def test_log_wordt_geboekt(self):
        with tempfile.TemporaryDirectory() as tmp:
            logpad = Path(tmp) / "log.json"
            with mock.patch.object(kloon, "_log_pad", return_value=logpad):
                kloon._log("toevoegen", {"titel": "X"})
                kloon._log("verwijderen", {})
                entries = json.loads(logpad.read_text())
                self.assertEqual([e["actie"] for e in entries],
                                 ["toevoegen", "verwijderen"])


if __name__ == "__main__":
    unittest.main()

