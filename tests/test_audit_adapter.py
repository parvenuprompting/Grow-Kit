#!/usr/bin/env python3
"""Tests: goedkeurings-audit via de adapter (scan-commando).

De adapter roept de bestaande module aan met begrensde invoer
(bron-filter, max-aantal) zodat de app-scan snel is. De parser zelf is
getest in test_goedkeuring.py; hier gaat het om het JSON-contract.
"""
import json
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).parent.parent
sys.path.insert(0, str(REPO))


class TestAdapterAudit(unittest.TestCase):
    def _roep(self, invoer):
        import io
        from contextlib import redirect_stdout
        import adapter
        buf = io.StringIO()
        code = 0
        with redirect_stdout(buf):
            import sys as s
            s.stdin = io.StringIO(json.dumps(invoer))
            code = adapter.main(["audit"]) or 0
        return int(code), json.loads(buf.getvalue().strip())

    def test_audit_geeft_samenvatting_en_kritiek(self):
        code, uit = self._roep({"doel": "/tmp", "max": 200})
        self.assertEqual(code, 0)
        self.assertTrue(uit["ok"])
        data = uit["data"]
        self.assertIn("samenvatting", data)
        self.assertIn("kritiek", data)
        self.assertIsInstance(data["kritiek"], list)
        self.assertLessEqual(len(data["kritiek"]), 200)
        # samenvatting is in simpele taal (nooit leeg)
        self.assertTrue(len(data["samenvatting"]) > 20)

    def test_audit_kritiek_item_heeft_simpele_velden(self):
        code, uit = self._roep({"doel": "/tmp", "max": 500})
        for item in uit["data"]["kritiek"]:
            self.assertIn("soort", item)
            self.assertIn("uitleg", item)
            self.assertIn("actie", item)


if __name__ == "__main__":
    unittest.main()
