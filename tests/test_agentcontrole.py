"""Slice D — tests voor agentcontrole: ophalen wat af is, uitspraak doen.

Offline: SSH-uitvoerder geïnjecteerd. Bewijsvruchten:
- ophalen leest alleen afgerond/*.json en verplaatst ze naar controle/
- goedkeuren/afkeuren verplaatst naar de juiste map en keurt in het register
- fouten zijn nette fouten, nooit tracebacks
"""
import json
import re
import unittest

from kern import growkit_agentcontrole as ac

_W = ac.WACHTRIJ_ROOT
_PAD = re.compile(re.escape(_W) + r"/(\w+)/(\w+)/([\w-]+\.json)")


class NepSSH:
    """Speelt de VPS-bestanden in een dict, keyed op vol pad."""

    def __init__(self, bestanden: dict[str, str] | None = None, faal=False):
        self.fs = dict(bestanden or {})
        self.verplaatst: list[tuple[str, str]] = []
        self.faal = faal

    def __call__(self, commando: list[str], stdin: str | None,
                 timeout: int) -> tuple[int, str]:
        if self.faal:
            return 1, ""
        regel = commando[-1]
        # mv BRON DOEL
        m = re.match(r"^mv (\S+) (\S+)$", regel)
        if m:
            bron, doel = m.group(1), m.group(2)
            if bron not in self.fs:
                return 1, ""
            self.fs[doel] = self.fs.pop(bron)
            self.verplaatst.append((bron, doel))
            return 0, ""
        # ls-pad (afgerond/controle): "ls PAD/*.json 2>/dev/null"
        m = re.match(r"^ls (\S+) 2>/dev/null$", regel)
        if m:
            pad = m.group(1).split("/*")[0]
            uit = "\n".join(k for k in self.fs if k.startswith(pad + "/")
                            and k.endswith(".json"))
            return 0, uit
        # cat
        m = re.match(r"^cat (\S+)$", regel)
        if m:
            if m.group(1) not in self.fs:
                return 1, ""
            return 0, self.fs[m.group(1)]
        return 2, "onbekend commando"


def _taak(agent: str, taak_id: str) -> str:
    return json.dumps({"taak_id": taak_id, "agent": agent,
                       "titel": f"Taak {taak_id}",
                       "bewijs": "shell_check ok", "bron": "agent-zelf"})


class TestAgentControle(unittest.TestCase):
    def test_ophalen_leest_afgerond_en_verplaatst_naar_controle(self):
        bron = f"{_W}/vigil/afgerond/taak-9.json"
        ssh = NepSSH({bron: _taak("vigil", "taak-9")})
        r = ac.ophalen(uitvoerder=ssh)
        self.assertTrue(r["ok"])
        self.assertEqual(len(r["data"]["afgerond"]), 1)
        item = r["data"]["afgerond"][0]
        self.assertEqual(item["agent"], "vigil")
        self.assertEqual(item["taak_id"], "taak-9")
        doel = f"{_W}/vigil/controle/taak-9.json"
        self.assertIn((bron, doel), ssh.verplaatst)

    def test_ophalen_van_leeg_is_leeg(self):
        ssh = NepSSH()
        r = ac.ophalen(uitvoerder=ssh)
        self.assertTrue(r["ok"])
        self.assertEqual(r["data"]["afgerond"], [])

    def test_uitspraak_goedkeurt_en_archiveert(self):
        bron = f"{_W}/vigil/controle/taak-9.json"
        ssh = NepSSH({bron: _taak("vigil", "taak-9")})
        r = ac.besluit("vigil", "taak-9", goed=True, uitvoerder=ssh)
        self.assertTrue(r["ok"])
        self.assertIn((bron, f"{_W}/vigil/goedgekeurd/taak-9.json"),
                      ssh.verplaatst)

    def test_uitspraak_afkeuren_archiveert_anders(self):
        bron = f"{_W}/vigil/controle/taak-9.json"
        ssh = NepSSH({bron: _taak("vigil", "taak-9")})
        r = ac.besluit("vigil", "taak-9", goed=False, uitvoerder=ssh)
        self.assertTrue(r["ok"])
        self.assertIn((bron, f"{_W}/vigil/afgekeurd/taak-9.json"),
                      ssh.verplaatst)

    def test_onbekende_agent_geweigerd(self):
        r = ac.besluit("hacker", "taak-1", goed=True, uitvoerder=NepSSH())
        self.assertFalse(r["ok"])

    def test_vps_faal_is_nette_fout(self):
        bron = f"{_W}/vigil/afgerond/taak-9.json"
        ssh = NepSSH({bron: _taak("vigil", "taak-9")}, faal=True)
        r = ac.ophalen(uitvoerder=ssh)
        self.assertFalse(r["ok"])


if __name__ == "__main__":
    unittest.main()
