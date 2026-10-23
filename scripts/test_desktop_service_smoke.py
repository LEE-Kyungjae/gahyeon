import unittest
from scripts.evaluate_desktop_service_smoke import evaluate, evaluate_runtime_health


class DesktopRuntimeLivenessTest(unittest.TestCase):
    def test_dead_tunnel_and_stalled_renderer_are_separate_failures(self):
        result = evaluate_runtime_health(False, True, [158872, 158872, 158872])
        self.assertEqual(result['core'], 'unreachable')
        self.assertEqual(result['renderer'], 'stalled')
        self.assertFalse(result['healthy'])

    def test_live_process_and_core_cannot_hide_frozen_producer(self):
        result = evaluate_runtime_health(True, True, [42, 42])
        self.assertEqual(result['renderer'], 'stalled')
        self.assertFalse(result['healthy'])
        self.assertTrue(evaluate_runtime_health(True, True, [42, 43])['healthy'])
        self.assertFalse(evaluate_runtime_health(True, True, [42])['healthy'])


class DesktopServiceSmokeTest(unittest.TestCase):
    def test_warm_success_cannot_hide_slow_inaccurate_first_request(self):
        cold = {'checks': [{'name':'tts','seconds':.406},
                           {'name':'stt-synthetic-roundtrip','seconds':20.509},
                           {'name':'conversation','seconds':26.991}],
                'transcription':{'transcript':'안녕하세요 다현이입니다'},
                'conversation':{'content':'안녕하세요! 오늞 잘 지내졂나요?'}}
        warm = {'checks':[{'name':'tts','seconds':.181},
                          {'name':'stt-synthetic-roundtrip','seconds':2.934},
                          {'name':'conversation','seconds':4.168}],
                'transcription':{'transcript':'안녕하세요. 가현입니다.'},
                'conversation':{'content':'안녕하세요! 잘 지내고 있나요?'}}
        verdict = evaluate([cold, warm])
        self.assertEqual(verdict['status'], 'failed')
        self.assertEqual({f['reason'] for f in verdict['failures']},
                         {'stt-synthetic-roundtrip-latency','conversation-latency','fixture-name-not-preserved'})
        self.assertEqual(evaluate([warm])['status'], 'synthetic-smoke-passed')
        self.assertFalse(verdict['organicTrafficValidated'])

    def test_no_traffic_is_not_validation(self):
        self.assertEqual(evaluate([])['status'], 'inconclusive-no-traffic')


if __name__ == '__main__': unittest.main()
