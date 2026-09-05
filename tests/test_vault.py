"""Testen voor de Secure Vault-kern (kern/growkit_vault.py).

Inbouw van SecureVault v2 (parvenuprompting/secure-vault-v2) als
GrowKit-kernmodule. De encryptie doet macOS zelf: hdiutil (AES-256, APFS).
GrowKit is de hand, niet het slot. Geen externe libraries — stdlib-only,
zoals de rest van de kern.

Deze tests draaien ZONDER echte hdiutil-aanroepen: het proces wordt
geïnjecteerd (injectie-patroon), zodat de logica machine-onafhankelijk
testbaar is. De echte hdiutil-integratie bewijst de E2E op macOS.
"""
import unittest
from unittest import mock
from pathlib import Path

from kern import growkit_vault as vault


REPO = Path(__file__).resolve().parent.parent


def _fake_run(uitkomst: dict):
    """Maak een nep-subprocess.run die vault-informatie teruggeeft."""
    class _Result:
        def __init__(self):
            self.returncode = uitkomst.get("code", 0)
            self.stdout = uitkomst.get("stdout", "")
            self.stderr = uitkomst.get("stderr", "")

    return mock.patch.object(
        vault.subprocess, "run", return_value=_Result()
    )


class TestKluisVormen(unittest.TestCase):
    """De drie kluisvormen uit SecureVault v2 (UDZO, UDRW, UDSB)."""

    def test_drie_vormen_bestaan(self):
        vormen = vault.KLUIS_VORMEN
        self.assertEqual(
            set(vormen), {"UDZO", "UDRW", "UDSB"},
            "De drie vormen uit SecureVault: archief, lees/schrijf, meegroeiend",
        )

    def test_elke_vorm_heeft_menselijke_naam_en_omschrijving(self):
        for code, vorm in vault.KLUIS_VORMEN.items():
            self.assertIn("naam", vorm)
            self.assertIn("omschrijving", vorm)
            self.assertTrue(vorm["naam"])
            self.assertTrue(vorm["omschrijving"])

    def test_vorm_bepaalt_extentie(self):
        self.assertEqual(vault.extentie_voor("UDZO"), ".dmg")
        self.assertEqual(vault.extentie_voor("UDRW"), ".dmg")
        self.assertEqual(vault.extentie_voor("UDSB"), ".sparsebundle")
        with self.assertRaises(ValueError):
            vault.extentie_voor("VERKEERD")


class TestPadenEnNamen(unittest.TestCase):
    """Padvalidatie zoals validate_paths in SecureVault v2."""

    def test_bestaande_bronmap_wordt_geaccepteerd(self):
        bron = REPO / "kern"
        pad = vault.valideer_bron(str(bron))
        self.assertEqual(Path(pad).resolve(), bron.resolve())

    def test_ontbrekende_bronmap_wordt_geweigerd(self):
        with self.assertRaises(vault.KluisFout):
            vault.valideer_bron("/bestaat/niet/ooit")

    def test_bron_mag_geen_los_bestand_zijn(self):
        with self.assertRaises(vault.KluisFout):
            vault.valideer_bron(str(REPO / "README.md"))

    def test_doelmap_moet_bestaan(self):
        with self.assertRaises(vault.KluisFout):
            vault.valideer_doel("/bestaat/niet/ooit")

    def test_kluispad_komt_niet_stilletjes_overschrijven(self):
        # bestaande kluis + geen toestemming → fout (SecureVault-gedrag)
        with mock.patch.object(vault.os.path, "lexists", return_value=True):
            with self.assertRaises(vault.KluisFout):
                vault.controleer_overschrijven("/pad/kluis.dmg", toestaan=False)

    def test_overschrijven_met_expliciete_toestemming_mag(self):
        with mock.patch.object(vault.os.path, "lexists", return_value=True):
            self.assertTrue(
                vault.controleer_overschrijven("/pad/kluis.dmg", toestaan=True)
            )

    def test_geen_bestaande_kluis_is_prima(self):
        with mock.patch.object(vault.os.path, "lexists", return_value=False):
            self.assertFalse(
                vault.controleer_overschrijven("/pad/kluis.dmg", toestaan=False)
            )


class TestWachtwoordSterkte(unittest.TestCase):
    """Sterktemeter zoals check_password_strength in SecureVault v2."""

    def test_ontbrekend_wachtwoord_wordt_geweigerd(self):
        sterk, reden, score = vault.wachtwoord_sterkte("")
        self.assertFalse(sterk)

    def test_te_kort_wachtwoord_faalt(self):
        sterk, reden, score = vault.wachtwoord_sterkte("abc12")
        self.assertFalse(sterk)
        self.assertLess(score, vault.STERKTE_GOED)

    def test_sterk_wachtwoord_slaagt(self):
        sterk, reden, score = vault.wachtwoord_sterkte("Kluis!2026#SterkGenoot")
        self.assertTrue(sterk)
        self.assertGreaterEqual(score, vault.STERKTE_GOED)

    def test_generator_levert_bruikbaar_wachtwoord(self):
        pw = vault.genereer_wachtwoord(20)
        self.assertEqual(len(pw), 20)
        sterk, _, score = vault.wachtwoord_sterkte(pw)
        self.assertTrue(sterk)
        # twee aanroepen verschillen (willekeur)
        self.assertNotEqual(pw, vault.genereer_wachtwoord(20))


class TestKeychain(unittest.TestCase):
    """Sleutelhangar-opslag (security CLI), zoals SecureVault v2."""

    def test_sla_op_roept_security_aan(self):
        with _fake_run({}) as nep:
            ok = vault.keychain_sla_op("kluis.dmg", "wachtwoord123")
            self.assertTrue(ok)
            cmd = nep.call_args[0][0]
            self.assertEqual(cmd[0], "security")
            self.assertIn("add-generic-password", cmd)

    def test_lees_geeft_wachtwoord_terug(self):
        with _fake_run({"stdout": "geheim\n"}):
            self.assertEqual(vault.keychain_lees("kluis.dmg"), "geheim")

    def test_lees_zonder_item_geeft_geen_wachtwoord(self):
        with _fake_run({"code": 44, "stderr": "could not be found"}):
            self.assertIsNone(vault.keychain_lees("kluis.dmg"))

    def test_verwijder_geeft_ok_terug(self):
        with _fake_run({}):
            self.assertTrue(vault.keychain_verwijder("kluis.dmg"))


class TestKluisMaken(unittest.TestCase):
    """hdiutil create — AES-256, APFS, stdinpass (zoals SecureVault v2)."""

    def test_maken_roept_hdiutil_met_aes256_en_stdinpass(self):
        met_hdiutil = mock.patch.object(
            vault.subprocess, "run",
            return_value=type("R", (), {"returncode": 0, "stdout": "", "stderr": ""})(),
        )
        with met_hdiutil as nep:
            ok, pad = vault.maak_kluis(
                bron=str(REPO / "kern"),
                doelmap=str(REPO),
                naam="testkluis",
                wachtwoord="Kluis!2026#SterkGenoot",
                vorm="UDZO",
            )
            self.assertTrue(ok)
            self.assertTrue(pad.endswith("testkluis.dmg"))
            cmd = nep.call_args[0][0]
            self.assertEqual(cmd[0], "hdiutil")
            self.assertIn("create", cmd)
            self.assertIn("AES-256", cmd)
            self.assertIn("APFS", cmd)
            self.assertIn("-stdinpass", cmd)
            # het wachtwoord zit NIET in het commando (alleen via stdin)
            self.assertNotIn("Kluis!2026#SterkGenoot", cmd)

    def test_maken_met_zwak_wachtwoord_weigert(self):
        ok, bericht = vault.maak_kluis(
            bron=str(REPO / "kern"),
            doelmap=str(REPO),
            naam="testkluis",
            wachtwoord="abc",
            vorm="UDZO",
        )
        self.assertFalse(ok)
        self.assertIn("wachtwoord", bericht.lower())

    def test_maken_met_ontbrekende_bron_faalt_netjes(self):
        ok, bericht = vault.maak_kluis(
            bron="/bestaat/niet",
            doelmap=str(REPO),
            naam="testkluis",
            wachtwoord="Kluis!2026#SterkGenoot",
            vorm="UDZO",
        )
        self.assertFalse(ok)
        self.assertTrue(bericht)

    def test_maken_bestaand_pad_weigert_zonder_toestemming(self):
        with mock.patch.object(vault.os.path, "lexists", return_value=True):
            ok, bericht = vault.maak_kluis(
                bron=str(REPO / "kern"),
                doelmap=str(REPO),
                naam="testkluis",
                wachtwoord="Kluis!2026#SterkGenoot",
                vorm="UDZO",
                overschrijven=False,
            )
            self.assertFalse(ok)
            self.assertIn("bestaat", bericht.lower())


class TestKluisOpenEnDicht(unittest.TestCase):
    """mount/unmount via hdiutil attach/detach."""

    def test_open_roept_hdiutil_attach_met_stdinpass(self):
        with _fake_run({"stdout": "/dev/disk5s1\t/Volumes/kluis-x (APFS)\n"}) as nep:
            ok, mountpunt = vault.open_kluis("kluis.dmg", "wachtwoord")
            self.assertTrue(ok)
            self.assertIn("/Volumes/", mountpunt)
            cmd = nep.call_args[0][0]
            self.assertEqual(cmd[0], "hdiutil")
            self.assertIn("attach", cmd)
            self.assertNotIn("wachtwoord", cmd)

    def test_open_met_verkeerd_wachtwoord_geeft_bruikbaar_fout(self):
        with _fake_run({"code": 1, "stderr": "Authentication error"}):
            ok, bericht = vault.open_kluis("kluis.dmg", "verkeerd")
            self.assertFalse(ok)
            self.assertIn("wachtwoord", bericht.lower())

    def test_sluiten_roept_hdiutil_detach(self):
        with _fake_run({}) as nep:
            ok = vault.sluit_kluis("/Volumes/kluis-x")
            self.assertTrue(ok)
            cmd = nep.call_args[0][0]
            self.assertIn("detach", cmd)

    def test_open_kluizen_leest_mount_lijst(self):
        uit = "disk5s1\t/Volumes/a (APFS)\ndisk6s2\t/Volumes/b (APFS)\n"
        with _fake_run({"stdout": uit}):
            mounts = vault.open_kluizen()
            self.assertEqual(mounts, ["/Volumes/a", "/Volumes/b"])


class TestKluisZoeker(unittest.TestCase):
    """Systeem-brede kluiszoeker (Spotlight via mdfind), zoals v2.2.0."""

    def test_zoek_geeft_paden_terug(self):
        with _fake_run({"stdout": "/a/kluis1.dmg\n/b/kluis2.sparsebundle\n"}):
            gevonden = vault.zoek_kluizen()
            self.assertEqual(len(gevonden), 2)
            self.assertTrue(all(str(p).endswith((".dmg", ".sparsebundle")) for p in gevonden))

    def test_zoek_filtert_andere_bestanden_weg(self):
        with _fake_run({"stdout": "/a/kluis.dmg\n/b/leesmij.txt\n"}):
            gevonden = vault.zoek_kluizen()
            self.assertEqual(gevonden, ["/a/kluis.dmg"])


class TestAuditSpoor(unittest.TestCase):
    """Elke kluis-actie leeft in het append-only logboek (huisregel)."""

    def test_actie_wordt_geboekt(self):
        import tempfile, os
        with tempfile.TemporaryDirectory() as tmp:
            logpad = os.path.join(tmp, "audit.json")
            with mock.patch.object(vault, "_audit_pad", return_value=logpad):
                vault._audit_boek("test", {"detail": "x"})
                import json
                met = json.loads(Path(logpad).read_text())
                self.assertEqual(len(met), 1)
                self.assertEqual(met[0]["actie"], "test")
                self.assertIn("moment", met[0])
            # tweede entry append (nooit overschrijven)
            with mock.patch.object(vault, "_audit_pad", return_value=logpad):
                vault._audit_boek("tweede", {})
                import json
                met = json.loads(Path(logpad).read_text())
                self.assertEqual(len(met), 2)


if __name__ == "__main__":
    unittest.main()
