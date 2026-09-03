import json
import tempfile
import unittest
from pathlib import Path

from kern.growkit_leesroute import fase_content


class TestLeesroute(unittest.TestCase):
    """De leesroute is een grens, geen advies: per fase alleen de juiste content."""

    def setUp(self):
        # miniatuur-repo in tmp zodat de test onafhankelijk van de echte repo is
        self.tmp = tempfile.TemporaryDirectory()
        self.repo = Path(self.tmp.name)
        (self.repo / "SEED.md").write_text("# Geboortebrief\n\nRegels hier.\n", encoding="utf-8")
        profielen = self.repo / "profielen"
        (profielen / "tweede-brein").mkdir(parents=True)
        (profielen / "INDEX.md").write_text("# Kiemkeuze\n\nCatalogus.\n", encoding="utf-8")
        stappen = [
            {"id": "stap-001", "commando": "echo een", "bewijs": {"type": "shell_check", "commando": "echo een", "verwacht_substr": "een"}, "bij_falen": {}, "idempotent": True},
            {"id": "stap-002", "commando": "echo twee", "bewijs": {"type": "shell_check", "commando": "echo twee", "verwacht_substr": "twee"}, "bij_falen": {}, "idempotent": True},
        ]
        (profielen / "tweede-brein" / "profiel.json").write_text(
            json.dumps({"profiel": "tweede-brein", "status": "bewezen-vorm", "stappen": stappen}, ensure_ascii=False),
            encoding="utf-8")
        groei = self.repo / "groei"
        groei.mkdir()
        (groei / "SETUP.md").write_text("# Groeilaag\n\nInstructie.\n", encoding="utf-8")

    def tearDown(self):
        self.tmp.cleanup()

    def test_fase0_is_geboortebrief(self):
        content = fase_content(0, {"repo": self.repo})
        self.assertIn("Geboortebrief", content)
        self.assertNotIn("Kiemkeuze", content)  # fase 0 ziet de catalogus niet

    def test_fase1_is_kiemkeuze(self):
        content = fase_content(1, {"repo": self.repo})
        self.assertIn("Kiemkeuze", content)
        self.assertNotIn("Geboortebrief", content)

    def test_fase2_geeft_alleen_de_gevraagde_stap(self):
        stap1 = fase_content(2, {"repo": self.repo, "profiel": "tweede-brein", "stap_index": 0})
        stap2 = fase_content(2, {"repo": self.repo, "profiel": "tweede-brein", "stap_index": 1})
        self.assertIn("stap-001", stap1)
        self.assertIn("stap-002", stap2)
        self.assertNotIn("stap-002", stap1)  # afdwinging: stap 1 ziet stap 2 niet
        self.assertNotIn("stap-001", stap2)

    def test_fase3_is_groeilaag(self):
        content = fase_content(3, {"repo": self.repo})
        self.assertIn("Groeilaag", content)

    def test_onbekende_fase_weigert(self):
        with self.assertRaises(ValueError):
            fase_content(9, {"repo": self.repo})


if __name__ == "__main__":
    unittest.main()
