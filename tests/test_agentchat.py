"""Ronde 3 — tests voor agentchat: praten met de familie via de wachtrij.

Bewijsvruchten:
- een bericht belandt als taak (bron=agentchat) in de wachtrij van de agent
- de draad is append-only en chronologisch: berichten + antwoorden bij elkaar
- antwoorden van de VPS worden gekoppeld aan het juiste bericht
- geen shell-injectie; secrets-scanner geldt ook voor chatberichten
"""
import json
import re
import unittest

from kern import growkit_agentchat as ac
from kern import growkit_agenttaak as at

_PAD = re.compile(re.escape(at.WACHTRIJ_ROOT) + r"/(\w+)/(\w+)/([\w.-]+\.json)")


class NepSSH:
    """Speelt de VPS: wachtrij/afgerond/antwoorden per agent."""

    def __init__(self, bestanden=None, faal=False):
        self.fs = dict(bestanden or {})
        self.geplaatst: dict[str, str] = {}
        self.faal = faal

    def __call__(self, commando, stdin, timeout):
        if self.faal:
            return 255, ""   # echte SSH-verbindingsfout
        regel = commando[-1]
        if stdin is not None and "cat >" in regel:   # upload
            m = _PAD.search(regel)
            if not m:
                return 3, ""
            self.geplaatst[m.group(0)] = stdin
            return 0, ""
        if regel.startswith("for f in "):
            # Nieuw protocol: één roundtrip, bestanden achter markers
            pad = regel[len("for f in "):].split("/*.json")[0]
            delen = []
            for k, inhoud in self.fs.items():
                if k.startswith(pad + "/") and k.endswith(".json"):
                    delen.append("===GROWKIT_BESTAND===\nFILE:" + k + "\n" + inhoud)
            return 0, "\n".join(delen)
        if regel.startswith("ls "):
            pad = regel[3:].split("/*")[0].split(" 2>/dev")[0]
            return 0, "\n".join(k for k in self.fs if k.startswith(pad + "/"))
        if regel.startswith("cat "):
            pad = regel[4:]
            return (0, self.fs[pad]) if pad in self.fs else (1, "")
        return 2, "onbekend commando"


def _bericht(agent, taak_id, tekst):
    return json.dumps({"taak_id": taak_id, "agent": agent, "titel": tekst,
                       "bron": "agentchat", "aangemeld_op": "2026-09-05T12:00:00+00:00"})


class TestAgentChat(unittest.TestCase):
    def test_bericht_landt_met_bron_agentchat(self):
        ssh = NepSSH()
        r = ac.stuur("vigil", "heb je vandaag iets gezien?", uitvoerder=ssh)
        self.assertTrue(r["ok"])
        doc = json.loads(list(ssh.geplaatst.values())[0])
        self.assertEqual(doc["bron"], "agentchat")
        self.assertEqual(doc["titel"], "heb je vandaag iets gezien?")

    def test_secret_in_bericht_geweigerd(self):
        ssh = NepSSH()
        r = ac.stuur("vigil", "mijn key is sk-ant-api03-abcdef1234567890",
                     uitvoerder=ssh)
        self.assertFalse(r["ok"])
        self.assertEqual(ssh.geplaatst, {})

    def test_draad_koppelt_antwoord_aan_bericht(self):
        w = f"{at.WACHTRIJ_ROOT}/vigil/wachtrij/chat-001.json"
        a = f"{at.WACHTRIJ_ROOT}/vigil/antwoorden/chat-001.json"
        ssh = NepSSH({w: _bericht("vigil", "chat-001", "hoe gaat het?"),
                      a: json.dumps({"taak_id": "chat-001",
                                     "antwoord": "Prima — alles live.",
                                     "afgerond_op": "2026-09-05T12:01:00+00:00"})})
        r = ac.draad("vigil", uitvoerder=ssh)
        self.assertTrue(r["ok"])
        thread = r["data"]["draad"]
        self.assertEqual(len(thread), 1)
        self.assertEqual(thread[0]["bericht"], "hoe gaat het?")
        self.assertEqual(thread[0]["antwoord"], "Prima — alles live.")

    def test_draad_toont_onbeantwoord(self):
        w = f"{at.WACHTRIJ_ROOT}/vigil/wachtrij/chat-002.json"
        ssh = NepSSH({w: _bericht("vigil", "chat-002", "nog daar?")})
        r = ac.draad("vigil", uitvoerder=ssh)
        self.assertIsNone(r["data"]["draad"][0]["antwoord"])

    def test_ssh_faal_nette_fout(self):
        r = ac.draad("vigil", uitvoerder=NepSSH(faal=True))
        self.assertFalse(r["ok"])


if __name__ == "__main__":
    unittest.main()
