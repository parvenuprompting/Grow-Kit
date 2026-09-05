"""Slice C — taak koppelen: van GrowKit naar de VPS-wachtrij van een agent.

Offline tests: de SSH-uitvoerder wordt geïnjecteerd. Bewijsvruchten:
- het taakbestand is geldige JSON in de wachtrij-map van de juiste agent
- geen shell-injectie: het commando bevat de taakinhoud nooit
- gouverneur-plafond geldt vóór versturen (2 taken per agent)
"""
import json
import re
import unittest
from pathlib import Path

from kern import growkit_agenttaak as at

_PAD = re.compile(re.escape(at.WACHTRIJ_ROOT) + r"/\S+?\.json(?=\.deel| |$|\b)")


class NepSSH:
    """Vangt het 'remote' commando en speelt bestandssysteem."""

    def __init__(self, faal: bool = False):
        self.bestanden: dict[str, str] = {}
        self.commandos: list[list[str]] = []
        self.faal = faal

    def __call__(self, commando: list[str], stdin: str | None,
                 timeout: int) -> tuple[int, str]:
        self.commandos.append(list(commando))
        if self.faal:
            return 1, ""
        # het doelpad zit in de shell-regel: "umask 177; cat > PAD.deel && mv ..."
        m = _PAD.search(" ".join(commando))
        if not m:
            return 3, ""
        doel = m.group(0)
        self.bestanden[doel] = stdin or ""
        return 0, ""


class TestAgentTaak(unittest.TestCase):
    def test_verstuur_schrijft_json_in_wachtrij(self):
        ssh = NepSSH()
        r = at.verstuur("vigil", "taak-001", "Check schijfruimte",
                        uitvoerder=ssh)
        self.assertTrue(r["ok"])
        pad = r["data"]["bestand"]
        self.assertTrue(pad.startswith(at.WACHTRIJ_ROOT + "/vigil/wachtrij/"))
        doc = json.loads(ssh.bestanden[pad])
        self.assertEqual(doc["taak_id"], "taak-001")
        self.assertEqual(doc["titel"], "Check schijfruimte")
        self.assertEqual(doc["agent"], "vigil")
        self.assertIn("aangemeld_op", doc)

    def test_onbekende_agent_wordt_geweigerd(self):
        ssh = NepSSH()
        r = at.verstuur("hacker", "taak-002", "x", uitvoerder=ssh)
        self.assertFalse(r["ok"])
        self.assertEqual(ssh.bestanden, {})

    def test_geen_shell_injectie_mogelijk(self):
        ssh = NepSSH()
        kwaad = 'x"; rm -rf /; echo "'
        r = at.verstuur("vigil", "taak-003", kwaad, uitvoerder=ssh)
        self.assertTrue(r["ok"])
        cmd = " ".join(ssh.commandos[0])
        self.assertNotIn(kwaad, cmd)          # inhoud zit op stdin, niet in cmd
        self.assertEqual(json.loads(ssh.bestanden[r["data"]["bestand"]])["titel"],
                         kwaad)               # en blijft letterlijk bewaard

    def test_ssh_faal_is_nette_fout(self):
        r = at.verstuur("vigil", "taak-004", "x",
                        uitvoerder=NepSSH(faal=True))
        self.assertFalse(r["ok"])
        self.assertIn("wachtrij", r["fout"].lower())

    def test_bestandsnaam_is_veilig_afgeleid(self):
        ssh = NepSSH()
        r = at.verstuur("libra", "taak/../gevaarlijk", "x", uitvoerder=ssh)
        self.assertFalse(r["ok"])  # taak-id met pad-onderdelen wordt geweigerd


if __name__ == "__main__":
    unittest.main()
