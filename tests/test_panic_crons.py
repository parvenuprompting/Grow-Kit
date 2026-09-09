"""Tests voor growkit_panic_crons — Slice C: PANIC geldt ook voor zaadjes-crons.

De PANIC-knop pauzeert nu niet alleen Grow Kit-agents maar ook alle wakers/zijcronnen.
Bestandspatroon: /root/.hermes/wakers/panic-status.json (gedeeld met het Zaad).
Aan de cron-zijde leest elke waker vóór zijn run is_panic_actief; panic = script
sluit direct af met één logregel (zichtbaar stoppen, geen stille kill).
"""
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from kern import growkit_panic_crons as pc


class TestPanicCheck(unittest.TestCase):
    def test_geen_statusbestand_geen_panic(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertFalse(pc.is_panic_actief(Path(d)))

    def test_actieve_panic_wordt_gezien(self):
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / "panic-status.json").write_text(json.dumps({"actief": True, "reden": "test"}))
            self.assertTrue(pc.is_panic_actief(Path(d)))

    def test_gestopte_panic_is_niet_actief(self):
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / "panic-status.json").write_text(json.dumps({"actief": False, "reden": "x"}))
            self.assertFalse(pc.is_panic_actief(Path(d)))

    def test_corrupt_status_bestand_is_veilig_geen_panic(self):
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / "panic-status.json").write_text("{kapot")
            self.assertFalse(pc.is_panic_actief(Path(d)))


class TestWakerPoort(unittest.TestCase):
    def test_waker_gaat_door_zonder_panic(self):
        with tempfile.TemporaryDirectory() as d:
            ran, reden = pc.waker_poort(Path(d), naam="schijf-waker")
            self.assertTrue(ran)
            self.assertEqual(reden, "")

    def test_waker_stopt_netjes_met_panic(self):
        with tempfile.TemporaryDirectory() as d:
            pc.activeer_panic(Path(d), "test-stop")
            ran, reden = pc.waker_poort(Path(d), naam="schijf-waker")
            self.assertFalse(ran)
            self.assertIn("panic", reden)
            # logregel geschreven (zichtbaar stoppen)
            log = Path(d) / "waker-stilte.log"
            self.assertTrue(log.exists())
            self.assertIn("schijf-waker", log.read_text())

    def test_elke_stilte_logregel_heeft_tijdstip_en_naam(self):
        with tempfile.TemporaryDirectory() as d:
            pc.activeer_panic(Path(d), "test")
            pc.waker_poort(Path(d), naam="dienst-klok")
            pc.waker_poort(Path(d), naam="herstel-haan")
            regels = (Path(d) / "waker-stilte.log").read_text().strip().splitlines()
            self.assertEqual(len(regels), 2)
            self.assertIn("dienst-klok", regels[0])
            self.assertIn("herstel-haan", regels[1])


if __name__ == "__main__":
    unittest.main()
