"""Testen voor het prompts-commando (prompt-bibliotheek, roadmap 5 sept).

De gecureerde prompts komen letterlijk (ongewijzigd) uit de privé-repo
audit-prompt-bibliotheek. Het commando leest, filtert en zoekt — het
genereert of herschrijft nooit.
"""
import json
import unittest

from adapter import cmd_prompts, AdapterFout

DATA = (__import__("pathlib").Path(__file__).resolve().parent.parent
        / "kern" / "data" / "prompt_bibliotheek.json")


class TestPrompts(unittest.TestCase):
    def test_data_bestand_bestaat_en_is_valide(self):
        ruw = json.loads(DATA.read_text(encoding="utf-8"))
        self.assertGreater(len(ruw["prompts"]), 100)
        self.assertGreater(len(ruw["domains"]), 20)

    def test_alleen_lezen_geeft_alle_prompts_en_domeinen(self):
        uit = cmd_prompts({})
        self.assertTrue(uit["ok"])
        self.assertEqual(len(uit["data"]["prompts"]), 125)
        self.assertEqual(len(uit["data"]["domains"]), 26)

    def test_filter_op_domein(self):
        uit = cmd_prompts({"domein": 1})
        self.assertTrue(uit["ok"])
        for p in uit["data"]["prompts"]:
            self.assertEqual(p["domainId"], 1)
        self.assertGreater(len(uit["data"]["prompts"]), 0)

    def test_filter_op_sectie(self):
        uit = cmd_prompts({"sectie": "custom_infra"})
        self.assertEqual(len(uit["data"]["prompts"]), 9)
        for p in uit["data"]["prompts"]:
            self.assertEqual(p["section"], "custom_infra")

    def test_zoek_op_tekst(self):
        uit = cmd_prompts({"zoek": "security"})
        self.assertTrue(uit["ok"])
        self.assertGreater(len(uit["data"]["prompts"]), 0)
        # match in titel, tags, scope of role — niet per se in content
        for p in uit["data"]["prompts"]:
            hooi = " ".join(str(p.get(k, "")) for k in
                            ("title", "tags", "scope", "role", "content")).lower()
            self.assertIn("security", hooi)

    def test_enkele_prompt_op_id(self):
        uit = cmd_prompts({"id": "1.1"})
        self.assertTrue(uit["ok"])
        self.assertEqual(len(uit["data"]["prompts"]), 1)
        self.assertEqual(uit["data"]["prompts"][0]["id"], "1.1")

    def test_onbekend_id_is_nette_fout(self):
        with self.assertRaises(AdapterFout):
            cmd_prompts({"id": "99.99"})

    def test_onbekende_sectie_is_nette_fout(self):
        with self.assertRaises(AdapterFout):
            cmd_prompts({"sectie": "bestaatniet"})

    def test_prompts_worden_letterlijk_doorgegeven(self):
        """De adapter mag niets wijzigen: veld-voor-veld gelijk aan de bron."""
        bron = {p["id"]: p for p in
                json.loads(DATA.read_text(encoding="utf-8"))["prompts"]}
        uit = cmd_prompts({"id": "1.1"})
        self.assertEqual(uit["data"]["prompts"][0], bron["1.1"])


if __name__ == "__main__":
    unittest.main()
