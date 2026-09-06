"""Testen voor chat-geschiedenis: wis (→archief), lees, definitief wissen.

Besluit 6 sept: 'sessie wissen' = leesweergave leegmaken, berichten gaan
naar <agent>/geschiedenis/ op de VPS. Definitief wissen vereist bevestig.
"""
import json
import re
import unittest

from kern import growkit_agentchat as ac
from kern import growkit_agenttaak as at

_PAD = re.compile(re.escape(at.WACHTRIJ_ROOT) + r"/(\w+)/(\w+)/([\w.-]+\.json)")


class NepSSH:
    """Simuleert de VPS inclusief mv/rm tussen mappen."""

    def __init__(self, bestanden=None):
        self.fs = dict(bestanden or {})

    def __call__(self, commando, stdin, timeout):
        regel = commando[-1]
        if stdin is not None and "cat >" in regel:
            m = _PAD.search(regel)
            if not m:
                return 3, ""
            self.fs[m.group(0)] = stdin
            return 0, ""
        if "mkdir -p" in regel and "mv" in regel and "geschiedenis/" in regel:
            # wis_draad (multiline): verplaats alle json naar geschiedenis/;
            # antwoorden krijgen prefix antwoord- (geen naam-botsing)
            basis = at.WACHTRIJ_ROOT
            for pad in list(self.fs):
                if pad.startswith(basis + "/") and "/geschiedenis/" not in pad:
                    doc = self.fs[pad]
                    if '"agentchat"' in doc or "/antwoorden/" in pad:
                        if "/antwoorden/" in pad:
                            nieuw = pad.replace("/antwoorden/",
                                                "/geschiedenis/antwoord-")
                        else:
                            nieuw = pad.replace("/wachtrij/", "/geschiedenis/") \
                                .replace("/bezig/", "/geschiedenis/") \
                                .replace("/afgerond/", "/geschiedenis/")
                        self.fs[nieuw] = self.fs.pop(pad)
            return 0, "OK"
        if regel.startswith("for f in ") and "cat" in regel:
            marker = "===GROWKIT_BESTAND==="
            pad = regel[len("for f in "):].split("/*.json")[0]
            delen = []
            for k, inhoud in self.fs.items():
                if k.startswith(pad + "/") and k.endswith(".json"):
                    delen.append(marker + "\nFILE:" + k + "\n" + inhoud)
            return 0, "\n".join(delen)
        if regel.startswith("rm -f") and "geschiedenis" in regel:
            basis = regel.split("rm -f ")[1].split("/*.json")[0]
            for pad in list(self.fs):
                if pad.startswith(basis + "/"):
                    del self.fs[pad]
            return 0, "OK"
        return 2, "onbekend commando"


def _bericht(agent, taak_id, tekst):
    return json.dumps({"taak_id": taak_id, "agent": agent, "titel": tekst,
                       "bron": "agentchat", "aangemeld_op": "2026-09-06T10:00:00+00:00"})


class TestGeschiedenis(unittest.TestCase):
    def test_wis_draad_verplaatst_naar_archief(self):
        w = f"{at.WACHTRIJ_ROOT}/vigil/wachtrij/chat-010.json"
        ssh = NepSSH({w: _bericht("vigil", "chat-010", "oud bericht")})
        r = ac.wis_draad("vigil", uitvoerder=ssh)
        self.assertTrue(r["ok"])
        # draad is nu leeg
        draad = ac.draad("vigil", uitvoerder=ssh)
        self.assertEqual(draad["data"]["draad"], [])
        # geschiedenis heeft hem
        g = ac.geschiedenis("vigil", uitvoerder=ssh)
        self.assertEqual(len(g["data"]["geschiedenis"]), 1)
        self.assertEqual(g["data"]["geschiedenis"][0]["bericht"], "oud bericht")

    def test_geschiedenis_is_alleen_lezen_snapshot(self):
        w = f"{at.WACHTRIJ_ROOT}/codex/afgerond/chat-011.json"
        ssh = NepSSH({w: _bericht("codex", "chat-011", "afgerond bericht"),
                      f"{at.WACHTRIJ_ROOT}/codex/antwoorden/chat-011.json":
                          json.dumps({"taak_id": "chat-011", "antwoord": "klaar",
                                      "redenatie": "denk stap 1"})})
        r = ac.wis_draad("codex", uitvoerder=ssh)
        self.assertTrue(r["ok"])
        g = ac.geschiedenis("codex", uitvoerder=ssh)
        items = g["data"]["geschiedenis"]
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["bericht"], "afgerond bericht")
        self.assertEqual(items[0]["antwoord"], "klaar")
        self.assertEqual(items[0]["redenatie"], "denk stap 1")

    def test_definitief_wissen_zonder_bevestiging_weigerd(self):
        ssh = NepSSH()
        r = ac.wis_geschiedenis("codex", uitvoerder=ssh)
        self.assertFalse(r["ok"])
        self.assertIn("bevestiging", r["fout"])

    def test_definitief_wissen_met_bevestiging_leegt_archief(self):
        w = f"{at.WACHTRIJ_ROOT}/libra/geschiedenis/chat-012.json"
        ssh = NepSSH({w: _bericht("libra", "chat-012", "oud")})
        r = ac.wis_geschiedenis("libra", bevestig=True, uitvoerder=ssh)
        self.assertTrue(r["ok"])
        g = ac.geschiedenis("libra", uitvoerder=ssh)
        self.assertEqual(g["data"]["geschiedenis"], [])

    def test_onbekende_agent_geweigerd(self):
        ssh = NepSSH()
        self.assertFalse(ac.wis_draad("hacker", uitvoerder=ssh)["ok"])
        self.assertFalse(ac.geschiedenis("hacker", uitvoerder=ssh)["ok"])
        self.assertFalse(ac.wis_geschiedenis("hacker", bevestig=True,
                                             uitvoerder=ssh)["ok"])


class TestRedenatie(unittest.TestCase):
    def test_redenatie_uit_box(self):
        rauw = ("Query: test\n"
                "Initializing agent...\n"
                "╭─ ☤ Hermes ─────╮\n"
                "Ik denk na over het antwoord.\n"
                "╰────────────────╯\n"
                "Het antwoord zelf.")
        self.assertEqual(ac.redenatie_uit(rauw),
                         "Ik denk na over het antwoord.")

    def test_redenatie_leeg_zonder_box(self):
        self.assertIsNone(ac.redenatie_uit("Gewoon een antwoord."))

    def test_zuiver_antwoord_raakt_redenatie_niet_kapot(self):
        rauw = "╭─ ☤ Hermes ──╮\nDenkwerk.\n╰──────────────╯\nPuur antwoord."
        self.assertEqual(ac.zuiver_antwoord(rauw), "Puur antwoord.")
        self.assertEqual(ac.redenatie_uit(rauw), "Denkwerk.")


if __name__ == "__main__":
    unittest.main()
