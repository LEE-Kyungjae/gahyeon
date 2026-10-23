package com.gahyeonbot.adapters.discord.voice;

import com.gahyeonbot.services.assistant.AssistantProperties;
import org.junit.jupiter.api.Test;
import org.springframework.test.util.ReflectionTestUtils;
import java.lang.reflect.*;
import static org.assertj.core.api.Assertions.*;
import static org.mockito.Mockito.*;

class VoiceFeedbackRegressionTest {
    private Object guard() throws Exception {
        var service = mock(VoiceAssistantService.class, CALLS_REAL_METHODS);
        ReflectionTestUtils.setField(service, "properties", new AssistantProperties());
        var type = Class.forName(VoiceAssistantService.class.getName() + "$RequestGuard");
        var constructor = type.getDeclaredConstructor(VoiceAssistantService.class);
        constructor.setAccessible(true);
        return constructor.newInstance(service);
    }
    private String offer(Object guard, String text, long time) {
        return ReflectionTestUtils.invokeMethod(guard, "mergeOrHold", text, time);
    }
    @Test void unfinishedFeedbackWaitsAndSurvivesTranscriptionLatency() throws Exception {
        var guard = guard();
        assertThat(offer(guard, "내가 말하는 동안에는 어떻게 해야 되냐면", 1000)).isNull();
        assertThat(offer(guard, "말이 끝날 때까지 기다려 줘", 9000))
                .isEqualTo("내가 말하는 동안에는 어떻게 해야 되냐면 말이 끝날 때까지 기다려 줘");
    }
    @Test void completeCorrectionAndAcknowledgementRemainImmediate() throws Exception {
        var guard = guard();
        assertThat(offer(guard, "임베딩이 아니라 임베드다", 1000)).isEqualTo("임베딩이 아니라 임베드다");
        assertThat(offer(guard, "응", 2000)).isEqualTo("응");
        assertThat(offer(guard, "어떻게 하면 돼?", 3000)).isEqualTo("어떻게 하면 돼?");
    }
    @Test void staleContinuationDoesNotAttachToUnrelatedLaterConversation() throws Exception {
        var guard = guard();
        assertThat(offer(guard, "예를 들면", 1000)).isNull();
        assertThat(offer(guard, "오늘 일정 알려줘", 40000)).isEqualTo("오늘 일정 알려줘");
    }
    @Test void koreanPronunciationFeedbackDoesNotRequestEnglishDelivery() {
        assertThat(new VoiceAssistantExpressionPolicy().plan("드릴게요의 한국어 발음이 잘못됐어").communicativeIntent())
                .isNotEqualTo("speak_with_clear_english_pronunciation");
        assertThat(new VoiceAssistantExpressionPolicy().plan("영어 발음으로 읽어줘").communicativeIntent())
                .isEqualTo("speak_with_clear_english_pronunciation");
    }
    @Test void progressSpeechIsDisabledByDefault() {
        assertThat(new AssistantProperties().getResponseAcknowledgementMillis()).isNegative();
    }

    @Test void twentySecondsOfContinuousSpeechIsNotSubmittedMidSentence() {
        var config = new AssistantProperties();
        var segmentation = new com.gahyeonbot.application.speech.UtteranceSegmentationPolicy(
                32000, config.getMaxUtteranceSeconds(), 320, 1500, 0, 0, 1500, 0, 16000);
        try (var accumulator = new com.gahyeonbot.application.speech.StreamingUtteranceAccumulator(segmentation, null, 0)) {
            accumulator.accept(new byte[20 * 32000], 20000);
            assertThat(accumulator.poll(20000)).isEmpty();
            accumulator.accept(new byte[4 * 32000], 24000);
            assertThat(accumulator.poll(24000)).isEmpty();
            assertThat(accumulator.poll(25500).orElseThrow().capturedAudioMillis()).isEqualTo(24000);
        }
    }
    @Test void legacyAcknowledgementDelayDoesNotReenableUnwantedSpeech() {
        var config = new AssistantProperties();
        config.setResponseAcknowledgementMillis(1500);
        assertThat(config.isResponseAcknowledgementsEnabled()).isFalse();
    }
}
