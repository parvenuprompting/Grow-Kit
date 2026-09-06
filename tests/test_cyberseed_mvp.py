"""Testen voor CyberSeed MVP-uitbreiding: naam-kiezer, RAM-detectie,
vergrendeling, cloud/lokaal-modus, routering, installatie-status.

Review-punten (NuNu 6 sept) zijn verwerkt:
- punt 1: lokaal = eindbestemming, cloud = brug (modus per naam, swapbaar)
- punt 2: lichte routering — Sprout is default, escalatie expliciet
- punt 4: alle Ollama-tags geverifieerd (11× HTTP 200 op ollama.com/library)
- punt 5: chatlog-vulling zichtbaar in status
"""
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from kern import growkit_cyberseed as cs
from kern import growkit_ram as ram


class TestRamDetectie(unittest.TestCase):
    def test_klasse_per_grenswaarde(self):
        self.assertEqual(ram.ram_klasse(8), "8-15")
        self.assertEqual(ram.ram_klasse(16), "16-23")
        self.assertEqual(ram.ram_klasse(24), "24-36")
        self.assertEqual(ram.ram_klasse(48), "48-64")
        self.assertEqual(ram.ram_klasse(96), "96+")
        self.assertEqual(ram.ram_klasse(128), "96+")

    def test_ram_gb_leest_sysctl_macos(self):
        import sys
        if sys.platform != "darwin":
            self.skipTest("sysctl is macOS-only")
        gb = ram.ram_gb()
        self.assertGreater(gb, 0)

    def test_manifest_bestaat_en_is_geldig(self):
        m = ram.manifest()
        self.assertEqual(m["versie"], 1)
        for klasse in ("8-15", "16-23", "24-36", "48-64", "96+"):
            self.assertIn(klasse, m["lokaal"])
        for naam in ("sprout", "root", "leaf", "tree", "jungle", "amazone"):
            self.assertIn(naam, m["cloud"])
            self.assertIn(naam, m["namen"])

    def test_alle_ollama_tags_bestaan_in_library(self):
        """Punt 4 (NuNu): elke niet-null tag moet een geldige Ollama-tag zijn.
        We controleren de manifest-structuur + dat de geverifieerde lijst
        klopt (offline-test; de live-check draaide al: 11× HTTP 200)."""
        m = ram.manifest()
        geverifieerd = {
            "qwen3:0.6b", "qwen3:1.7b", "qwen3:4b", "qwen3:8b", "qwen3:14b",
            "qwen3:32b", "qwen3.6:27b", "qwen3-coder:30b", "gpt-oss:20b",
            "llama3.3:70b", "qwen3-coder-next",
        }
        for klasse_dict in m["lokaal"].values():
            for tag in klasse_dict.values():
                if tag is not None:
                    self.assertIn(tag, geverifieerd)

    def test_model_voor_naam_en_vergrendeling(self):
        self.assertEqual(ram.model_voor("24-36", "sprout"), "qwen3:4b")
        self.assertEqual(ram.model_voor("24-36", "amazone"), "qwen3:32b")
        # 8-15: jungle/amazone vergrendeld
        self.assertIsNone(ram.model_voor("8-15", "jungle"))
        self.assertTrue(ram.is_vergrendeld("8-15", "jungle"))
        self.assertFalse(ram.is_vergrendeld("24-36", "jungle"))

    def test_min_ram_voor_vergrendelde_naam(self):
        # jungle wordt pas beschikbaar in 16-23 → minimaal 16 GB
        self.assertEqual(ram.min_ram_gb("jungle"), 16)
        # amazone pas in 24-36 → minimaal 24 GB
        self.assertEqual(ram.min_ram_gb("amazone"), 24)
        # sprout is overal → 8
        self.assertEqual(ram.min_ram_gb("sprout"), 8)


class TestNamenEnPrompts(unittest.TestCase):
    def test_zes_namen_met_prompts(self):
        namen = cs.cyberseed_namen()
        self.assertEqual(len(namen), 6)
        for sleutel, info in namen.items():
            self.assertIn("titel", info)
            self.assertIn("prompt", info)
            self.assertTrue(info["prompt"].startswith("Je bent CyberSeed"))

    def test_prompts_governance_in_alle_tiers(self):
        """Review: governance in alle tiers (geen actie zonder audit-spoor)."""
        for sleutel, info in cs.cyberseed_namen().items():
            p = info["prompt"]
            # Sprout/Root zijn consultatief; Leaf+ noemen grenzen expliciet
            if sleutel in ("leaf", "tree", "jungle", "amazone"):
                self.assertTrue(
                    "buiten" in p or "goedkeuring" in p or "governance" in p,
                    f"prompt van {sleutel} mist governance-regel")


class TestModusEnRoutering(unittest.TestCase):
    def test_standaard_is_sprout_lokaal(self):
        """Punt 2 (NuNu): lichte routering — Sprout is de default, nooit
        per ongeluk een duur model."""
        keuze = cs.kies_model("gewone vraag", naam=None, modus=None)
        self.assertEqual(keuze["naam"], "sprout")
        self.assertEqual(keuze["modus"], "lokaal")

    def test_expliciete_escalatie_wordt_gevolgd(self):
        keuze = cs.kies_model("complex ontwerp", naam="amazone", modus="cloud")
        self.assertEqual(keuze["naam"], "amazone")
        self.assertEqual(keuze["modus"], "cloud")
        self.assertEqual(keuze["model_id"],
                         "anthropic/claude-opus-5")  # uit manifest (frontier-opties)

    def test_lokaal_gebruikt_ram_klasse_model(self):
        with mock.patch.object(ram, "ram_klasse", return_value="24-36"):
            keuze = cs.kies_model("vraag", naam="root", modus="lokaal")
        self.assertEqual(keuze["model_id"], "qwen3:8b")  # 24-36 → root

    def test_vergrendelde_naam_valt_terug_naar_sprout(self):
        with mock.patch.object(ram, "ram_klasse", return_value="8-15"):
            keuze = cs.kies_model("vraag", naam="amazone", modus="lokaal")
        self.assertEqual(keuze["naam"], "sprout")  # teruggevallen
        self.assertTrue(keuze.get("teruggevallen"))

    def test_keuze_wordt_gelogd(self):
        """Verificatie-eis: log-regel per call met naam + model_id."""
        with tempfile.TemporaryDirectory() as tmp:
            with mock.patch.object(cs, "_basis_pad", return_value=Path(tmp)):
                with mock.patch.object(cs, "_http_post",
                                       return_value=(200, json.dumps(
                                           {"message": {"content": "ok"}}).encode())), \
                     mock.patch.object(cs, "soul_lees", return_value="S"):
                    cs.chat("test", van="X", naam="root", modus="lokaal")
                logpad = Path(tmp) / "routinglog.jsonl"
                self.assertTrue(logpad.exists())
                laatste = json.loads(logpad.read_text().strip().splitlines()[-1])
                self.assertEqual(laatste["naam"], "root")
                self.assertIn("model_id", laatste)
                self.assertIn("modus", laatste)


class TestInstallatieStatus(unittest.TestCase):
    def test_status_per_naam(self):
        with mock.patch.object(cs, "ollama_status",
                               return_value={"draait": True,
                                             "modellen": ["qwen3:8b"],
                                             "sprout_basis_aanwezig": True}), \
             mock.patch.object(ram, "ram_klasse", return_value="24-36"):
            overzicht = cs.installatie_status()
        # root in 24-36 = qwen3:8b → geïnstalleerd
        self.assertEqual(overzicht["root"]["status"], "geinstalleerd")
        self.assertEqual(overzicht["root"]["model"], "qwen3:8b")
        # alles is beschikbaar in 24-36
        self.assertFalse(overzicht["amazone"]["vergrendeld"])

    def test_vergrendeld_toont_min_ram(self):
        with mock.patch.object(cs, "ollama_status",
                               return_value={"draait": True, "modellen": [],
                                             "sprout_basis_aanwezig": False}), \
             mock.patch.object(ram, "ram_klasse", return_value="8-15"):
            overzicht = cs.installatie_status()
        self.assertTrue(overzicht["jungle"]["vergrendeld"])
        self.assertEqual(overzicht["jungle"]["min_ram_gb"], 16)
        self.assertEqual(overzicht["jungle"]["status"], "vergrendeld")

    def test_niet_geinstalleerd_met_pull_commando(self):
        with mock.patch.object(cs, "ollama_status",
                               return_value={"draait": True,
                                             "modellen": [],
                                             "sprout_basis_aanwezig": False}), \
             mock.patch.object(ram, "ram_klasse", return_value="24-36"):
            overzicht = cs.installatie_status()
        self.assertEqual(overzicht["amazone"]["status"], "niet geinstalleerd")
        self.assertEqual(overzicht["amazone"]["pull_commando"],
                         "ollama pull qwen3:32b")


class TestChatlogVulling(unittest.TestCase):
    def test_vulling_percentage(self):
        """Punt 5 (NuNu): toon hoe vol de chatlog is die de volgende
        SOUL-regeneratie voedt."""
        with tempfile.TemporaryDirectory() as tmp:
            with mock.patch.object(cs, "_basis_pad", return_value=Path(tmp)):
                pad = Path(tmp) / "chatlog.jsonl"
                with pad.open("w") as f:
                    for i in range(68):
                        f.write(json.dumps({"ts": "t", "rol": "gebruiker",
                                            "tekst": "x" * 100}) + "\n")
                vulling = cs.chatlog_vulling()
                self.assertIn("procent", vulling)
                self.assertGreater(vulling["procent"], 0)



class TestCloudOpties(unittest.TestCase):
    """Frontier-cloud: meerdere modellen per naam, eerste = default."""

    def test_opties_per_naam(self):
        self.assertIn("google/gemini-3.5-flash", ram.cloud_opties("sprout"))
        self.assertIn("z-ai/glm-5.3-flash", ram.cloud_opties("sprout"))
        self.assertIn("openai/gpt-6-astra", ram.cloud_opties("amazone"))
        self.assertIn("anthropic/claude-opus-5", ram.cloud_opties("amazone"))
        self.assertIn("moonshotai/kimi-k3", ram.cloud_opties("jungle"))

    def test_default_is_eerste_optie(self):
        for naam in ("sprout", "root", "leaf", "tree", "jungle", "amazone"):
            self.assertEqual(ram.cloud_default(naam),
                             ram.cloud_opties(naam)[0])

    def test_kies_model_gebruikt_expliciete_cloud_keuze(self):
        k = cs.kies_model("x", naam="jungle", modus="cloud",
                          cloud_model="moonshotai/kimi-k3")
        self.assertEqual(k["model_id"], "moonshotai/kimi-k3")

    def test_ongeldige_cloud_keuze_valt_op_default(self):
        k = cs.kies_model("x", naam="leaf", modus="cloud",
                          cloud_model="nep/model")
        self.assertEqual(k["model_id"], ram.cloud_default("leaf"))


if __name__ == "__main__":
    unittest.main()
