"""Mijlpaal-bevestiging (§11.4): grote planten worden bevestigd vóór de motorstart.

Regels (fase 3, taak 6):
- Drempel N is configureerbaar in het profiel (mijlpaal_drempel), standaard 10.
- Aantal stappen ≥ N → seed.py toont vóór de motorstart het vaste
  mijlpaal-formaat (begrepen / afgesproken mèt logboek-verwijzing /
  bewijs tot nu toe / hierna) en vraagt precies één bevestiging.
- De bevestiging wordt append-only in het logboek gelogd; zonder
  bevestiging: geen actie.
- Het huidige tweede-brein-profiel (8 stappen) raakt de drempel niet.
"""
import json
import tempfile
import unittest
from pathlib import Path

from kern.growkit_poort import mijlpaal_nodig
from seed import mijlpaal_blok, vraag_mijlpaal_bevestiging

TWEEDE_BREIN = Path(__file__).parent.parent / "profielen" / "tweede-brein" / "profiel.json"


def _profiel(aantal_stappen: int, drempel: int | None = None) -> dict:
    profiel = {
        "profiel": "test-boom",
        "stappen": [{"id": f"stap-{i:03d}"} for i in range(1, aantal_stappen + 1)],
    }
    if drempel is not None:
        profiel["mijlpaal_drempel"] = drempel
    return profiel


class TestMijlpaalDrempel(unittest.TestCase):
    def test_tien_stappen_raakt_de_standaarddrempel(self):
        self.assertTrue(mijlpaal_nodig(_profiel(10)))

    def test_acht_stappen_raakt_de_drempel_niet(self):
        self.assertFalse(mijlpaal_nodig(_profiel(8)))

    def test_drempel_is_dynamisch_uit_het_profiel(self):
        self.assertTrue(mijlpaal_nodig(_profiel(3, drempel=3)))
        self.assertFalse(mijlpaal_nodig(_profiel(10, drempel=20)))

    def test_bestaand_tweede_brein_profiel_verandert_niet(self):
        """Regressie: het 8-stappenprofiel krijgt geen mijlpaal — E2E's blijven staan."""
        with open(TWEEDE_BREIN, encoding="utf-8") as f:
            self.assertFalse(mijlpaal_nodig(json.load(f)))


class TestMijlpaalFormaat(unittest.TestCase):
    def test_blok_volgt_het_vaste_114_formaat(self):
        with tempfile.TemporaryDirectory() as tmp:
            doel = Path(tmp)
            logboek = doel / "logboek.json"
            blok = mijlpaal_blok(_profiel(12), doel, logboek)
            self.assertIn("Wat ik begrepen heb", blok)
            self.assertIn("Wat we afgesproken hebben", blok)
            self.assertIn(str(logboek), blok)          # logboek-verwijzing: controleerbaar
            self.assertIn("Het bewijs tot nu toe", blok)
            self.assertIn("Wat hierna komt", blok)
            self.assertIn("test-boom", blok)           # het begrip van de agent, niet de wens


class TestMijlpaalBevestiging(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.doel = Path(self._tmp.name)
        self.logboek = self.doel / "logboek.json"
        self.logboek.write_text("[]", encoding="utf-8")

    def tearDown(self):
        self._tmp.cleanup()

    def test_bevestiging_ja_wordt_append_only_geloggd(self):
        bestaand = [{"stap": "stap-000", "status": "geslaagd", "bewijs": "eerder"}]
        self.logboek.write_text(json.dumps(bestaand), encoding="utf-8")
        ok = vraag_mijlpaal_bevestiging(_profiel(12), self.doel, self.logboek,
                                        invoer_fn=lambda _: "ja")
        self.assertTrue(ok)
        entries = json.loads(self.logboek.read_text(encoding="utf-8"))
        self.assertEqual(entries[0], bestaand[0])          # append-only: niets verdwijnt
        mijlpaal = [e for e in entries if e.get("type") == "mijlpaal"]
        self.assertEqual(len(mijlpaal), 1)
        self.assertEqual(mijlpaal[0]["status"], "bevestigd")
        self.assertIn("tijdstip", mijlpaal[0])

    def test_geen_bevestiging_geen_actie(self):
        ok = vraag_mijlpaal_bevestiging(_profiel(12), self.doel, self.logboek,
                                        invoer_fn=lambda _: "nee")
        self.assertFalse(ok)
        entries = json.loads(self.logboek.read_text(encoding="utf-8"))
        self.assertEqual([e for e in entries if e.get("type") == "mijlpaal"], [])

    def test_vraagt_precies_een_keer(self):
        calls = []
        vraag_mijlpaal_bevestiging(_profiel(12), self.doel, self.logboek,
                                   invoer_fn=lambda _: calls.append(1) or "ja")
        self.assertEqual(len(calls), 1)


if __name__ == "__main__":
    unittest.main()
