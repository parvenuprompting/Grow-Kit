#!/usr/bin/env python3
"""Tests voor de goedkeurings-audit (kern/growkit_goedkeuring.py).

Kern: de uitleg moet in simpele taal zijn en kritische acties moeten
opvallen. De classifier zelf wordt getest op de gevarenklassen.
"""
import json
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).parent.parent
sys.path.insert(0, str(REPO))

from kern import growkit_goedkeuring as gk


class TestSoortEnRisico(unittest.TestCase):
    def test_lezen_is_groen(self):
        self.assertEqual(gk._soort_en_risico("ls -la", "shell"),
                         ("lezen", "groen", False))

    def test_bestand_schrijven_is_geel(self):
        soort, risico, _ = gk._soort_en_risico("cat <<'PY' > bestand.py", "shell")
        self.assertEqual((soort, risico), ("bestand schrijven", "geel"))

    def test_rm_is_rood_en_kritiek(self):
        self.assertEqual(gk._soort_en_risico("rm -rf build/", "shell"),
                         ("wissen", "rood", True))

    def test_git_push_is_geel(self):
        self.assertEqual(gk._soort_en_risico("git push origin main", "shell"),
                         ("git delen (push)", "geel", False))

    def test_branch_verwijderen_op_server_is_rood(self):
        self.assertEqual(gk._soort_en_risico("git push origin --delete feat/x", "shell"),
                         ("wissen (branch op de server)", "rood", True))

    def test_env_lezen_is_rood(self):
        soort, risico, krit = gk._soort_en_risico("cat .env", "shell")
        self.assertEqual((soort, risico), ("geheimbestand lezen", "rood"))
        self.assertTrue(krit)

    def test_systeem_aanpassing_is_rood(self):
        self.assertEqual(gk._soort_en_risico("sudo launchctl load x.plist", "shell"),
                         ("systeem aanpassen", "rood", True))

    def test_installeren_is_geel(self):
        soort, risico, _ = gk._soort_en_risico("pip install requests", "shell")
        self.assertEqual((soort, risico), ("software installeren", "geel"))

    def test_write_tool_is_schrijven(self):
        soort, risico, _ = gk._soort_en_risico("x", "Write")
        self.assertEqual((soort, risico), ("bestand schrijven", "geel"))

    def test_git_lezen_is_groen(self):
        self.assertEqual(gk._soort_en_risico("git log --oneline -5", "shell"),
                         ("git lezen", "groen", False))


class TestUitlegSimpeleTaal(unittest.TestCase):
    def test_uitleg_noemt_het_bestand(self):
        tekst = gk._uitleg_actie("bestand schrijven", "cat <<'PY' > server.py", "shell")
        self.assertIn("server.py", tekst)

    def test_uitleg_bestaat_voor_elke_soort(self):
        for soort in ("lezen", "wissen", "git delen (push)", "geheimbestand lezen",
                      "systeem aanpassen", "onduidelijk"):
            self.assertTrue(len(gk._UITLEG.get(soort, "")) > 10, soort)


class TestSamenvatting(unittest.TestCase):
    def test_leeg_geeft_net_antwoord(self):
        self.assertIn("Geen", gk.samenvatting([]))

    def _actie(self, **over):
        a = {"bron": "codex", "tijdstip": "2026-09-05T10:00", "tool": "shell",
             "actie": "ls", "soort": "lezen", "risico": "groen",
             "kritisch": False, "uitleg": "gelezen"}
        a.update(over)
        return a

    def test_samenvatting_noemt_kritiek(self):
        tekst = gk.samenvatting([
            self._actie(actie="rm -rf build/", soort="wissen", risico="rood",
                        kritisch=True, uitleg="verwijderd"),
            self._actie(),
        ])
        self.assertIn("verdienen je aandacht", tekst)
        self.assertIn("rm -rf build/", tekst)

    def test_samenvatting_zonder_kritiek_is_geruststellend(self):
        self.assertIn("Geen kritische acties", gk.samenvatting([self._actie()]))


class TestParsers(unittest.TestCase):
    def test_codex_parser_leest_shell_commands(self):
        with tempfile.TemporaryDirectory() as tmp:
            f = Path(tmp) / "sessie.jsonl"
            regels = [
                {"timestamp": "2026-09-05T10:00:00Z", "payload": {
                    "type": "function_call", "name": "shell_command",
                    "arguments": json.dumps({"command": "ls"})}},
                {"timestamp": "2026-09-05T10:01:00Z", "payload": {
                    "type": "function_call", "name": "apply_patch",
                    "arguments": "{}"}},
            ]
            f.write_text("\n".join(json.dumps(r) for r in regels), encoding="utf-8")
            acties = gk._parse_codex(f)
            self.assertEqual(len(acties), 2)
            self.assertEqual(acties[0]["actie"], "ls")
            self.assertEqual(acties[1]["tool"], "apply_patch")

    def test_claude_parser_leest_tool_use(self):
        with tempfile.TemporaryDirectory() as tmp:
            f = Path(tmp) / "proj" / "sessie.jsonl"
            f.parent.mkdir()
            d = {"timestamp": "2026-09-05T10:00:00Z",
                 "message": {"role": "assistant", "content": [
                     {"type": "tool_use", "name": "Bash",
                      "input": {"command": "git push origin main"}}]}}
            f.write_text(json.dumps(d), encoding="utf-8")
            acties = gk._parse_claude(f)
            self.assertEqual(len(acties), 1)
            self.assertEqual(acties[0]["actie"], "git push origin main")


if __name__ == "__main__":
    unittest.main()
