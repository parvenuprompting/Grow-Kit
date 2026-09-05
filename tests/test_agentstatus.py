"""Slice B — tests voor agentstatus (offline: uitvoerder wordt geïnjecteerd)."""
import unittest

from kern import growkit_agentstatus as gs


def nep_uitvoerder(stdout: str, code: int = 0):
    def run(commando, timeout):
        return code, stdout
    return run


class TestAgentStatus(unittest.TestCase):
    def test_alle_actief(self):
        uit = "hermes-gateway-kairos active\nhermes-gateway-researchos active\n" \
              "hermes-gateway-vigil active\nhermes-gateway-libra active\n" \
              "hermes-gateway-memoria active\nhermes-gateway-codex active\n" \
              "hermes-gateway-genius active\n"
        r = gs.verzamel_status(uitvoerder=nep_uitvoerder(uit))
        self.assertTrue(r["ok"])
        self.assertEqual(len(r["agents"]), 7)
        self.assertTrue(all(a["status"] == "active" for a in r["agents"]))

    def test_een_uit_valt_op(self):
        uit = "hermes-gateway-vigil inactive\n"
        r = gs.verzamel_status(uitvoerder=nep_uitvoerder(uit))
        vigil = [a for a in r["agents"] if a["agent"] == "vigil"][0]
        self.assertEqual(vigil["status"], "inactive")
        self.assertTrue(r["ok"])  # anderen leven nog

    def test_allemaal_uit_geeft_waarschuwing(self):
        r = gs.verzamel_status(uitvoerder=nep_uitvoerder(""))
        self.assertEqual(r["fout"], "Geen enkele gateway meldt zich actief.")

    def test_ssh_faalt_nettig(self):
        r = gs.verzamel_status(uitvoerder=nep_uitvoerder("", code=255))
        self.assertFalse(r["ok"])
        self.assertIn("onbereikbaar", r["fout"])

    def test_geen_agent_vervalt_naar_onbekend(self):
        r = gs.verzamel_status(uitvoerder=nep_uitvoerder("hermes-gateway-vigil active\n"))
        genius = [a for a in r["agents"] if a["agent"] == "genius"][0]
        self.assertEqual(genius["status"], "onbekend")


if __name__ == "__main__":
    unittest.main()
