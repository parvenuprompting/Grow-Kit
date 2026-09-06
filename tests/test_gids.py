"""Testen voor de AI Gids-kern (kern/growkit_gids.py).

De gids bevat kerninzichten gedistilleerd uit Tiëndo's Google
Drive-documenten. Verankerd wordt: het bestand laadt, elk inzicht heeft
een bron, zoeken werkt en thema's zijn compleet.
"""
import unittest
from pathlib import Path

from kern import growkit_gids as gids

REPO = Path(__file__).resolve().parent.parent


class TestGidsData(unittest.TestCase):
    def test_data_bestaat_en_laadt(self):
        data = gids.laad()
        self.assertIn("thema's", data)
        self.assertTrue(len(data["thema's"]) >= 5)

    def test_elk_inzicht_heeft_titel_inhoud_en_bron(self):
        for thema in gids.laad()["thema's"]:
            for i in thema["inzichten"]:
                self.assertTrue(i["titel"], f"titel leeg in {thema['thema']}")
                self.assertTrue(i["inhoud"], f"inhoud leeg: {i['titel']}")
                self.assertTrue(i["bron"], f"bron ontbreekt: {i['titel']}")

    def test_bekende_themas_aanwezig(self):
        namen = {t["thema"] for t in gids.laad()["thema's"]}
        for verwacht in ("De Architect-mindset", "Zero-Trust en Machine-Bewijs",
                         "Samenwerken met AI", "Bouwen met agenten",
                         "Besturing en vertrouwen", "Effectief leren"):
            self.assertIn(verwacht, namen)


class TestZoeken(unittest.TestCase):
    def test_zoek_op_titel(self):
        r = gids.zoek("machine-bewijs")
        self.assertTrue(r)
        self.assertTrue(any(
            "machine-bewijs" in x["titel"].lower()
            or "machine-bewijs" in x["inhoud"].lower()
            or "machine-bewijs" in x["bron"].lower()
            for x in r))

    def test_zoek_op_inhoud(self):
        r = gids.zoek("hallucin")
        self.assertTrue(r)

    def test_zoek_zonder_resultaat_geeft_leeg(self):
        self.assertEqual(gids.zoek("xtqwxzqq"), [])

    def test_zoek_op_bron(self):
        r = gids.zoek("Nachtfabriek")
        self.assertTrue(r)
        self.assertTrue(all("Nachtfabriek" in x["bron"] or
                            "Nachtfabriek" in x["titel"] or
                            "Nachtfabriek" in x["inhoud"] for x in r))


if __name__ == "__main__":
    unittest.main()
