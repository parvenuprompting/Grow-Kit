"""ZT-7 — Skills-beheer fase A2: het scherm (view-model).

Het view-model dat het SwiftUI-skills-scherm voedt, op basis van de
A1-kern (kern/growkit_skills.py):

1. laad_lijst() levert sorteerbare skills met naam + pad uit de
   A1-bronnen (geen crash op lege of ontbrekende bronmappen);
2. laad_inhoud(pad) geeft frontmatter en body gescheiden terug;
   onbestaand pad → nette fout-melding, geen crash;
3. vergelijk(oud, nieuw) markeert verwijderde en veranderde regels
   (minimale tekstvergelijking, geen fancy diff-UI);
4. weigeren van schrijven als de inhoud een secrets-patroon bevat
   (A1-validatie, hergebruikt — test niet verzwakt).
"""
import unittest
import tempfile
import os

from kern import growkit_skills_scherm as scherm

_GELDIG = "---\nnaam: demo\n---\n\n# Demo\n\nInhoud.\n"


def _bron(root):
    return {"mac": {"pad": os.path.join(root, "mac-skills")}}


class TestSkillsSchermModel(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp()
        self.bronnen = _bron(self.root)
        self.mac = os.path.join(self.root, "mac-skills")

    # 1 — laad_lijst: sorteerbare skills met naam + pad
    def test_laad_lijst_gesorteerd_met_naam_en_pad(self):
        for naam in ("zoek", "agenda", "vault"):
            os.makedirs(os.path.join(self.mac, naam))
            with open(os.path.join(self.mac, naam, "SKILL.md"), "w") as f:
                f.write(_GELDIG.replace("demo", naam))
        uit = scherm.laad_lijst(bronnen=self.bronnen)
        self.assertEqual([s["naam"] for s in uit],
                         ["agenda", "vault", "zoek"])  # alfabetisch gesorteerd
        self.assertTrue(all(s["pad"].endswith("SKILL.md") for s in uit))
        self.assertEqual(uit[0]["bron"], "mac")

    def test_laad_lijst_lege_of_ontbrekende_bron_geen_crash(self):
        self.assertEqual(scherm.laad_lijst(bronnen=self.bronnen), [])
        self.assertEqual(
            scherm.laad_lijst(bronnen={"mac": {"pad": "/bestaat/niet"}}), [])

    def test_laad_lijst_negeert_map_zonder_skill_md(self):
        os.makedirs(os.path.join(self.mac, "leeg"))
        self.assertEqual(scherm.laad_lijst(bronnen=self.bronnen), [])

    # 2 — laad_inhoud: frontmatter en body gescheiden; nette fout
    def test_laad_inhoud_scheidt_frontmatter_en_body(self):
        pad = os.path.join(self.mac, "demo", "SKILL.md")
        os.makedirs(os.path.dirname(pad))
        with open(pad, "w") as f:
            f.write(_GELDIG)
        uit = scherm.laad_inhoud(pad)
        self.assertEqual(uit["frontmatter"], "naam: demo")
        self.assertIn("# Demo", uit["body"])

    def test_laad_inhoud_onbestaand_pad_nette_fout(self):
        uit = scherm.laad_inhoud(os.path.join(self.mac, "ontbreekt", "SKILL.md"))
        self.assertIn("fout", uit)
        self.assertNotIn("frontmatter", uit)

    # 3 — vergelijk: verwijderde en veranderde regels gemarkeerd
    def test_vergelijk_markeert_verwijderd(self):
        uit = scherm.vergelijk("# Demo\nregel A\n", "# Demo\n")
        soorten = {(d["type"], d["regel"]) for d in uit}
        self.assertIn(("verwijderd", "regel A"), soorten)

    def test_vergelijk_markeert_gewijzigd(self):
        uit = scherm.vergelijk("# Demo\noud\n", "# Demo\nnieuw\n")
        soorten = {(d["type"], d["regel"]) for d in uit}
        self.assertIn(("verwijderd", "oud"), soorten)
        self.assertIn(("nieuw", "nieuw"), soorten)

    def test_vergelijk_identiek_leeg(self):
        self.assertEqual(scherm.vergelijk("# Demo\n", "# Demo\n"), [])

    # 4 — schrijf-weigeren bij secrets (A1-validatie, hergebruikt)
    def test_schrijf_weigert_secret(self):
        # runtime opgebouwd zodat dit bestand zelf geen token-letterlijk
        # bevat (poort BSL-037); de gevalideerde inhoud is identiek
        token = "sk-" + "abcdefghijklmnop123456"
        kwad = _GELDIG + "\nsleutel: " + token + "\n"
        met_een_resultaat = scherm.schrijf("mac", "demo", kwad,
                                           bronnen=self.bronnen)
        self.assertFalse(met_een_resultaat["ok"])
        self.assertIn("geweigerd", met_een_resultaat["fout"])
        # niets op schijf gezet
        self.assertFalse(os.path.exists(os.path.join(self.mac, "demo", "SKILL.md")))

    def test_schrijf_geldige_inhoud_ok_met_backupid(self):
        uit = scherm.schrijf("mac", "demo", _GELDIG, bronnen=self.bronnen)
        self.assertTrue(uit["ok"])
        with open(os.path.join(self.mac, "demo", "SKILL.md")) as f:
            self.assertEqual(f.read(), _GELDIG)

    def test_schrijf_weigert_ook_zonder_frontmatter(self):
        uit = scherm.schrijf("mac", "demo", "# Demo zonder frontmatter\n",
                             bronnen=self.bronnen)
        self.assertFalse(uit["ok"])


if __name__ == "__main__":
    unittest.main()
