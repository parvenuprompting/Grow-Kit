"""VOORSTEL-doorstroom (§13, taak 4): sync is append-only en gemarkeerd.

Regels:
- VOORSTEL-bestanden = bestanden in de boom-inbox met de prefix `VOORSTEL-`.
- Doorstroom: append-only kopie naar de brein-inbox als
  `VOORSTEL-<boom_id>-<naam>`; per bestand een gebeurtenis in het boom-logboek.
- Drift-guard, hard: zonder prefix reist er NIETS — REGELS.md, logboeken,
  geboortebewijs, willekeurige bestanden blijven thuis.
- Naam-collisie in de brein-inbox → weigering, nooit overschrijven.
- Tweemaal doorsturen → geen duplicaten (verzonden staat in het boom-logboek).
"""
import json
import tempfile
import unittest
import uuid
from pathlib import Path

from kern.growkit_oerwoud import stuur_voorstellen


class Basis(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.brein = Path(self._tmp.name) / "brein"
        self.boom = Path(self._tmp.name) / "boom"
        for map_ in (self.brein, self.boom):
            (map_ / "inbox").mkdir(parents=True)
            (map_ / "geboortebewijs.json").write_text(json.dumps({
                "boom_id": str(uuid.uuid4()), "profiel": "tweede-brein",
                "machine": "mac", "locatie": str(map_.resolve()),
                "geplant_op": "2026-09-03T20:00:00+00:00"}), encoding="utf-8")
            (map_ / "logboek.json").write_text("[]", encoding="utf-8")
        (self.brein / "inbox" / "REGELS.md").write_text("brein-regels", encoding="utf-8")
        (self.boom / "inbox" / "REGELS.md").write_text("boom-regels", encoding="utf-8")

    def tearDown(self):
        self._tmp.cleanup()

    def _voorstel(self, naam: str, inhoud: str) -> None:
        (self.boom / "inbox" / naam).write_text(inhoud, encoding="utf-8")


class TestDoorstroom(Basis):
    def test_voorstel_komt_met_prefix_in_de_brein_inbox(self):
        self._voorstel("VOORSTEL-nieuw-inzicht.md", "blijkbaar wil deze gebruiker altijd X")
        verzonden, namen = stuur_voorstellen(self.boom, self.brein)
        self.assertEqual(verzonden, 1)
        boom_id = json.loads((self.boom / "geboortebewijs.json").read_text(encoding="utf-8"))["boom_id"]
        verwacht = f"VOORSTEL-{boom_id}-nieuw-inzicht.md"
        self.assertEqual(namen, [verwacht])
        doel_bestand = self.brein / "inbox" / verwacht
        self.assertTrue(doel_bestand.exists())
        self.assertEqual(doel_bestand.read_text(encoding="utf-8"),
                         "blijkbaar wil deze gebruiker altijd X")
        # de boom-inbox behoudt het origineel (niets verplaatst)
        self.assertTrue((self.boom / "inbox" / "VOORSTEL-nieuw-inzicht.md").exists())

    def test_doorstroom_wordt_append_only_gelgd(self):
        self._voorstel("VOORSTEL-a.md", "a")
        bestaand = [{"stap": "stap-001", "status": "geslaagd", "bewijs": "eerder"}]
        (self.boom / "logboek.json").write_text(json.dumps(bestaand), encoding="utf-8")
        stuur_voorstellen(self.boom, self.brein)
        entries = json.loads((self.boom / "logboek.json").read_text(encoding="utf-8"))
        self.assertEqual(entries[0], bestaand[0])
        doorstroom = [e for e in entries if e.get("type") == "doorstroom"]
        self.assertEqual(len(doorstroom), 1)
        self.assertIn("VOORSTEL-a.md", doorstroom[0]["bewijs"])

    def test_meerdere_voorstellen_reizen_allemaal(self):
        self._voorstel("VOORSTEL-a.md", "a")
        self._voorstel("VOORSTEL-b.md", "b")
        verzonden, _ = stuur_voorstellen(self.boom, self.brein)
        self.assertEqual(verzonden, 2)


class TestDriftGuard(Basis):
    def test_zonder_prefix_reist_er_niets(self):
        """Drift-guard: REGELS.md, root-bestanden en niet-gemarkeerde bestanden
        blijven thuis — ook al staan ze in de boom."""
        (self.boom / "REGELS.md").write_text("root-regels", encoding="utf-8")
        (self.boom / "inbox" / "notitie-zonder-prefix.md").write_text(" privé", encoding="utf-8")
        (self.boom / "inbox" / "logboek-zonder-prefix.json").write_text("[]", encoding="utf-8")
        verzonden, _ = stuur_voorstellen(self.boom, self.brein)
        self.assertEqual(verzonden, 0)
        brein_inhoud = sorted(p.name for p in (self.brein / "inbox").iterdir())
        self.assertEqual(brein_inhoud, ["REGELS.md"])         # niets extra gekomen

    def test_logboeken_en_paden_reisen_nooit(self):
        """Drift-guard: het echte boom-logboek en geboortebewijs reizen nooit —
        uitsluitend de gemarkeerde VOORSTEL-kopie belandt in de brein-inbox."""
        (self.boom / "inbox" / "VOORSTEL-inzicht.md").write_text("inzicht", encoding="utf-8")
        stuur_voorstellen(self.boom, self.brein)
        self.assertEqual((self.brein / "logboek.json").read_text(encoding="utf-8"), "[]")
        brein_id = json.loads((self.brein / "geboortebewijs.json").read_text(encoding="utf-8"))["boom_id"]
        boom_id = json.loads((self.boom / "geboortebewijs.json").read_text(encoding="utf-8"))["boom_id"]
        self.assertNotEqual(brein_id, boom_id)                   # het brein-bewijs is onaangetast
        brein_inbox = sorted(p.name for p in (self.brein / "inbox").iterdir()
                             if p.name != "REGELS.md")
        self.assertEqual(len(brein_inbox), 1)
        self.assertTrue(brein_inbox[0].startswith("VOORSTEL-"))


class TestVeiligheid(Basis):
    def test_tweemaal_doorsturen_geeft_geen_duplicaten(self):
        self._voorstel("VOORSTEL-a.md", "a")
        verzonden1, _ = stuur_voorstellen(self.boom, self.brein)
        verzonden2, _ = stuur_voorstellen(self.boom, self.brein)
        self.assertEqual((verzonden1, verzonden2), (1, 0))
        brein_bestanden = [p.name for p in (self.brein / "inbox").iterdir()
                           if p.name.startswith("VOORSTEL-")]
        self.assertEqual(len(brein_bestanden), 1)

    def test_collisie_wordt_geweigerd_niet_overschreven(self):
        self._voorstel("VOORSTEL-a.md", "nieuw")
        boom_id = json.loads((self.boom / "geboortebewijs.json").read_text(encoding="utf-8"))["boom_id"]
        doel_bestand = self.brein / "inbox" / f"VOORSTEL-{boom_id}-a.md"
        doel_bestand.write_text("bestaand-origineel", encoding="utf-8")
        with self.assertRaises(ValueError) as ctx:
            stuur_voorstellen(self.boom, self.brein)
        self.assertIn("nooit overschrijven", str(ctx.exception))
        self.assertEqual(doel_bestand.read_text(encoding="utf-8"), "bestaand-origineel")

    def test_onbereikbaar_brein_is_nette_fout(self):
        self._voorstel("VOORSTEL-a.md", "a")
        with self.assertRaises(ValueError) as ctx:
            stuur_voorstellen(self.boom, Path(self._tmp.name) / "verdwenen")
        self.assertIn("onbereikbaar", str(ctx.exception).lower())


if __name__ == "__main__":
    unittest.main()
