package com.gahyeonbot.services.assistant;

final class TtsSpeechText {
    private TtsSpeechText() {}

    static String sanitize(String value) {
        if (value == null || value.isBlank()) return "";
        return value
                .replaceAll("(?s)```(?:[a-zA-Z0-9_+-]+)?\\s*(.*?)```", "$1")
                .replaceAll("\\[([^]]+)]\\(https?://[^)]+\\)", "$1")
                .replaceAll("https?://\\S+", "")
                .replaceAll("<a?:[a-zA-Z0-9_]+:\\d+>", "")
                .replaceAll("<[@#&]!?(?:\\d+)>", "")
                .replaceAll("[`*_~>#|]", " ")
                .replaceAll("[\\p{So}\\p{Sk}]", " ")
                .replaceAll("[^\\p{L}\\p{N}\\s.,?!%+\\-:/]", " ")
                .replaceAll("\\s+", " ")
                .trim();
    }
}
