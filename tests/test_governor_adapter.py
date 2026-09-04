#!/usr/bin/env python3
"""Tests: agent-governor via de adapter (JSON-CLI, bedienaar-principe).

De adapter voegt niets toe aan de governor — hij vertaalt alleen
JSON-in/JSON-uit. Fouten zijn nette {"ok": false, "fout": ...} antwoorden.
"""
import json
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).parent.parent
sys.path.insert(0, str(REPO))

from kern import growkit_agents as ag


def roep_governor(invoer: dict) -> tuple[int, dict, str]:
    """Simuleer een adapter-aanroep: import + main-pad met JSON in/uit."""
    import io
    from contextlib import redirect_stdout, redirect_stderr
    import adapter
    buf_out, buf_err = io.StringIO(), io.StringIO()
    code = 0
    with redirect_stdout(buf_out), redirect_stderr(buf_err):
        try:
            adapter._lees_invoer  # noqa: F841  (module-import is het punt)
            import sys as _s
            _s.stdin = io.StringIO(json.dumps(invoer))
            code = adapter.main(["governor"])
        except SystemExit as e:
            code = e.code or 0
    uit = buf_out.getvalue().strip()
    try:
        return int(code), json.loads(uit), buf_err.getvalue()
    except json.JSONDecodeError:
        return 1, {"ok": False, "fout": f"geen JSON: {uit[:200]}"}, buf_err.getvalue()


class TestGovernorStatus(unittest.TestCase):
    def test_status_toont_observer_en_limieten(self):
        code, uit, _ = roep_governor({"doel": "/tmp", "actie": "status"})
        self.assertEqual(code, 0)
        self.assertTrue(uit["ok"])
        data = uit["data"]
        self.assertEqual(data["limieten"]["taken_per_agent"], 2)
        self.assertEqual(data["limieten"]["max_agents"], 8)
        self.assertEqual(data["limieten"]["max_taken_totaal"], 16)
        self.assertIn("observer", [a["agent"] for a in data["agents"]])


class TestGovernorTaak(unittest.TestCase):
    def setUp(self):
        self.reg_pad = Path(tempfile.mkdtemp()) / "governor.json"

    def _invoer(self, **over):
        i = {"doel": "/tmp", "register_pad": str(self.reg_pad), "actie": "aanmelden",
             "agent": "kairos", "taak_id": "t1"}
        i.update(over)
        return i

    def test_aanmelden_en_status_persistent(self):
        code, uit, _ = roep_governor(self._invoer())
        self.assertEqual(uit["data"]["resultaat"]["ok"], True)
        code, uit, _ = roep_governor({"doel": "/tmp", "register_pad": str(self.reg_pad),
                                      "actie": "status"})
        namen = [a["agent"] for a in uit["data"]["agents"]]
        self.assertIn("kairos", namen)

    def test_derde_taak_weigering_als_nette_fout(self):
        roep_governor(self._invoer())
        roep_governor(self._invoer(taak_id="t2"))
        code, uit, _ = roep_governor(self._invoer(taak_id="t3"))
        self.assertEqual(code, 0)
        self.assertIn("2 taken", uit["data"]["resultaat"]["reden"])

    def test_observer_geen_taken(self):
        code, uit, _ = roep_governor(self._invoer(agent="observer"))
        self.assertFalse(uit["data"]["resultaat"]["ok"])
        self.assertIn("observer", uit["data"]["resultaat"]["reden"].lower())


class TestGovernorControle(unittest.TestCase):
    def setUp(self):
        self.reg_pad = Path(tempfile.mkdtemp()) / "governor.json"
        roep_governor({"doel": "/tmp", "register_pad": str(self.reg_pad),
                       "actie": "aanmelden", "agent": "kairos", "taak_id": "t1"})
        roep_governor({"doel": "/tmp", "register_pad": str(self.reg_pad),
                       "actie": "afronden", "agent": "kairos", "taak_id": "t1",
                       "bewijs": "tests groen"})

    def _invoer(self, **over):
        i = {"doel": "/tmp", "register_pad": str(self.reg_pad),
             "actie": "controle", "taak_id": "t1", "goed": True}
        i.update(over)
        return i

    def test_goedkeuring(self):
        code, uit, _ = roep_governor(self._invoer())
        self.assertTrue(uit["data"]["resultaat"]["ok"])
        self.assertIn("goedgekeurd", uit["data"]["resultaat"]["reden"])

    def test_afkeuring_met_reden(self):
        code, uit, _ = roep_governor(self._invoer(goed=False, reden="test faalde"))
        self.assertTrue(uit["data"]["resultaat"]["ok"])
        self.assertIn("afgekeurd", uit["data"]["resultaat"]["reden"])


class TestGovernorObserverMelding(unittest.TestCase):
    def test_melding_landt_in_register(self):
        reg_pad = Path(tempfile.mkdtemp()) / "governor.json"
        code, uit, _ = roep_governor({"doel": "/tmp", "register_pad": str(reg_pad),
                                      "actie": "melding", "tekst": "Aandachtspunt X"})
        self.assertTrue(uit["ok"])
        code, uit, _ = roep_governor({"doel": "/tmp", "register_pad": str(reg_pad),
                                      "actie": "status"})
        self.assertEqual(len(uit["data"]["observer_meldingen"]), 1)


if __name__ == "__main__":
    unittest.main()
