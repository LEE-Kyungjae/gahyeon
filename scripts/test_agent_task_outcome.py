import unittest
from evaluate_agent_task_outcome import TaskEvidence, evaluate

class AgentTaskOutcomeTest(unittest.TestCase):
    def test_news_refusal_without_existing_tool_attempt_is_failure(self):
        e=TaskEvidence('news',frozenset({'getRecentPersonalizedNews'}),frozenset(),False,'오늘 기사를 확인할 도구가 없어요.')
        self.assertEqual('failed-no-tool-attempt',evaluate(e))
        self.assertEqual('failed-unverified-result',evaluate(TaskEvidence('news',e.available_tools,e.available_tools,False,'찾았어요.')))
        self.assertEqual('fulfilled',evaluate(TaskEvidence('news',e.available_tools,e.available_tools,True,'검증한 기사와 출처입니다.')))
    def test_server_and_market_missing_authority_are_not_success(self):
        for intent in ('server','market'):
            self.assertEqual('blocked-missing-capability',evaluate(TaskEvidence(intent,frozenset(),frozenset(),False,'직접 찾아보세요.')))
    def test_confirmed_mixed_korean_answer_is_rejected(self):
        self.assertEqual('failed-korean-style',evaluate(TaskEvidence('coding',frozenset(),frozenset(),False,'算法设计, 버그找出도 할 수 있어.')))
        self.assertEqual('fulfilled',evaluate(TaskEvidence('coding',frozenset(),frozenset(),False,'응, 코드 작성과 오류 분석을 도울 수 있어.')))

if __name__=='__main__': unittest.main()
