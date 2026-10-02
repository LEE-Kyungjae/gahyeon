package com.gahyeonbot.adapters.unreal;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.gahyeonbot.adapters.unreal.protocol.UnrealEnvelope;
import com.gahyeonbot.core.speech.AudioOutput;
import com.gahyeonbot.core.speech.ExpressiveSpeechRequest;
import com.gahyeonbot.core.speech.ExpressiveSpeechSynthesisUseCase;
import com.gahyeonbot.core.speech.SpeechSegment;
import com.gahyeonbot.core.speech.SpeechSynthesisUseCase;
import com.gahyeonbot.core.speech.VoiceExpression;
import com.gahyeonbot.core.speech.VoiceProfileId;
import io.micrometer.core.instrument.simple.SimpleMeterRegistry;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.condition.EnabledIfEnvironmentVariable;

import java.nio.file.Files;
import java.nio.file.Path;
import java.security.MessageDigest;
import java.time.Clock;
import java.time.Duration;
import java.util.ArrayDeque;
import java.util.ArrayList;
import java.util.HexFormat;
import java.util.List;
import java.util.Map;

import static org.assertj.core.api.Assertions.assertThat;

class UnrealSpeechPreparedLiveIntegrationTest {
    @Test
    @EnabledIfEnvironmentVariable(named = "GAHYEON_VISEME_LIVE_WAV", matches = ".+")
    void publishesRealGeneratedAudioExpressionAndWaveformTimelineTogether() throws Exception {
        Path path = Path.of(System.getenv("GAHYEON_VISEME_LIVE_WAV")).toAbsolutePath().normalize();
        String text = System.getenv().getOrDefault(
                "GAHYEON_VISEME_LIVE_TEXT", "잠깐만, 지금 확인해 볼게.");
        byte[] bytes = Files.readAllBytes(path);
        var audio = new AudioOutput(bytes, "audio/wav", "wav");
        var segment = new SpeechSegment(0, text);
        var expression = new VoiceExpression("bright", 0.58, "share_positive_affect");
        SpeechSynthesisUseCase segmentation = new SpeechSynthesisUseCase() {
            @Override public boolean isReady(VoiceProfileId voiceProfile) { return false; }
            @Override public List<SpeechSegment> prepare(String ignored) { return List.of(segment); }
            @Override public AudioOutput synthesize(SpeechSegment ignored, VoiceProfileId voiceProfile) {
                throw new AssertionError("natural synthesis must not be selected");
            }
        };
        ExpressiveSpeechSynthesisUseCase expressive = new ExpressiveSpeechSynthesisUseCase() {
            @Override public boolean isExpressiveReady(VoiceProfileId voiceProfile) {
                return VoiceProfileId.ASSISTANT.equals(voiceProfile);
            }
            @Override public AudioOutput synthesizeExpressive(ExpressiveSpeechRequest request) {
                assertThat(request).isEqualTo(new ExpressiveSpeechRequest(
                        segment, VoiceProfileId.ASSISTANT, expression));
                return audio;
            }
        };
        var tasks = new ArrayDeque<Runnable>();
        var messages = new ArrayList<UnrealEnvelope>();
        var broker = new UnrealEphemeralBroker(Clock.systemUTC());
        broker.subscribe("live-renderer", "live-session", messages::add);
        var cache = new UnrealAudioCache(Clock.systemUTC(), Duration.ofMinutes(5));
        var registry = new SimpleMeterRegistry();
        var service = new DefaultUnrealSpeechPreparationService(
                segmentation, expressive, cache, broker, tasks::add,
                new UnrealRuntimeMetrics(registry), new PcmWavKoreanVisemeTimeline());

        service.prepare(new UnrealSpeechPreparationRequest(
                "live-session", "live:g1:utterance:0", 1, 0, text,
                VoiceProfileId.ASSISTANT, expression), () -> true);
        tasks.remove().run();

        assertThat(messages).hasSize(1);
        UnrealEnvelope prepared = messages.getFirst();
        assertThat(prepared.type()).isEqualTo("speech.prepared");
        assertThat(prepared.payload()).containsEntry("voiceProfile", "gahyeon.assistant");
        assertThat(prepared.payload().get("voiceExpression")).isEqualTo(Map.of(
                "style", "bright", "intensity", 0.58,
                "communicativeIntent", "share_positive_affect"));
        List<?> visemes = (List<?>) prepared.payload().get("visemes");
        assertThat(visemes).isNotEmpty();
        String audioId = (String) prepared.payload().get("utteranceId");
        AudioOutput cached = cache.get(audioId).orElseThrow();
        assertThat(cached.data()).isEqualTo(bytes);
        assertThat(prepared.payload().get("audio")).isEqualTo(Map.of(
                "url", "/api/gahyeon/unreal/speech/audio/" + audioId,
                "mimeType", "audio/wav"));
        assertThat(registry.get("gahyeon.unreal.viseme.timeline")
                .tag("source", "waveform-guided").counter().count()).isEqualTo(1);

        System.out.println(new ObjectMapper().writeValueAsString(Map.of(
                "eventType", prepared.type(),
                "voiceProfile", prepared.payload().get("voiceProfile"),
                "expression", prepared.payload().get("voiceExpression"),
                "visemeSource", "waveform-guided",
                "visemeCount", visemes.size(),
                "cachedAudioBytes", cached.data().length,
                "wavSha256", HexFormat.of().formatHex(
                        MessageDigest.getInstance("SHA-256").digest(cached.data())))));
    }
}
