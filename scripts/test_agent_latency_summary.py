import unittest
from scripts.summarize_agent_latency import summarize

class LatencySummaryTest(unittest.TestCase):
    def test_pairs_steps_and_does_not_mark_incomplete_runs_complete(self):
        def e(event,stamp):return f'LATENCY_EVENT run=test event={event} step=1 tool=null at=2026-10-18 00:00:{stamp}\n'
        text=e('RUN_CREATED','00.000')+e('MODEL_CALL_STARTED','00.100')+e('MODEL_CALL_COMPLETED','01.100')
        incomplete=summarize(text)['test']
        self.assertFalse(incomplete['complete']);self.assertEqual(1000,incomplete['modelMs'])
        complete=summarize(text+e('RUN_SUCCEEDED','01.200'))['test']
        self.assertTrue(complete['complete']);self.assertEqual(200,complete['otherMs'])
        self.assertEqual('RUN_FAILED',summarize(text+e('RUN_FAILED','01.200'))['test']['outcome'])

if __name__=='__main__':unittest.main()
