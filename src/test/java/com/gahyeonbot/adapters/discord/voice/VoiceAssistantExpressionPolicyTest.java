package com.gahyeonbot.adapters.discord.voice;

import org.junit.jupiter.api.Test;

import static org.assertj.core.api.Assertions.assertThat;

class VoiceAssistantExpressionPolicyTest {
    private final VoiceAssistantExpressionPolicy policy = new VoiceAssistantExpressionPolicy();

    @Test
    void mapsDirectLaughterRequestsToAudibleSuppressedLaughter() {
        var expression = policy.plan("아니, 그냥 웃어봐");

        assertThat(expression.style()).isEqualTo("suppressed_laugh");
        assertThat(expression.communicativeIntent()).isEqualTo("respond_with_audible_laughter");
        assertThat(expression.intensity()).isGreaterThanOrEqualTo(0.7);
    }

    @Test
    void keepsOrdinarySpeechNatural() {
        assertThat(policy.plan("오늘 일정 알려줘"))
                .isEqualTo(com.gahyeonbot.core.speech.VoiceExpression.NATURAL);
    }

    @Test
    void mapsConcernAndEnglishPronunciationRequestsWithoutFlatteningThem() {
        assertThat(policy.plan("내가 좀 걱정되는데 괜찮아?").style()).isEqualTo("concerned");
        assertThat(policy.plan("이 문장은 영어 발음으로 읽어줘").communicativeIntent())
                .isEqualTo("speak_with_clear_english_pronunciation");
    }
}
