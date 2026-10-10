import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from kern.growkit_motor import voer_uit, voer_stap_uit
from kern.growkit_bewijs import controleer
from kern.growkit_panic import activeer_panic, is_panic_actief, lees_status
from kern.growkit_ratificatie import wacht_ratificatie_stappen

class ExecutionGuards(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.doel = Path(self.tmp.name)
        self.log = self.doel / 'logboek.json'
        self.stap = {'id': 'stap-2', 'commando': 'touch executed',
                     'bewijs': {'type': 'file_exists', 'pad': 'executed'}}

    def test_wait_blocks_next_step_and_can_be_approved(self):
        mens = {'id': 'stap-1', 'mens_nodig': {'instructie': 'Controleer'}}
        self.assertFalse(voer_uit({'stappen': [mens, self.stap]}, self.doel, self.log, None))
        self.assertFalse((self.doel / 'executed').exists())
        self.assertEqual(wacht_ratificatie_stappen(self.log), ['stap-1'])

    def test_panic_blocks_direct_and_full_execution(self):
        activeer_panic(self.doel, 'test')
        self.assertFalse(voer_stap_uit(self.stap, self.doel, None)[0])
        self.assertFalse(voer_uit({'stappen': [self.stap]}, self.doel, self.log, None))
        self.assertFalse((self.doel / 'executed').exists())

    def test_corrupt_or_invalid_panic_is_blocking(self):
        for value in ('{', '[]', '{}', '{"actief": "false"}'):
            (self.doel / 'panic_status.json').write_text(value)
            self.assertTrue(is_panic_actief(self.doel))
            self.assertTrue(lees_status(self.doel)['actief'])

    def test_nonzero_check_cannot_succeed_from_output(self):
        self.assertFalse(controleer({'type': 'shell_check', 'commando': 'echo OK; exit 1',
                                    'verwacht_substr': 'OK'}, self.doel)[0])

    def test_panic_blocks_alternative_and_proof_command(self):
        self.stap['bij_falen'] = {'alternatief_commando': 'touch alternative'}
        def execute(*args, **kwargs):
            activeer_panic(self.doel, 'during command')
            return type('Result', (), {'returncode': 1})()
        with patch('kern.growkit_motor.subprocess.run', side_effect=execute) as run:
            self.assertFalse(voer_stap_uit(self.stap, self.doel, None)[0])
            self.assertEqual(run.call_count, 1)

    def test_timeout_becomes_logged_failure(self):
        import subprocess
        with patch('kern.growkit_motor.subprocess.run', side_effect=subprocess.TimeoutExpired('test', 300)):
            self.assertFalse(voer_uit({'stappen': [self.stap]}, self.doel, self.log, None))
        self.assertEqual(json.loads(self.log.read_text())[-1]['status'], 'gefaald')
