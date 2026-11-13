package com.gahyeonbot.services.ai.agent;

/**
 * 스트림 관찰자와 실행 제어 양쪽의 취소 신호를 하나로 판정한다.
 */
final class AgentCancellation {
    private AgentCancellation() {
    }

    static void ensureNotCancelled(
            AgentStreamObserver observer,
            AgentExecutionControl control) {
        if (cancelled(observer, control)) throw new AgentStreamCancelledException();
    }

    static boolean cancelled(
            AgentStreamObserver observer,
            AgentExecutionControl control) {
        return control.isCancelled()
                || observer != null
                && (observer.isCancelled() || Thread.currentThread().isInterrupted());
    }
}
