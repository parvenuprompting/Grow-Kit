"""Testen voor eigen cloud-model per naam (Tiëndo's customize-wens) mét
tier-validatie (NuNu-verfijning): te zwaar op Sprout = geweigerd, tenzij
force=true (bewuste keuze, gelogd)."""
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

import adapter
from kern import growkit_cyberseed as cs
from kern import growkit_ram as ram


class TestEigenCloud(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        p = mock.patch.object(cs, "_basis_pad", return_value=Path(self._tmp.name))
        p.start()
        self.addCleanup(p.stop)
        self.addCleanup(self._tmp.cleanup)

    def test_zet_en_lees(self):
        cs.zet_eigen_cloud("sprout", "z-ai/glm-5.3-flash")
        self.assertEqual(cs.eigen_cloud()["sprout"], "z-ai/glm-5.3-flash")
        cs.zet_eigen_cloud("sprout", None)
        self.assertNotIn("sprout", cs.eigen_cloud())

    def test_kies_model_gebruikt_eigen_keuze(self):
        cs.zet_eigen_cloud("sprout", "z-ai/glm-5.3-flash")
        k = cs.kies_model("vraag", naam="sprout", modus="cloud")
        self.assertEqual(k["model_id"], "z-ai/glm-5.3-flash")

    def test_expliciete_keuze_wint_van_eigen(self):
        cs.zet_eigen_cloud("sprout", "z-ai/glm-5.3-flash")
        k = cs.kies_model("vraag", naam="sprout", modus="cloud",
                          cloud_model="openai/gpt-5.6-luna")
        self.assertEqual(k["model_id"], "openai/gpt-5.6-luna")

    def test_onbekende_naam_geweigerd(self):
        with self.assertRaises(ValueError):
            cs.zet_eigen_cloud("onbestaand", "vendor/model")


class TestTierValidatie(unittest.TestCase):
    def _roep(self, naam, model, force=False):
        invoer = {"zet_eigen_cloud": naam, "model": model}
        if force:
            invoer["force"] = True
        return adapter.COMMANDOS["cyberseedinstellingen"](invoer)

    def test_binnen_tier_gaat_goed(self):
        r = self._roep("sprout", "z-ai/glm-5.3-flash")  # zelfde tier
        self.assertTrue(r["ok"])

    def test_1_tier_verschil_mag(self):
        r = self._roep("root", "google/gemini-3.5-flash")  # 1 tier lager
        self.assertTrue(r["ok"])

    def test_te_zwaar_op_sprout_geweigerd(self):
        """NuNu: Opus-prijs voor Flash-vragen — geweigerd zonder force."""
        with self.assertRaises(adapter.AdapterFout) as ctx:
            self._roep("sprout", "anthropic/claude-opus-5")
        self.assertIn("force", str(ctx.exception))

    def test_te_zwaar_met_force_lukt(self):
        r = self._roep("sprout", "anthropic/claude-opus-5", force=True)
        self.assertTrue(r["ok"])
        self.assertEqual(cs.eigen_cloud()["sprout"], "anthropic/claude-opus-5")

    def test_onbekend_model_krijgt_notitie(self):
        r = self._roep("sprout", "vendor/nieuw-model-2027")
        self.assertTrue(r["ok"])
        self.assertIn("niet in bekende lijst", r["data"]["notitie"])


if __name__ == "__main__":
    unittest.main()
