"""Loop.py plant-modus (§5, §11.1 hard in fase 4): de loop voert niets uit
dat niet de mensbevestiging heeft gehad.

Regels (fase 4, taak 3):
- Het §11.3-formulier wordt door de loop getekend (nummers + iets anders);
  de poort blijft de enige invoerbescherming.
- Geen bevestiging → niets uitgevoerd, doel-logboek onaangeroerd.
- Invoer in tests via invoer_fn-injectie (patroon test_mijlpaal).
"""
import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

import loop


class TestFormulier(unittest.TestCase):
    def test_formulier_toont_opties_met_nummers(self):
        uit = io.StringIO()
        with contextlib.redirect_stdout(uit):
            keuze = loop.formuliervraag("Kies een boom:", ["tweede-brein", "dev-werkplaats"],
                                        invoer_fn=lambda _: "1")
        self.assertEqual(keuze, "tweede-brein")
        self.assertIn("1. tweede-brein", uit.getvalue())
        self.assertIn("2. dev-werkplaats", uit.getvalue())

    def test_iets_anders_wordt_letterlijk_overgenomen(self):
        keuze = loop.formuliervraag("Kies:", ["tweede-brein"], invoer_fn=lambda _: "mijn eigen boom")
        self.assertEqual(keuze, "mijn eigen boom")


class TestPlantModus(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.doel = Path(self._tmp.name) / "boom"
        self._antwoorden = []

    def tearDown(self):
        self._tmp.cleanup()

    def _invoer_fn(self, _vraag: str) -> str:
        return self._antwoorden.pop(0)

    def test_plant_na_bevestiging_via_poort_en_motor(self):
        self._antwoorden = ["1", str(self.doel), "ja"]
        uit = io.StringIO()
        with contextlib.redirect_stdout(uit):
            code = loop.plant_profiel(invoer_fn=self._invoer_fn)
        self.assertEqual(code, 0)
        logboek = json.loads((self.doel / "logboek.json").read_text(encoding="utf-8"))
        statuses = [e["status"] for e in logboek]
        self.assertEqual(statuses.count("geslaagd"), 7)
        self.assertIn("wacht_op_mens", statuses)
        self.assertIn("[mens-moment]", uit.getvalue())

    def test_geen_bevestiging_niets_uitgevoerd(self):
        self._antwoorden = ["1", str(self.doel), "nee"]
        uit = io.StringIO()
        with contextlib.redirect_stdout(uit):
            code = loop.plant_profiel(invoer_fn=self._invoer_fn)
        self.assertEqual(code, 1)
        self.assertFalse(self.doel.exists())
        self.assertNotIn("[OK]", uit.getvalue())

    def test_leeg_doel_wordt_door_de_poort_geweigerd(self):
        self._antwoorden = ["1", ""]
        uit = io.StringIO()
        with contextlib.redirect_stdout(uit):
            code = loop.plant_profiel(invoer_fn=self._invoer_fn)
        self.assertEqual(code, 1)
        self.assertIn("helderziende", uit.getvalue())
        self.assertFalse(self.doel.exists())


class TestModuskeuze(unittest.TestCase):
    def test_onbekende_modus_is_nette_weigering(self):
        uit = io.StringIO()
        with contextlib.redirect_stdout(uit):
            code = loop.main(invoer_fn=lambda _: "onzin")
        self.assertEqual(code, 1)
        self.assertIn("geen actie", uit.getvalue().lower())


if __name__ == "__main__":
    unittest.main()
