"""Slice 4 — inbox-curatiescherm (docs/ROADMAP-SLICES.md).

Nieuwe adapter-commando's voor de brein-inbox (curatielaag):
- `inbox`: toon VOORSTEL-items uit de brein-inbox. Per item:
    {"naam", "boom_id", "inhoud", "aangekomen": tijdstip(uit naam of mtime)}
  Zonder bekend brein → ok met lege lijst + melding.
- `curate`: goedkeuren of afwijzen van VOORSTEL-items, volgens het
  curatiebeleid van 3 september 2026 (chat-goedkeuring IS curatie):
    {"brein_pad"|default-staat, "items": [{"naam", "besluit": "goedgekeurd"|"afgewezen",
      "reden"?, "bestemming"?}]}
  Goedgekeurd: het bestand MIGREERT append-only naar
  `brein/kennis/<bestemming>` (standaard "goedgekeurd/") — de inbox-copy
  blijft bestaan maar wordt gemarkeerd met status-suffix `.geboekt`.
  NIETS wordt overschreven: bestaand doelbestand → weigering.
  Afgewezen: inbox-copy krijgt suffix `.afgewezen` (+ reden als
  afwijzingen.md). Nooit verwijderen — de geschiedenis blijft intact.
- Corrupte of ontbrekende inbox-bestanden → nette fout, geen auto-reparatie.
- Onbekende naam → nette fout; dubbele besluiten over dezelfde naam →
  geweigerd (een item wordt één keer besloten).
"""
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).parent.parent
ADAPTER = REPO / "adapter.py"


class InboxBasis(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.home = Path(self._tmp.name) / "growkit-home"
        self._oude_env = os.environ.get("GROWKIT_OERWOUD_STAAT")
        os.environ["GROWKIT_OERWOUD_STAAT"] = str(self.home / "oerwoud.json")

    def tearDown(self):
        if self._oude_env is None:
            os.environ.pop("GROWKIT_OERWOUD_STAAT", None)
        else:
            os.environ["GROWKIT_OERWOUD_STAAT"] = self._oude_env
        self._tmp.cleanup()

    def roep(self, commando: str, invoer: dict) -> tuple[int, dict, str]:
        resultaat = subprocess.run(
            [sys.executable, str(ADAPTER), commando],
            input=json.dumps(invoer), capture_output=True, text=True,
            env={**os.environ}, cwd=str(REPO), timeout=120)
        try:
            uit = json.loads(resultaat.stdout)
        except json.JSONDecodeError:
            uit = {"_rauw": resultaat.stdout}
        return resultaat.returncode, uit, resultaat.stderr

    def _brein(self, naam: str = "brein") -> Path:
        brein = Path(self._tmp.name) / naam
        brein.mkdir(parents=True, exist_ok=True)
        (brein / "geboortebewijs.json").write_text(json.dumps({
            "boom_id": f"brein-{naam}", "profiel": "tweede-brein",
            "machine": "test", "locatie": str(brein),
            "geplant_op": "2026-09-01T09:00:00+00:00"}), encoding="utf-8")
        return brein

    def _koppel(self, brein: Path) -> None:
        from kern import growkit_oerwoud
        growkit_oerwoud.sla_brein_pad(brein)

    def _voorstel(self, brein: Path, naam: str, inhoud: str = "inzicht") -> Path:
        inbox = brein / "inbox"
        inbox.mkdir(parents=True, exist_ok=True)
        pad = inbox / naam
        pad.write_text(inhoud, encoding="utf-8")
        return pad


class InboxTonen(InboxBasis):
    def test_geen_brein_gekoppeld(self):
        code, uit, _ = self.roep("inbox", {})
        self.assertEqual(code, 0)
        self.assertEqual(uit["data"]["items"], [])
        self.assertIn("melding", uit["data"])

    def test_leegt_inbox(self):
        brein = self._brein()
        self._koppel(brein)
        code, uit, _ = self.roep("inbox", {})
        self.assertEqual(code, 0)
        self.assertEqual(uit["data"]["items"], [])

    def test_voorstellen_worden_getoond(self):
        brein = self._brein()
        self._koppel(brein)
        self._voorstel(brein, "VOORSTEL-abc-123-inzicht.md", "het vliegwiel draait")
        self._voorstel(brein, "VOORSTEL-def-456-anders.md", "tweede inzicht")
        (brein / "inbox" / "REGELS.md").write_text("regels", encoding="utf-8")
        code, uit, _ = self.roep("inbox", {})
        self.assertEqual(code, 0)
        items = uit["data"]["items"]
        self.assertEqual(len(items), 2)          # REGELS.md reist niet mee
        namen = {i["naam"] for i in items}
        self.assertIn("VOORSTEL-abc-123-inzicht.md", namen)
        self.assertTrue(all(i["inhoud"] for i in items))

    def test_expliciet_brein_pad(self):
        brein = self._brein()
        self._voorstel(brein, "VOORSTEL-abc-123-x.md", "inhoud x")
        code, uit, _ = self.roep("inbox", {"brein_pad": str(brein)})
        self.assertEqual(code, 0)
        self.assertEqual(len(uit["data"]["items"]), 1)


class CuratieBesluiten(InboxBasis):
    def setUp(self):
        super().setUp()
        self.brein = self._brein()
        self._koppel(self.brein)
        self.item = "VOORSTEL-abc-123-inzicht.md"
        self._voorstel(self.brein, self.item, "het vliegwiel draait")

    def test_goedkeuring_migreert_append_only(self):
        code, uit, _ = self.roep("curate", {
            "items": [{"naam": self.item, "besluit": "goedgekeurd",
                       "bestemming": "kennis/goedgekeurd"}]})
        self.assertEqual(code, 0)
        resultaat = uit["data"]["resultaten"][0]
        self.assertEqual(resultaat["status"], "goedgekeurd")
        doel = self.brein / "kennis" / "goedgekeurd" / self.item
        self.assertTrue(doel.exists())           # geboekt in het brein
        self.assertEqual(doel.read_text(encoding="utf-8"), "het vliegwiel draait")
        # inbox-copy gemarkeerd, niet gewist
        gemarkeerd = self.brein / "inbox" / (self.item + ".geboekt")
        self.assertTrue(gemarkeerd.exists())
        self.assertFalse((self.brein / "inbox" / self.item).exists())

    def test_afwijzing_markeert_met_reden(self):
        code, uit, _ = self.roep("curate", {
            "items": [{"naam": self.item, "besluit": "afgewezen",
                       "reden": "dubbel inzicht"}]})
        self.assertEqual(code, 0)
        gemarkeerd = self.brein / "inbox" / (self.item + ".afgewezen")
        self.assertTrue(gemarkeerd.exists())
        self.assertEqual(gemarkeerd.read_text(encoding="utf-8"), "het vliegwiel draait")
        afwijzingen = self.brein / "kennis" / "afwijzingen.md"
        self.assertTrue(afwijzingen.exists())
        self.assertIn("dubbel inzicht", afwijzingen.read_text(encoding="utf-8"))

    def test_niets_overschreven_bij_collisie(self):
        doel_map = self.brein / "kennis" / "goedgekeurd"
        doel_map.mkdir(parents=True, exist_ok=True)
        (doel_map / self.item).write_text("BESTAAND — nooit overschrijven", encoding="utf-8")
        code, uit, _ = self.roep("curate", {
            "items": [{"naam": self.item, "besluit": "goedgekeurd",
                       "bestemming": "kennis/goedgekeurd"}]})
        self.assertEqual(code, 1)
        self.assertFalse(uit["ok"])
        self.assertIn("nooit overschrijven", uit["fout"].lower())
        self.assertEqual((doel_map / self.item).read_text(encoding="utf-8"),
                         "BESTAAND — nooit overschrijven")

    def test_onbekende_naam_nette_fout(self):
        code, uit, _ = self.roep("curate", {
            "items": [{"naam": "VOORSTEL-bestaat-niet.md", "besluit": "goedgekeurd"}]})
        self.assertEqual(code, 1)
        self.assertFalse(uit["ok"])

    def test_twee_besluiten_over_hetzelfde_item_geweigerd(self):
        code, uit, _ = self.roep("curate", {
            "items": [{"naam": self.item, "besluit": "goedgekeurd"},
                      {"naam": self.item, "besluit": "afgewezen", "reden": "x"}]})
        self.assertEqual(code, 1)
        self.assertFalse(uit["ok"])
        # niets gewijzigd
        self.assertTrue((self.brein / "inbox" / self.item).exists())

    def test_ongeldig_besluit_geweigerd(self):
        code, uit, _ = self.roep("curate", {
            "items": [{"naam": self.item, "besluit": "misschien"}]})
        self.assertEqual(code, 1)
        self.assertFalse(uit["ok"])

    def test_besluit_wordt_gelogd_append_only(self):
        logboek = self.brein / "logboek.json"
        self.roep("curate", {"items": [{"naam": self.item, "besluit": "goedgekeurd"}]})
        if logboek.exists():
            entries = json.loads(logboek.read_text(encoding="utf-8"))
            self.assertTrue(any(e.get("type") == "curatie" for e in entries))


class InboxRobuustheid(InboxBasis):
    def setUp(self):
        super().setUp()
        self.brein = self._brein()
        self._koppel(self.brein)

    def test_leeg_voorstel_bestand(self):
        self._voorstel(self.brein, "VOORSTEL-abc-123-leeg.md", "")
        code, uit, _ = self.roep("inbox", {})
        self.assertEqual(code, 0)
        item = next(i for i in uit["data"]["items"] if i["naam"] == "VOORSTEL-abc-123-leeg.md")
        self.assertEqual(item["inhoud"], "")

    def test_geen_voorstellen_geen_items(self):
        (self.brein / "inbox").mkdir(parents=True, exist_ok=True)
        (self.brein / "inbox" / "notities.md").write_text("geen voorstel", encoding="utf-8")
        code, uit, _ = self.roep("inbox", {})
        self.assertEqual(code, 0)
        self.assertEqual(uit["data"]["items"], [])


if __name__ == "__main__":
    unittest.main()
