"""ZT-6 — Skills-beheer fase A1: kern.

- lijst_bron() geeft beide bronnen terug (Mac-lokaal + VPS-profiel),
  met een gedirigeerde tmp-root (geen echte profielmap bij de test);
- lees() retourneert exacte SKILL.md-inhoud;
- schrijf() maakt EERST een backup met timestamp, overschrijft pas
  daarna (append-only geest);
- valideer(): zonder frontmatter → fout; zonder kop → fout; inhoud met
  een API-key-patroon → geweigerd, geen crash.
"""
import unittest
import tempfile
import os
from pathlib import Path

from kern import growkit_skills as sk


def _bron(root: str) -> dict:
    return {
        "mac": {"pad": os.path.join(root, "mac-skills")},
        "vps": {"pad": os.path.join(root, "vps-skills")},
    }


_GELDIG = "---\nnaam: test\n---\n\n# Test\n\nInhoud.\n"


class TestSkillsKern(unittest.TestCase):
    def setUp(self):
        import tempfile
        self.root = tempfile.mkdtemp()
        for b in ("mac", "vps"):
            os.makedirs(os.path.join(self.root, f"{b}-skills", "demo"))

    # 1 — lijst_bron geeft beide bronnen terug
    def test_lijst_bron_geeft_beide_bronnen(self):
        bronnen = sk.lijst_bron(bronnen={"mac": {"pad": self.root + "/mac-skills"},
                                         "vps": {"pad": self.root + "/vps-skills"}})
        ids = {b["id"] for b in bronnen}
        self.assertEqual(ids, {"mac", "vps"})
        mac = next(b for b in bronnen if b["id"] == "mac")
        self.assertEqual(mac["pad"], self.root + "/mac-skills")

    # 2 — lees retourneert exacte SKILL.md-inhoud
    def test_lees_exacte_inhoud(self):
        pad = os.path.join(self.root, "mac-skills", "demo", "SKILL.md")
        with open(pad, "w") as f:
            f.write(_GELDIG)
        uit = sk.lees("mac", "demo",
                      bronnen={"mac": {"pad": self.root + "/mac-skills"}})
        self.assertEqual(uit, _GELDIG)

    def test_lees_onbekende_skill_geeft_geen_crash(self):
        uit = sk.lees("mac", "bestaatniet",
                      bronnen={"mac": {"pad": self.root + "/mac-skills"}})
        self.assertIsNone(uit)

    # 3 — schrijf maakt eerst backup, overschrijft pas daarna
    def test_schrijf_maakt_backup_voor_overschrijven(self):
        pad = os.path.join(self.root, "vps-skills", "demo", "SKILL.md")
        oud = _GELDIG
        with open(pad, "w") as f:
            f.write(oud)
        nieuw = oud + "\nNieuwe regel.\n"
        sk.schrijf("vps", "demo", nieuw,
                   bronnen={"vps": {"pad": self.root + "/vps-skills"}})
        with open(pad) as f:
            self.assertEqual(f.read(), nieuw)
        backups = [n for n in os.listdir(os.path.dirname(pad))
                   if n.startswith("SKILL.backup-") and n.endswith(".md")]
        self.assertEqual(len(backups), 1, "er moet precies één backup zijn")
        with open(os.path.join(os.path.dirname(pad), backups[0])) as f:
            self.assertEqual(f.read(), oud)

    def test_schrijf_nieuwe_skill_zonder_backup(self):
        pad = os.path.join(self.root, "vps-skills", "demo", "SKILL.md")
        sk.schrijf("vps", "demo", _GELDIG,
                   bronnen={"vps": {"pad": self.root + "/vps-skills"}})
        with open(pad) as f:
            self.assertEqual(f.read(), _GELDIG)
        backups = [n for n in os.listdir(os.path.dirname(pad))
                   if n.startswith("SKILL.backup-")]
        self.assertEqual(backups, [])

    # 4 — valideer: frontmatter en kop verplicht
    def test_valideer_zonder_frontmatter_is_fout(self):
        self.assertFalse(sk.valideer("# Kop\n\nTekst.")[0])

    def test_valideer_zonder_kop_is_fout(self):
        self.assertFalse(sk.valideer("---\nnaam: x\n---\n\nGeen kop.")[0])

    # 5 — valideer: API-key-patroon geweigerd, geen crash
    def test_valideer_weigert_api_key(self):
        geheim = "---\nnaam: x\n---\n\n# X\n\nkey: sk-" + "abc123def456ghi789jkl012mno\n"
        ok, reden = sk.valideer(geheim)
        self.assertFalse(ok)
        self.assertTrue(any("secret" in reden.lower() or "key" in reden.lower()
                            for reden in [sk.valideer(geheim)[1]]))

    def test_valideer_geldig_document(self):
        self.assertTrue(sk.valideer(_GELDIG)[0])


if __name__ == "__main__":
    unittest.main()
