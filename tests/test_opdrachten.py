import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from kern import growkit_opdrachten as op

class OpdrachtenTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        p = patch.object(op, '_root', return_value=Path(tmp.name))
        p.start(); self.addCleanup(p.stop)
        self.profile = {'stappen': [{'id': 'a', 'commando': 'echo hi > result.txt',
                        'verwacht': 'Resultaat bestaat', 'bewijs': {'type': 'file_exists', 'pad': 'result.txt'}}]}

    def test_full_lifecycle_and_no_accidental_rerun(self):
        d = op.nieuw('Test', ['Resultaat klopt'], self.profile)
        with self.assertRaises(ValueError): op.uitvoeren(d['id'], d['plan_hash'])
        with self.assertRaises(ValueError): op.uitvoeren(d['id'], 'old', True)
        d = op.uitvoeren(d['id'], d['plan_hash'], True)
        self.assertEqual(d['status'], 'resultaat')
        self.assertTrue(d['rapport']['technisch_gecontroleerd'])
        self.assertFalse(d['rapport']['mens_goedgekeurd'])
        with self.assertRaises(ValueError): op.uitvoeren(d['id'], d['plan_hash'], True)
        d = op.beoordeel(d['id'], True, 'Bestand geopend en inhoud gecontroleerd')
        self.assertEqual(d['status'], 'goedgekeurd')
        self.assertEqual(op.lijst()['opdrachten'][0]['status'], 'goedgekeurd')

    def test_wait_approval_and_resume(self):
        self.profile['stappen'].insert(0, {'id': 'mens', 'mens_nodig': {'instructie': 'Bevestig'}})
        d = op.nieuw('Test', ['Resultaat klopt'], self.profile)
        d = op.uitvoeren(d['id'], d['plan_hash'], True)
        self.assertEqual(d['status'], 'wacht_op_mens')
        self.assertFalse((Path(d['doel']) / 'result.txt').exists())
        op.beoordeel(d['id'], True, 'Gecontroleerd')
        d = op.uitvoeren(d['id'], d['plan_hash'], True)
        self.assertEqual(d['status'], 'resultaat')

    def test_concurrent_execution_is_rejected(self):
        d = op.nieuw('Test', ['ok'], self.profile)
        with op._uitvoerslot(d['id']):
            with self.assertRaises(ValueError): op.uitvoeren(d['id'], d['plan_hash'], True)

    def test_bad_id_cannot_escape_storage(self):
        with self.assertRaises(ValueError): op.lees('../outside')
