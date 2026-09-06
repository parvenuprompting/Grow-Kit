"""Adapter-tests voor de Digitale Kloon-commando's."""
import unittest
from unittest import mock
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))
import adapter  # noqa: E402
from kern import growkit_kloon as kloon  # noqa: E402


class TestKloonAdapter(unittest.TestCase):
    def test_categorieen(self):
        uit = adapter.COMMANDOS["klooncategorieen"]({})
        self.assertEqual(set(uit["data"]["categorieen"]),
                         {"wachtwoord", "apikey", "bank", "crypto", "account"})

    def test_lijst(self):
        with mock.patch.object(kloon, "lijst", return_value=[{"id": "a", "titel": "X"}]):
            uit = adapter.COMMANDOS["kloonlijst"]({})
        self.assertEqual(uit["data"]["items"][0]["titel"], "X")

    def test_toevoegen_verplicht(self):
        with self.assertRaises(adapter.AdapterFout):
            adapter.COMMANDOS["kloontoevoegen"]({"titel": "X"})

    def test_toevoegen_geeft_geen_cijfertekst_terug(self):
        item = {"id": "a", "titel": "X", "velden_versleuteld": {"Key": "cipher"}}
        with mock.patch.object(kloon, "voeg_toe", return_value=item):
            uit = adapter.COMMANDOS["kloontoevoegen"]({
                "titel": "X", "categorie": "apikey", "velden": {"Key": "secret"}
            })
        self.assertNotIn("secret", str(uit))
        self.assertEqual(uit["data"]["item"]["velden_versleuteld"], ["Key"])

    def test_lees_verplicht_id(self):
        with self.assertRaises(adapter.AdapterFout):
            adapter.COMMANDOS["kloonlees"]({})

    def test_lees_item(self):
        with mock.patch.object(kloon, "lees_item", return_value={"id": "a", "velden_ontsleuteld": {"Key": "x"}}):
            uit = adapter.COMMANDOS["kloonlees"]({"id": "a"})
        self.assertEqual(uit["data"]["item"]["id"], "a")

    def test_verwijder(self):
        with mock.patch.object(kloon, "verwijder", return_value=True):
            uit = adapter.COMMANDOS["kloonverwijder"]({"id": "a"})
        self.assertEqual(uit["data"]["verwijderd"], "a")


if __name__ == "__main__":
    unittest.main()
