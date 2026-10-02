package com.gahyeonbot.adapters.unreal;

import com.gahyeonbot.application.speech.StreamingExpressiveSpeechSynthesisPort;
import com.gahyeonbot.core.speech.AudioOutput;
import com.gahyeonbot.core.speech.ExpressiveSpeechRequest;
import com.gahyeonbot.core.speech.PcmAudioFormat;
import com.gahyeonbot.core.speech.SpeechSegment;
import com.gahyeonbot.core.speech.SpeechSynthesisUseCase;
import com.gahyeonbot.core.speech.VoiceExpression;
import com.gahyeonbot.core.speech.VoiceProfileId;
import io.micrometer.core.instrument.simple.SimpleMeterRegistry;
import org.junit.jupiter.api.Test;

import java.io.ByteArrayOutputStream;
import java.time.Clock;
import java.time.Duration;
import java.util.ArrayDeque;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;

import static org.assertj.core.api.Assertions.assertThat;

class DefaultUnrealStreamingSpeechPreparationServiceTest {
    @Test
    void publishesReplayablePcmStreamBeforeSynthesisCompletes() throws Exception {
        var tasks = new ArrayDeque<Runnable>();
        var provider = new StreamingProvider();
        var streams = new UnrealPcmStreamCache(provider, tasks::add, Clock.systemUTC(),
                Duration.ofMinutes(1));
        var outbound = new UnrealEphemeralBroker(Clock.systemUTC());
        var messages = new ArrayList<com.gahyeonbot.adapters.unreal.protocol.UnrealEnvelope>();
        outbound.subscribe("renderer", "session", messages::add);
        var service = service(tasks, streams, outbound);
        var expression = new VoiceExpression("fake_cute", 0.72, "playful_tease");

        service.prepare(new UnrealSpeechPreparationRequest(
                "session", "correlation", 3, 0, "싫어어~",
                VoiceProfileId.ASSISTANT, expression), () -> true);
        tasks.remove().run();

        assertThat(messages).hasSize(1);
        var prepared = messages.getFirst();
        assertThat(prepared.type()).isEqualTo("speech.prepared");
        Map<?, ?> audio = (Map<?, ?>) prepared.payload().get("audio");
        assertThat(audio.get("mimeType")).isEqualTo("audio/pcm");
        assertThat(audio.get("url")).asString().contains("/speech/stream/");
        assertThat(prepared.payload().get("visemes")).isEqualTo(List.of());
        String streamId = (String) prepared.payload().get("utteranceId");
        assertThat(streams.contains(streamId)).isTrue();

        tasks.remove().run();
        var rendered = new ByteArrayOutputStream();
        streams.writeTo(streamId, rendered);
        assertThat(rendered.toByteArray()).isEqualTo(provider.pcm);
    }

    private static DefaultUnrealSpeechPreparationService service(
            ArrayDeque<Runnable> tasks,
            UnrealPcmStreamCache streams,
            UnrealEphemeralBroker outbound) {
        SpeechSynthesisUseCase segmentation = new SpeechSynthesisUseCase() {
            @Override public boolean isReady(VoiceProfileId voiceProfile) { return true; }
            @Override public List<SpeechSegment> prepare(String text) {
                return List.of(new SpeechSegment(0, text));
            }
            @Override public AudioOutput synthesize(SpeechSegment segment, VoiceProfileId voiceProfile) {
                throw new AssertionError("complete WAV fallback must not run");
            }
        };
        var metrics = new UnrealRuntimeMetrics(new SimpleMeterRegistry());
        return new DefaultUnrealSpeechPreparationService(
                segmentation, null,
                new UnrealAudioCache(Clock.systemUTC(), Duration.ofMinutes(1)),
                outbound, tasks::add, metrics, UnrealVisemeTimelinePort.unavailable(), streams);
    }

    private static final class StreamingProvider implements StreamingExpressiveSpeechSynthesisPort {
        private final byte[] pcm = new byte[9_600];

        @Override public boolean isStreamingReady(VoiceProfileId voiceProfile) { return true; }
        @Override public void streamPcm(
                ExpressiveSpeechRequest request,
                java.util.function.BooleanSupplier current,
                PcmSink sink) {
            assertThat(request.expression().style()).isEqualTo("fake_cute");
            assertThat(current.getAsBoolean()).isTrue();
            sink.started(PcmAudioFormat.QWEN_MONO_24K_S16LE);
            sink.chunk(pcm);
            sink.completed(pcm.length);
        }
    }
}
