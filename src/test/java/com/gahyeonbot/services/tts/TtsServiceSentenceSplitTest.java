package com.gahyeonbot.services.tts;

import org.junit.jupiter.api.Test;

import java.util.List;

import static org.junit.jupiter.api.Assertions.assertEquals;

class TtsServiceSentenceSplitTest {
    @Test
    void splitsKoreanSentencesWithoutPython() {
        assertEquals(
                List.of("첫 번째 문장입니다.", "두 번째 문장인가요?", "네, 맞습니다!"),
                TtsService.splitSentencesLocally(
                        "첫 번째 문장입니다. 두 번째 문장인가요? 네, 맞습니다!"));
    }

    @Test
    void splitsLinesAndIgnoresBlankInput() {
        assertEquals(List.of("첫째", "둘째"),
                TtsService.splitSentencesLocally("첫째\n둘째"));
        assertEquals(List.of(), TtsService.splitSentencesLocally("  "));
    }
}
