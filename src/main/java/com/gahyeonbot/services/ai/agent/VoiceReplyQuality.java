package com.gahyeonbot.services.ai.agent;

import java.util.*;
import java.util.regex.Pattern;

/** Narrow checks for observed voice failures; never rewrites the user's transcript. */
final class VoiceReplyQuality {
    static final String GUIDANCE = """
            [실제 음성 대화]
            사용자의 말은 STT로 전사되었고 답변은 TTS로 재생된다. 음성 대화가 불가능하다고 말하지 않는다.
            사용자가 발음이나 끊김을 지적하면 이 서비스에 대한 피드백으로 이해한다.
            사용자의 발음 연습이나 빨리/짧게 말하기를 해결책으로 떠넘기지 않는다.
            로그나 진단 근거 없이 STT/TTS 중 어느 쪽의 원인인지 단정하지 않는다.
            '음성으로 설명드릴게요', '잠시만요', '정리해서 답할게요' 같은 진행 안내 없이 본론부터 답한다.
            용어가 등장했다는 이유만으로 정의를 설명하지 않는다. 제안·피드백·정정과 설명 요청을 구분한다.
            'A가 아니라 B'라는 정정은 B로 이해하고, A에 대한 설명을 반복하지 않는다.
            특히 디스코드에서 임베드는 메시지 카드 맥락일 수 있으며 벡터 임베딩으로 자동 해석하지 않는다.
            직전 맥락에 있는 '이것도'를 다시 처음부터 설명해 달라고 요구하지 않는다.
            아직 실행하지 않은 설정 변경이나 개선을 이미 적용했다고 약속하지 않는다.
            문장을 끝까지 완성하고, 한국어 문장에 무의미한 영문·중국어를 섞지 않는다.
            """;
    private static final Pattern PREAMBLE = Pattern.compile(
            "^(?:(?:음성으로 설명드릴게요|음성으로 설명할게요|잠시만요|정리해서 답할게요)[.!。]?\\s*)+");
    static String clean(String text) {
        return PREAMBLE.matcher(text == null ? "" : text.strip()).replaceFirst("").strip();
    }
    static String failure(String text, String finishReason) {
        if ("length".equalsIgnoreCase(finishReason) || "max_tokens".equalsIgnoreCase(finishReason)) return "truncated";
        if (text.isBlank()) return "empty";
        if (text.matches("(?is)^\\s*User Safety:.*Response Safety:.*")) return "classifier_output";
        if (text.contains("음성으로는 답변하지") || text.contains("음성으로 답변하지 않")) return "modality_denial";
        // Repeated long Latin gibberish observed in the October 16 voice feedback.
        long latinWords = Pattern.compile("[a-zA-Z]{2,}").matcher(text).results().count();
        long latinCharacters = text.codePoints().filter(c -> c >= 'a' && c <= 'z' || c >= 'A' && c <= 'Z').count();
        if (latinWords < 12 || latinCharacters < text.length() * 0.55) return "";
        Map<String, Integer> counts = new HashMap<>();
        var words = Pattern.compile("[a-zA-Z]{8,}").matcher(text);
        while (words.find()) {
            if (counts.merge(words.group().toLowerCase(Locale.ROOT), 1, Integer::sum) >= 4) return "repetition";
        }
        return "";
    }
}
