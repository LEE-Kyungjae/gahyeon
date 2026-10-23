package com.gahyeonbot.adapters.speech;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.gahyeonbot.application.speech.*;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.condition.EnabledIfEnvironmentVariable;
import javax.sound.sampled.AudioSystem;
import java.nio.file.*;
import java.util.*;
import static org.assertj.core.api.Assertions.assertThat;

/** Opt-in real native/model inference benchmark; never connects to Discord or STT. */
@EnabledIfEnvironmentVariable(named = "VAD_BENCHMARK_DIR", matches = ".+")
class VadComparisonTest {
    @Test void compareRealProvidersOnIdenticalPcm() throws Exception {
        Path dir = Path.of(System.getenv("VAD_BENCHMARK_DIR"));
        var mapper = new ObjectMapper();
        var manifest = mapper.readTree(dir.resolve("fixtures.json").toFile());
        var rows = new ArrayList<Map<String, Object>>();
        for (String provider : List.of("ten", "silero")) {
            for (float threshold : new float[]{.3f, .5f, .7f}) {
                for (long minimumSpeech : new long[]{150, 300, 500}) {
                for (var fixture : manifest.get("fixtures")) {
                    String name = fixture.get("file").asText();
                    byte[] pcm;
                    try (var audio = AudioSystem.getAudioInputStream(dir.resolve(name).toFile())) {
                        assertThat(audio.getFormat().getSampleRate()).isEqualTo(48000);
                        assertThat(audio.getFormat().getChannels()).isEqualTo(2);
                        assertThat(audio.getFormat().getSampleSizeInBits()).isEqualTo(16);
                        pcm = audio.readAllBytes();
                    }
                    var detector = VoiceActivityDetectorFactory.create(provider, 256, threshold, "");
                    long[] detected = {0};
                    VoiceActivityDetector measured = packet -> {
                        var detection = detector.detect(packet);
                        detected[0] += detection.voiceSamples();
                        return detection;
                    };
                    var policy = new UtteranceSegmentationPolicy(192000, 20, 96000,
                            1500, minimumSpeech, 1000, 2000, 700, 16000);
                    int utterances = 0;
                    long firstSpeech = -1;
                    long firstCompleted = -1;
                    long elapsed = 0;
                    long nextPoll = 250;
                    long speechBins = 0, nonSpeechBins = 0, missedSpeechBins = 0, falseSpeechBins = 0;
                    int packetBytes = fixture.has("segments") ? 6144 : 3840;
                    try (detector; var accumulator = new StreamingUtteranceAccumulator(policy, measured, 0)) {
                        for (int offset = 0; offset < pcm.length; offset += packetBytes) {
                            long now = offset * 1000L / 192000;
                            long before = detected[0];
                            long start = System.nanoTime();
                            accumulator.accept(Arrays.copyOfRange(pcm, offset, Math.min(pcm.length, offset + packetBytes)), now);
                            elapsed += System.nanoTime() - start;
                            if (detected[0] > before && firstSpeech < 0) firstSpeech = now;
                            if (fixture.has("segments")) {
                                double midpoint = (now + packetBytes * 500.0 / 192000) / 1000.0;
                                boolean expected = false;
                                for (var segment : fixture.get("segments")) {
                                    if (midpoint >= segment.get(0).asDouble() && midpoint < segment.get(1).asDouble()) {
                                        expected = segment.get(2).asInt() == 1;
                                        break;
                                    }
                                }
                                boolean predicted = detected[0] > before;
                                if (expected) {
                                    speechBins++;
                                    if (!predicted) missedSpeechBins++;
                                } else {
                                    nonSpeechBins++;
                                    if (predicted) falseSpeechBins++;
                                }
                            }
                            if (now >= nextPoll) {
                                nextPoll += 250;
                                if (accumulator.poll(now).isPresent()) {
                                    utterances++;
                                    if (firstCompleted < 0) firstCompleted = now;
                                }
                            }
                        }
                        if (accumulator.poll(pcm.length * 1000L / 192000 + 3000).isPresent()) utterances++;
                    }
                    var row = new LinkedHashMap<String, Object>();
                    row.put("provider", provider); row.put("threshold", threshold);
                    row.put("minimumSpeechMs", minimumSpeech);
                    row.put("fixture", name); row.put("category", fixture.get("category").asText());
                    row.put("speechExpected", fixture.get("speechExpected").asBoolean());
                    row.put("packetMs", packetBytes / 192);
                    row.put("durationMs", pcm.length * 1000L / 192000);
                    row.put("detectedSpeechMs", detected[0] / 16);
                    row.put("speechBins", speechBins); row.put("nonSpeechBins", nonSpeechBins);
                    row.put("missedSpeechBins", missedSpeechBins); row.put("falseSpeechBins", falseSpeechBins);
                    row.put("utterances", utterances); row.put("firstSpeechMs", firstSpeech);
                    row.put("firstCompletedMs", firstCompleted); row.put("inferenceMs", elapsed / 1e6);
                    rows.add(row);
                }
                }
            }
        }
        mapper.writerWithDefaultPrettyPrinter().writeValue(dir.resolve("results.json").toFile(), rows);
    }
}
