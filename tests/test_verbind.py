"""Testen voor de centrale verbinding-constante (kern/growkit_verbind.py).

Audit 5 sept 2026, bevinding 1: het SSH-doel stond hardcoded in vijf
kernbestanden. Deze test verankert dat het doel op precies één plek
gedefinieerd is en dat de agent-bridges die constante hergebruiken.
"""
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
KERN = REPO / "kern"

_VIJF_BRIDGES = [
    "growkit_agenttaak.py",
    "growkit_agentcontrole.py",
    "growkit_agentstatus.py",
    "growkit_graaf.py",
    "growkit_observaties.py",
]


class TestCentraalHost(unittest.TestCase):
    def test_verbind_module_bestaat_en_biedt_host(self):
        from kern import growkit_verbind

        self.assertTrue(hasattr(growkit_verbind, "HOST"))
        host = growkit_verbind.HOST
        self.assertIsInstance(host, str)
        self.assertIn("@", host)  # gebruiker@adres
        # omleidbaar via omgeving (zelfde patroon als GROWKIT_*-overrides)
        self.assertIn("GROWKIT_HOST", growkit_verbind.__dict__.get("__doc__", "") + "")

    def test_verbind_host_is_omleidbaar_via_omgeving(self):
        import importlib
        import os
        from kern import growkit_verbind

        oud = os.environ.get("GROWKIT_HOST")
        try:
            os.environ["GROWKIT_HOST"] = "gebruiker@voorbeeld.test"
            importlib.reload(growkit_verbind)
            self.assertEqual(growkit_verbind.HOST, "gebruiker@voorbeeld.test")
        finally:
            if oud is None:
                os.environ.pop("GROWKIT_HOST", None)
            else:
                os.environ["GROWKIT_HOST"] = oud
            importlib.reload(growkit_verbind)

    def test_bridges_gebruiken_de_centrale_constante(self):
        for naam in _VIJF_BRIDGES:
            with self.subTest(bestand=naam):
                bron = (KERN / naam).read_text(encoding="utf-8")
                self.assertIn("from kern.growkit_verbind import HOST",
                              bron, f"{naam} importeert HOST niet centraal")
                self.assertNotIn("root@168.119.248.208", bron,
                                 f"{naam} bevat nog het hardcoded adres")

    def test_geen_hardcoded_adres_anders_in_kern(self):
        # het adres mag in de hele kern uitsluitend in growkit_verbind.py
        for bronbestand in KERN.glob("*.py"):
            if bronbestand.name == "growkit_verbind.py":
                continue
            with self.subTest(bestand=bronbestand.name):
                bron = bronbestand.read_text(encoding="utf-8")
                self.assertNotIn("168.119.248.208", bron,
                                 f"{bronbestand.name} bevat nog het IP-adres")


if __name__ == "__main__":
    unittest.main()


class TestStandaardOpslagConventie(unittest.TestCase):
    """Audit 5 sept 2026: per-machine staat hoort in ~/.growkit/, niet in
    een tweede verborgen map ~/growkit-profiel/."""

    def test_profiel_en_hervatvlag_gebruiken_growkit_thuismap(self):
        for naam in ("growkit_profiel.py", "growkit_hervatvlag.py"):
            with self.subTest(bestand=naam):
                bron = (KERN / naam).read_text(encoding="utf-8")
                self.assertNotIn("growkit-profiel", bron,
                                 f"{naam} schrijft nog naar ~/growkit-profiel/")
                self.assertIn('".growkit"', bron,
                              f"{naam} gebruikt de .growkit-thuismap niet")
