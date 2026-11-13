package com.gahyeonbot.services.ai.agent;

import java.util.List;
import java.util.Locale;

/**
 * 모델 최종 응답에서 추론 태그와 내부 마커를 걷어내고 사용자에게 보일 답변만 남긴다.
 */
final class AgentFinalResponseSanitizer {
    private AgentFinalResponseSanitizer() {
    }

    static String sanitize(String value) {
        if (value == null || value.isBlank()) return "";
        String content = value.trim();
        String lowerContent = content.toLowerCase(Locale.ROOT);
        int responseStart = lowerContent.lastIndexOf("<response>");
        if (responseStart >= 0) {
            String explicitResponse = content.substring(responseStart + "<response>".length())
                    .replaceFirst("(?is)\\s*(?:</response>|response>)\\s*$", "")
                    .trim();
            if (!explicitResponse.isBlank()) content = explicitResponse;
        }
        int thinkingEnd = content.toLowerCase(Locale.ROOT).lastIndexOf("</think>");
        if (thinkingEnd >= 0) {
            String finalAnswer = content.substring(thinkingEnd + "</think>".length()).trim();
            if (!finalAnswer.isBlank()) content = finalAnswer;
        }
        content = content
                .replaceAll("(?is)<think>.*?</think>", "")
                .replaceAll("(?is)</?think>", "")
                .replaceAll("(?is)<thought>.*?(?:</thought>|thought>)", "")
                .replaceAll("(?is)</?thought>", "")
                .replaceAll("(?is)</?response>", "")
                .replaceAll("(?i)(?:<pad>|<unk>|<s>|</s>)+", "")
                .trim();
        String lower = content.toLowerCase(Locale.ROOT);
        for (String marker : List.of(
                "\nfinal answer:", "\nfinal response:",
                "\n최종 답변:", "\n최종 응답:")) {
            int markerIndex = lower.lastIndexOf(marker);
            if (markerIndex >= 0) {
                String finalAnswer = content.substring(markerIndex + marker.length()).trim();
                if (!finalAnswer.isBlank()) return finalAnswer;
            }
        }
        if (lower.startsWith("here's a thinking process:")
                || lower.startsWith("here is a thinking process:")
                || lower.startsWith("thinking process:")
                || lower.startsWith("analysis:")
                || lower.startsWith("<thought>")) {
            return "";
        }
        return content;
    }
}
