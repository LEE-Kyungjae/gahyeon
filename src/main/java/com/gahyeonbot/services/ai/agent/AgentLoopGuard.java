package com.gahyeonbot.services.ai.agent;

import java.util.HashMap;
import java.util.Map;

public class AgentLoopGuard {
    private final int repeatedCallLimit;
    private final Map<String, Integer> repeatedCalls = new HashMap<>();

    public AgentLoopGuard(int repeatedCallLimit) {
        if (repeatedCallLimit < 2) {
            throw new IllegalArgumentException("반복 호출 제한은 2 이상이어야 합니다.");
        }
        this.repeatedCallLimit = repeatedCallLimit;
    }

    public void recordToolCall(String toolName, String arguments) {
        String signature = toolName + ":" + arguments;
        int repeats = repeatedCalls.merge(signature, 1, Integer::sum);
        if (repeats >= repeatedCallLimit) {
            throw new AgentLoopDetectedException(toolName, repeats);
        }
    }

    public static class AgentLoopDetectedException extends RuntimeException {
        public AgentLoopDetectedException(String toolName, int repeats) {
            super("동일한 도구 호출이 " + repeats + "회 반복되었습니다: " + toolName);
        }
    }
}
