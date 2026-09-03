"""Vliegwiel (§11.2, taak 6): het brein voedt de formulier-opties.

Regels:
- brein_opties leest alleen-lezen de mapnamen uit projecten/ van het brein
  (max. 5, alfabetisch); geen brein of lege map → lege lijst.
- De loop voegt ze als "uit je brein"-opties onderaan de kiemkeuze toe —
  advies, nooit uitvoer: een brein-optie is geen profiel en wordt door de
  poort-discipline net geweigerd (ook geen crash op vrije invoer).
"""
import json
import os
import tempfile
import unittest
from pathlib import Path

from kern.growkit_oerwoud import brein_opties


class TestBreinOpties(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.brein = Path(self._tmp.name) / "brein"

    def tearDown(self):
        self._tmp.cleanup()

    def _projecten(self, namen: list[str]) -> None:
        (self.brein / "projecten").mkdir(parents=True, exist_ok=True)
        for naam in namen:
            (self.brein / "projecten" / naam).mkdir(exist_ok=True)
            (self.brein / "projecten" / naam / ".gitkeep").write_text("", encoding="utf-8")

    def test_projecten_worden_opties(self):
        self._projecten(["logboeken", "websites", "experimenten"])
        self.assertEqual(brein_opties(self.brein),
                         ["experimenten", "logboeken", "websites"])  # alfabetisch

    def test_geen_brein_geeft_lege_lijst(self):
        self.assertEqual(brein_opties(Path(self._tmp.name) / "onbestaand"), [])

    def test_lege_projectenmap_geeft_lege_lijst(self):
        (self.brein / "projecten").mkdir(parents=True)
        self.assertEqual(brein_opties(self.brein), [])

    def test_max_vijf_alfabetisch(self):
        self._projecten(["zebra", "appel", "peer", "kiwi", "mango", "banaan", "fig"])
        self.assertEqual(brein_opties(self.brein), ["appel", "banaan", "fig", "kiwi", "mango"])

    def test_lezen_is_alleen_lezen(self):
        self._projecten(["logboeken"])
        bestand = self.brein / "projecten" / "logboeken" / ".gitkeep"
        inhoud_voor = bestand.read_text(encoding="utf-8")
        brein_opties(self.brein)
        self.assertEqual(bestand.read_text(encoding="utf-8"), inhoud_voor)


class TestKiemkeuzeMetBreinOpties(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.doel = Path(self._tmp.name) / "boom"
        self._home = Path(self._tmp.name) / "growkit-home"
        self._oude_env = os.environ.get("GROWKIT_OERWOUD_STAAT")
        os.environ["GROWKIT_OERWOUD_STAAT"] = str(self._home / "oerwoud.json")
        self.brein = Path(self._tmp.name) / "brein"
        (self.brein / "projecten").mkdir(parents=True)
        (self.brein / "projecten" / "logboeken").mkdir()
        (self.brein / "geboortebewijs.json").write_text(json.dumps({
            "boom_id": "x", "profiel": "tweede-brein", "machine": "mac",
            "locatie": str(self.brein), "geplant_op": "2026-09-03T20:00:00+00:00"}),
            encoding="utf-8")
        from kern.growkit_oerwoud import sla_brein_pad
        sla_brein_pad(self.brein)

    def tearDown(self):
        if self._oude_env is None:
            os.environ.pop("GROWKIT_OERWOUD_STAAT", None)
        else:
            os.environ["GROWKIT_OERWOUD_STAAT"] = self._oude_env
        self._tmp.cleanup()

    def test_kiemkeuze_toont_brein_opties_gemarkeerd(self):
        import contextlib
        import io
        import loop
        uit = io.StringIO()
        with contextlib.redirect_stdout(uit):
            try:
                loop.plant_profiel(invoer_fn=lambda _: "q")
            except StopIteration:
                pass
        self.assertIn("logboeken (uit je brein)", uit.getvalue())

    def test_brein_optie_is_advies_en_wordt_net_geweigerd(self):
        import contextlib
        import io
        import loop
        uit = io.StringIO()
        with contextlib.redirect_stdout(uit):
            code = loop.plant_profiel(invoer_fn=lambda _: "logboeken (uit je brein)")
        self.assertEqual(code, 1)
        self.assertIn("geen actie", uit.getvalue().lower())
        self.assertNotIn("Traceback", uit.getvalue())

    def test_vrije_garbage_wordt_ook_geweigerd_zonder_crash(self):
        """Latente bug gedicht: een getypte naam die geen profiel is mag niet
        tot een FileNotFoundError leiden."""
        import contextlib
        import io
        import loop
        uit = io.StringIO()
        with contextlib.redirect_stdout(uit):
            code = loop.plant_profiel(invoer_fn=lambda _: "niet-een-profiel")
        self.assertEqual(code, 1)
        self.assertIn("geen bewezen profiel", uit.getvalue().lower())


if __name__ == "__main__":
    unittest.main()
