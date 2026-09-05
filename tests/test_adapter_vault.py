"""Adapter-tests voor de Secure Vault-commando's.

De adapter is bedienaar, geen machthebber: deze tests verankeren dat de
kluis-commando's bestaan, hun verplichte velden afdwingen en nette
fouten geven (geen tracebacks). De echte hdiutil-integratie bewijst de
E2E op macOS.
"""
import json
import subprocess
import sys
import unittest
from unittest import mock
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

import adapter  # noqa: E402
from kern import growkit_vault as vault  # noqa: E402


def _roep(commando: str, invoer: dict) -> dict:
    """Roep een adapter-commando rechtstreeks aan (in-process)."""
    return adapter.COMMANDOS[commando](invoer)


class TestVaultCommandosBestaan(unittest.TestCase):
    def test_vijf_commandos_geregistreerd(self):
        for naam in ("vaultvormen", "vaultlijst", "vaultmaak",
                     "vaultopen", "vaultsluit"):
            self.assertIn(naam, adapter.COMMANDOS)


class TestVaultVormen(unittest.TestCase):
    def test_geeft_drie_vormen(self):
        uit = _roep("vaultvormen", {})
        self.assertTrue(uit["ok"])
        self.assertEqual(set(uit["data"]["vormen"]), {"UDZO", "UDRW", "UDSB"})


class TestVaultLijst(unittest.TestCase):
    def test_geeft_kluizen_en_open_mounts(self):
        with mock.patch.object(vault, "zoek_kluizen",
                               return_value=["/a/x.dmg"]), \
             mock.patch.object(vault, "open_kluizen",
                               return_value=["/Volumes/x"]):
            uit = _roep("vaultlijst", {})
        self.assertTrue(uit["ok"])
        self.assertEqual(uit["data"]["kluizen"], ["/a/x.dmg"])
        self.assertEqual(uit["data"]["open"], ["/Volumes/x"])


class TestVaultMaak(unittest.TestCase):
    def test_ontbrekend_veld_geeft_nette_fout(self):
        with self.assertRaises(adapter.AdapterFout) as ctx:
            _roep("vaultmaak", {"bron": "/x"})
        self.assertIn("doelmap", str(ctx.exception))

    def test_succes_geeft_kluispad(self):
        with mock.patch.object(vault, "maak_kluis",
                               return_value=(True, "/pad/kluis.dmg")) as nep:
            uit = _roep("vaultmaak", {
                "bron": "/bron", "doelmap": "/doel", "naam": "kluis",
                "wachtwoord": "Kluis!2026#Sterk", "vorm": "UDZO",
            })
        self.assertTrue(uit["ok"])
        self.assertEqual(uit["data"]["kluis"], "/pad/kluis.dmg")
        # overschrijven nooit standaard aan
        self.assertFalse(nep.call_args.kwargs["overschrijven"])

    def test_fout_landt_als_adapterfout(self):
        with mock.patch.object(vault, "maak_kluis",
                               return_value=(False, "bestaat al")):
            with self.assertRaises(adapter.AdapterFout):
                _roep("vaultmaak", {
                    "bron": "/bron", "doelmap": "/doel", "naam": "kluis",
                    "wachtwoord": "Kluis!2026#Sterk",
                })


class TestVaultOpenSluit(unittest.TestCase):
    def test_open_zonder_wachtwoord_en_zonder_keychain_weigert(self):
        with self.assertRaises(adapter.AdapterFout) as ctx:
            _roep("vaultopen", {"kluis": "/pad/x.dmg"})
        self.assertIn("wachtwoord", str(ctx.exception))

    def test_open_via_keychain_leest_sleutelhangar(self):
        with mock.patch.object(vault, "keychain_lees",
                               return_value="uit-de-hangar"), \
             mock.patch.object(vault, "open_kluis",
                               return_value=(True, "/Volumes/x")) as nep:
            uit = _roep("vaultopen", {"kluis": "/pad/x.dmg", "keychain": True})
        self.assertTrue(uit["ok"])
        self.assertEqual(nep.call_args[0][1], "uit-de-hangar")

    def test_open_keychain_leeg_geeft_nette_fout(self):
        with mock.patch.object(vault, "keychain_lees", return_value=None):
            with self.assertRaises(adapter.AdapterFout) as ctx:
                _roep("vaultopen", {"kluis": "/pad/x.dmg", "keychain": True})
        self.assertIn("Sleutelhangar", str(ctx.exception))

    def test_sluit_alles_geeft_lijst_terug(self):
        with mock.patch.object(vault, "open_kluizen",
                               return_value=["/Volumes/a", "/Volumes/b"]), \
             mock.patch.object(vault, "sluit_kluis",
                               side_effect=lambda m: m == "/Volumes/a"):
            uit = _roep("vaultsluit", {"alles": True})
        self.assertEqual(uit["data"]["gesloten"], ["/Volumes/a"])

    def test_sluit_zonder_mount_weigert(self):
        with self.assertRaises(adapter.AdapterFout):
            _roep("vaultsluit", {})


if __name__ == "__main__":
    unittest.main()
