"""Evidence-based task outcome independent of an LLM run's SUCCEEDED flag."""
from dataclasses import dataclass

@dataclass(frozen=True)
class TaskEvidence:
    intent: str
    available_tools: frozenset[str]
    called_tools: frozenset[str]
    has_verified_result: bool
    final_text: str

TOOLS = {
    'news': frozenset({'getRecentPersonalizedNews', 'searchNews'}),
    'server': frozenset({'getServerHealth'}),
    'market': frozenset({'getMarketQuote'}),
}

def evaluate(evidence: TaskEvidence) -> str:
    expected = TOOLS.get(evidence.intent)
    if expected:
        if not expected & evidence.available_tools:
            return 'blocked-missing-capability'
        if not expected & evidence.called_tools:
            return 'failed-no-tool-attempt'
        if not evidence.has_verified_result:
            return 'failed-unverified-result'
    # Narrow confirmed mixed-language signature; do not reject legitimate quoted CJK names.
    if any(fragment in evidence.final_text for fragment in ('算法设计', '버그找出')):
        return 'failed-korean-style'
    return 'fulfilled'
