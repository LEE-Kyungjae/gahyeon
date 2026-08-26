package com.gahyeonbot.application.speech;

import org.junit.jupiter.api.Test;

import static org.assertj.core.api.Assertions.assertThat;

class TranscriptHallucinationPolicyTest {
    @Test
    void rejectsShortKnownHallucinationsAndDominantRepetition() {
        assertThat(TranscriptHallucinationPolicy.rejects("감사합니다.", 1_340, 1_340)).isTrue();
        assertThat(TranscriptHallucinationPolicy.rejects(
                "에이전트, 에이전트, 에이전트, 에이전트, 에이전트", 8_000, 8_000)).isTrue();
    }

    @Test
    void preservesShortRealSpeechAndNaturalRepetition() {
        assertThat(TranscriptHallucinationPolicy.rejects("안녕", 920, 920)).isFalse();
        assertThat(TranscriptHallucinationPolicy.rejects(
                "아니 아니, 그게 아니라 다른 레포를 찾아줘", 3_200, 3_200)).isFalse();
    }
}
