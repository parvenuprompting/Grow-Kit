import json
import tempfile
import unittest
from pathlib import Path
from kern.growkit_resultaat import bewijsrapport
from kern.growkit_bewijs import controleer

class ResultaatTests(unittest.TestCase):
    def test_machine_success_is_not_human_or_content_approval(self):
        profile = {'acceptatiecriteria': ['Rapport klopt'], 'stappen': [{'id': 'a', 'verwacht': 'Bestand bestaat', 'bewijs': {'type': 'file_exists'}}]}
        result = bewijsrapport(profile, [{'stap': 'a', 'status': 'geslaagd', 'bewijs': 'bestand bestaat'}])
        self.assertTrue(result['technisch_gecontroleerd'])
        self.assertFalse(result['inhoudelijk_beoordeeld'])
        self.assertFalse(result['mens_goedgekeurd'])
        self.assertEqual(result['criteria'], ['Rapport klopt'])

    def test_later_failure_overrides_old_success(self):
        r = bewijsrapport({'stappen': [{'id': 'a'}]}, [{'stap': 'a', 'status': 'geslaagd'}, {'stap': 'a', 'status': 'gefaald'}])
        self.assertFalse(r['technisch_gecontroleerd'])

    def test_structured_values_reject_wrong_value_and_type(self):
        with tempfile.TemporaryDirectory() as tmp:
            pad = Path(tmp)
            check = {'type': 'json_valid', 'pad': 'report.json', 'verwacht_waarden': {'aantal': 1}}
            for value, expected in [(1, True), (2, False), (True, False)]:
                (pad / 'report.json').write_text(json.dumps({'aantal': value}))
                self.assertEqual(controleer(check, pad)[0], expected)
