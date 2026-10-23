package com.gahyeonbot.application.speech;

import com.gahyeonbot.adapters.discord.voice.VoiceAssistantService;
import com.gahyeonbot.services.assistant.AssistantProperties;
import org.junit.jupiter.api.Test;
import org.springframework.test.util.ReflectionTestUtils;
import java.util.Arrays;
import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.Mockito.mock;

class VoiceUnderstandingRegressionTest {
    @Test void completeShortAnswersAreDeliveredWithoutContaminatingNextRequest() throws Exception {
        for (String reply : new String[]{"네.", "예!", "응", " 네? "}) {
            Object guard = guard();
            assertThat(merge(guard, reply, 1000)).isEqualTo(reply.trim());
            assertThat(merge(guard, "서울 날씨 알려 줘", 2000)).isEqualTo("서울 날씨 알려 줘");
        }
    }
    @Test void acknowledgmentDiscardsPendingIncompleteFragment() throws Exception {
        Object guard = guard();
        assertThat(merge(guard, "가", 1000)).isNull();
        assertThat(merge(guard, "네.", 2000)).isEqualTo("네.");
        assertThat(merge(guard, "일정 확인해 줘", 2500)).isEqualTo("일정 확인해 줘");
    }
    @Test void otherFragmentsStillMergeAndAffirmativeSubstringsAreNotSpecialCased() throws Exception {
        Object guard = guard();
        assertThat(merge(guard, "가", 1000)).isNull();
        assertThat(merge(guard, "현아", 2000)).isEqualTo("가 현아");
        assertThat(merge(guard, "네가 알려 줘", 3000)).isEqualTo("네가 알려 줘");
    }
    @Test void shortAnswerStillPassesThroughDuplicateAndRateLimits() throws Exception {
        Object guard = guard();
        String text = merge(guard, "네", 1000);
        assertThat((Boolean) ReflectionTestUtils.invokeMethod(guard, "allow", text, 1000L)).isTrue();
        assertThat((Boolean) ReflectionTestUtils.invokeMethod(guard, "allow", text, 1500L)).isFalse();
    }
    @Test void expiredShortBurstCannotContaminateFollowingUtterance() {
        var policy = new UtteranceSegmentationPolicy(1000, 20, 100, 1200, 300, 1000, 2000, 0, 1000);
        VoiceActivityDetector detector = pcm -> new VoiceActivityDetector.Detection(true, pcm.length);
        var accumulator = new StreamingUtteranceAccumulator(policy, detector, 0);
        byte[] oldBurst = filled(200, 1);
        accumulator.accept(oldBurst, 0);
        assertThat(accumulator.poll(3000)).isEmpty();
        byte[] actual = filled(600, 2);
        accumulator.accept(actual, 4000);
        var result = accumulator.poll(6500).orElseThrow();
        assertThat(result.pcm()).containsExactly(actual);
        assertThat(result.detectedSpeechMillis()).isEqualTo(600);
    }
    @Test void fullInvalidBufferReleasesCapacityForNextSpokenAudio() {
        var policy = new UtteranceSegmentationPolicy(1000, 2, 100, 1200, 300, 1000, 2000, 0, 1000);
        int[] calls = {0};
        VoiceActivityDetector detector = pcm -> new VoiceActivityDetector.Detection(true, calls[0]++ == 0 ? 100 : 400);
        var accumulator = new StreamingUtteranceAccumulator(policy, detector, 0);
        accumulator.accept(new byte[2000], 0);
        assertThat(accumulator.poll(1)).isEmpty();
        byte[] actual = filled(600, 7);
        accumulator.accept(actual, 4000);
        var result = accumulator.poll(6500).orElseThrow();
        assertThat(result.pcm()).containsExactly(actual);
        assertThat(result.detectedSpeechMillis()).isEqualTo(400);
    }
    @Test void briefPauseInsideAnIncompleteUtteranceRetainsAudio() {
        var policy = new UtteranceSegmentationPolicy(1000, 20, 100, 1200, 300, 1000, 2000, 0, 1000);
        VoiceActivityDetector detector = pcm -> new VoiceActivityDetector.Detection(true, pcm.length);
        var accumulator = new StreamingUtteranceAccumulator(policy, detector, 0);
        accumulator.accept(filled(200, 1), 0);
        assertThat(accumulator.poll(1000)).isEmpty();
        accumulator.accept(filled(400, 2), 1100);
        var result = accumulator.poll(3200).orElseThrow();
        assertThat(result.pcm()).hasSize(600).startsWith((byte) 1).endsWith((byte) 2);
    }
    private static byte[] filled(int size, int value) {
        byte[] bytes = new byte[size]; Arrays.fill(bytes, (byte) value); return bytes;
    }
    private static String merge(Object guard, String text, long now) {
        return ReflectionTestUtils.invokeMethod(guard, "mergeOrHold", text, now);
    }
    private static Object guard() throws Exception {
        var service = mock(VoiceAssistantService.class);
        ReflectionTestUtils.setField(service, "properties", new AssistantProperties());
        Class<?> type = Arrays.stream(VoiceAssistantService.class.getDeclaredClasses())
                .filter(c -> c.getSimpleName().equals("RequestGuard")).findFirst().orElseThrow();
        var constructor = type.getDeclaredConstructor(VoiceAssistantService.class);
        constructor.setAccessible(true);
        return constructor.newInstance(service);
    }
}
