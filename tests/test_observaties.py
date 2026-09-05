"""Slice E — tests voor observaties: Genius' voorstellen uit de brein-inbox.

Offline: SSH-uitvoerder geïnjecteerd. Alleen-lezen: lijst + cat, niets anders.
"""
import json
import re
import unittest

from kern import growkit_observaties as ob

_PAD = re.compile(re.escape(ob.INBOX) + r"/\S+")


class NepSSH:
    def __init__(self, bestanden: dict[str, str] | None = None, faal=False):
        self.fs = dict(bestanden or {})
        self.faal = faal
        self.commandos: list[str] = []

    def __call__(self, commando: list[str], stdin, timeout):
        if self.faal:
            return 1, ""
        regel = commando[-1]
        self.commandos.append(regel)
        m = re.match(r"^ls (\S+) 2>/dev/null$", regel)
        if m:
            pad = m.group(1).split("/*")[0]
            return 0, "\n".join(k for k in self.fs if k.startswith(pad + "/"))
        if regel.startswith("cat "):
            pad = regel[4:]
            if pad not in self.fs:
                return 1, ""
            return 0, self.fs[pad]
        return 2, ""


class TestObservaties(unittest.TestCase):
    def test_lijst_met_titel_en_afzender(self):
        pad = ob.INBOX + "/2026-09-05-voorstel.md"
        ssh = NepSSH({pad: "---\ntitel: \"Wekelijkse pitch — week 36\"\n"
                             "afzender: genius\n---\n# Voorstel\n\nDoe dit."})
        r = ob.lees(uitvoerder=ssh)
        self.assertTrue(r["ok"])
        self.assertEqual(len(r["data"]["voorstellen"]), 1)
        v = r["data"]["voorstellen"][0]
        self.assertEqual(v["titel"], "Wekelijkse pitch — week 36")
        self.assertEqual(v["afzender"], "genius")
        self.assertIn("Doe dit", v["inhoud"])

    def test_leeg_is_leeg(self):
        r = ob.lees(uitvoerder=NepSSH())
        self.assertTrue(r["ok"])
        self.assertEqual(r["data"]["voorstellen"], [])

    def test_ongeldig_document_kapot_niet_de_lijst(self):
        pad = ob.INBOX + "/kapot.md"
        ssh = NepSSH({pad: "geen frontmatter hier"})
        r = ob.lees(uitvoerder=ssh)
        self.assertTrue(r["ok"])
        self.assertEqual(r["data"]["voorstellen"][0]["titel"], "kapot.md")

    def test_faal_is_nette_fout(self):
        r = ob.lees(uitvoerder=NepSSH(faal=True))
        self.assertFalse(r["ok"])

    def test_alleen_lees_commandos(self):
        pad = ob.INBOX + "/x.md"
        ssh = NepSSH({pad: "---\ntitel: t\n---\ninhoud"})
        ob.lees(uitvoerder=ssh)
        for cmd in ssh.commandos:
            self.assertTrue(cmd.startswith("ls ") or cmd.startswith("cat "),
                            f"ongeoorloofd commando: {cmd}")


if __name__ == "__main__":
    unittest.main()
