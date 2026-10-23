import unittest
from scripts.verify_lme_chat_answer import validate_answer

EXPECTED = dict(date='2026-10-16', source='https://example.test/copper', cash=14595.0,
                threeMonth=14485.0, cashDelta=56.0, threeMonthDelta=123.0)


class LmeChatAnswerTest(unittest.TestCase):
    def test_truncated_price_answer_is_not_success(self):
        truncated = '2026‑10‑16 USD/톤 현금 Cash 14,595.00 +56.00 | 3개월물 (3'
        self.assertTrue(validate_answer(truncated, EXPECTED))
        complete = truncated + '\n3개월물 14,485.00 +123.00 https://example.test/copper'
        self.assertEqual([], validate_answer(complete, EXPECTED))
        self.assertTrue(validate_answer(complete.replace('2026‑10‑16', '2026-10-15'), EXPECTED))
        self.assertTrue(validate_answer(complete.replace('14,485.00', '14,585.00'), EXPECTED))


if __name__ == '__main__':
    unittest.main()
