"""Fase 1 — tests voor het harnas: tests zijn wet, ook in GrowKit.

Bewijsvruchten:
- check vóór goedkeuring: gewijzigde kadertest = taak-faal, ongeacht bewijs
- ongeregistreerde/verdwijnen tests vallen op
- corrupt manifest = nette fout, nooit auto-herstel
- registratie is een mens-handeling (via adapter-actie), geen bijwerking
"""
import json
import tempfile
import unittest
from pathlib import Path

from kern import growkit_pts as pts

KADERTEKST = "def test_kader():\n    assert 1 + 1 == 2\n"


class TestHarnas(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.basis = Path(self.tmp.name)
        (self.basis / "kadertests").mkdir()
        (self.basis / "kadertests" / "test_kader.py").write_text(KADERTEKST)
        self.manifest = self.basis / "manifest.json"

    def tearDown(self):
        self.tmp.cleanup()

    def _registreer(self):
        pts.registreer_test(self.manifest, self.basis / "kadertests/test_kader.py",
                            self.basis)

    def test_schoon_na_registratie(self):
        self._registreer()
        r = pts.check_tests(self.basis, self.manifest)
        self.assertTrue(r["ok"])
        self.assertEqual(r["gecontroleerd"], 1)

    def test_gewijzigde_test_faalt_ongeacht_bewijs(self):
        self._registreer()
        # de agent buigt de test om te slagen:
        (self.basis / "kadertests/test_kader.py").write_text(
            "def test_kader():\n    assert True\n")
        r = pts.check_tests(self.basis, self.manifest)
        self.assertFalse(r["ok"])
        self.assertTrue(any("TESTGEWIJZIGD" in f for f in r["fouten"]))

    def test_ongeregistreerde_nieuwe_test_faalt(self):
        self._registreer()
        (self.basis / "kadertests/test_nieuw.py").write_text(KADERTEKST)
        r = pts.check_tests(self.basis, self.manifest)
        self.assertFalse(r["ok"])
        self.assertTrue(any("ONGEREGISTREERD" in f for f in r["fouten"]))

    def test_verdwenen_test_faalt(self):
        self._registreer()
        (self.basis / "kadertests/test_kader.py").unlink()
        r = pts.check_tests(self.basis, self.manifest)
        self.assertFalse(r["ok"])
        self.assertTrue(any("VERDWENEN" in f for f in r["fouten"]))

    def test_corrupt_manifest_is_nette_fout(self):
        self.manifest.write_text("{ kapot")
        with self.assertRaises(ValueError):
            pts.check_tests(self.basis, self.manifest)

    def test_her_registratie_na_menselijk_akkoord_herstelt(self):
        self._registreer()
        (self.basis / "kadertests/test_kader.py").write_text(
            "def test_kader():\n    assert True\n")
        self.assertFalse(pts.check_tests(self.basis, self.manifest)["ok"])
        # de mens stemt in en her-registreert bewust:
        pts.registreer_test(self.manifest, self.basis / "kadertests/test_kader.py",
                            self.basis)
        self.assertTrue(pts.check_tests(self.basis, self.manifest)["ok"])


if __name__ == "__main__":
    unittest.main()
