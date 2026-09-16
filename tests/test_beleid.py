"""Slice S12 — ThreatLocker politiek-laag per agent.

Elke agent krijgt een beleidsobject: mag/niet-mag per actiesoort.
Eerste bewijs: een agent zonder toegestane actie wordt geweigerd
vóór uitvoering — de weigering komt vóór de aanroep, niet erna.
"""
import unittest

from kern import growkit_beleid as bl


class TestBeleidsobject(unittest.TestCase):
    def test_beleid_voor_vigil_komt_uit_het_register(self):
        beleid = bl.beleid_voor("vigil")
        self.assertEqual(beleid["toegestaan"], ["lezen", "schrijven", "netwerk"])

    def test_onbekende_agent_krijgt_ook_leeg_beleid(self):
        # beleid kent alleen wat in het register staat; de rest is dicht
        self.assertEqual(bl.beleid_voor("onbekende-agent")["toegestaan"], [])

    def test_register_hoort_bij_de_familie(self):
        uit = bl.alle_beleidsobjecten()
        namen = {b["agent"] for b in uit}
        self.assertIn("KairOS", namen)
        self.assertIn("Genius", namen)


class TestWeigerenVoorUitvoering(unittest.TestCase):
    def test_actie_zonder_toestemming_wordt_geweigerd(self):
        # Vigil mag schrijven, niet wissen
        self.assertFalse(bl.toegestaan("vigil", "wissen"))

    def test_toegestane_actie_wordt_doorgelaten(self):
        self.assertTrue(bl.toegestaan("vigil", "schrijven"))

    def test_geen_agent_gaat_voorbij_gesloten_standaard(self):
        # gesloten standaard: wat niet expliciet is toegestaan, mag niet
        for agent in ("kairos", "riri", "vigil", "libra", "memoria",
                      "codex", "genius"):
            self.assertFalse(bl.toegestaan(agent, "wissen"),
                             f"{agent} mag nooit automatisch wissen")

    def test_weigering_noemt_de_actie_en_de_regel(self):
        r = bl.controleer("vigil", "wissen")
        self.assertFalse(r["ok"])
        self.assertIn("wissen", r["weigering"])
        self.assertIn("beleid", r["weigering"])

    def test_genius_observer_mag_niets_uitvoeren(self):
        # governor-wet: de observer voert niets uit
        for actie in ("schrijven", "netwerk", "wissen", "systeem"):
            self.assertFalse(bl.toegestaan("genius", actie),
                             f"observer mag geen {actie}")


if __name__ == "__main__":
    unittest.main()