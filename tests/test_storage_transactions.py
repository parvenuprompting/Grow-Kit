import json
import multiprocessing
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from kern.growkit_opslag import transactie, voeg_gebeurtenissen_toe
from kern import growkit_automatiek as am


def schrijf(pad, n):
    for i in range(15):
        voeg_gebeurtenissen_toe(Path(pad), [{'worker': n, 'i': i}])

class StorageTransactions(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.pad = Path(self.tmp.name) / 'log.json'

    def test_concurrent_processes_keep_every_event(self):
        ctx = multiprocessing.get_context('spawn')
        workers = [ctx.Process(target=schrijf, args=(str(self.pad), n)) for n in range(4)]
        for p in workers: p.start()
        for p in workers:
            p.join(20)
            self.assertEqual(p.exitcode, 0)
        data = json.loads(self.pad.read_text())
        self.assertEqual(len({(x['worker'], x['i']) for x in data}), 60)

    def test_failed_commit_keeps_previous_snapshot(self):
        voeg_gebeurtenissen_toe(self.pad, [{'old': True}])
        original = self.pad.read_bytes()
        with patch('kern.growkit_opslag.os.replace', side_effect=OSError('disk failure')):
            with self.assertRaises(OSError):
                voeg_gebeurtenissen_toe(self.pad, [{'new': True}])
        self.assertEqual(self.pad.read_bytes(), original)

    def test_corruption_is_preserved_and_blocks_write(self):
        self.pad.write_text('{broken')
        with self.assertRaises(ValueError):
            voeg_gebeurtenissen_toe(self.pad, [{'new': True}])
        self.assertEqual(self.pad.read_text(), '{broken')

    def test_history_cannot_be_edited(self):
        voeg_gebeurtenissen_toe(self.pad, [{'old': True}])
        with self.assertRaises(ValueError):
            with transactie(self.pad, append_only=True) as data:
                data[0]['old'] = False
        self.assertTrue(json.loads(self.pad.read_text())[0]['old'])

    def test_plan_and_history_committed_together_and_stale_edits_rejected(self):
        with patch.object(am, '_opslag_pad', return_value=self.pad), patch.object(am, '_log_pad', return_value=self.pad.with_name('events.json')):
            plan = am.voeg_toe('Test', am.nieuw_plan('Test')['blokken'])
            stale = am.lees(plan['id'])
            plan['titel'] = 'Changed'
            am.bewaar(plan)
            with self.assertRaises(ValueError): am.bewaar(stale)
            state = json.loads(am._staat_pad().read_text())
            self.assertEqual(state['plannen'][0]['titel'], 'Changed')
            self.assertEqual(len(state['gebeurtenissen']), 2)
