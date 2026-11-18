package com.gahyeonbot.services.ai.agent;

/**
 * 실행 원장 이벤트에 저장할 문자열 크기를 제한한다.
 */
final class AgentEventPayloads {
    static final int MAX_EVENT_PAYLOAD = 4_000;

    private AgentEventPayloads() {
    }

    static String limited(String value) {
        if (value == null) return null;
        return value.length() <= MAX_EVENT_PAYLOAD
                ? value
                : value.substring(0, MAX_EVENT_PAYLOAD) + "...[truncated]";
    }
}
