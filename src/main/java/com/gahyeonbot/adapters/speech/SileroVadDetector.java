package com.gahyeonbot.adapters.speech;

import ai.onnxruntime.*;
import com.gahyeonbot.application.speech.VoiceActivityDetector;
import java.io.IOException;
import java.nio.LongBuffer;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.Map;

/** Per-stream Silero v6 recurrent state. Input: 48 kHz stereo signed PCM16 LE. */
public final class SileroVadDetector implements VoiceActivityDetector {
    public static final String MODEL_RESOURCE = "/models/silero-vad/silero_vad-v6.2.3.onnx";
    private static final int WINDOW = 512;
    private static final int CONTEXT = 64;
    private final OrtEnvironment environment;
    private final OrtSession session;
    private final float threshold;
    private final float[][] input = new float[1][CONTEXT + WINDOW];
    private float[][][] state = new float[2][1][128];
    private int pending;
    private int decimationPhase;
    private boolean closed;

    public SileroVadDetector(float threshold, String modelPath) {
        if (!Float.isFinite(threshold) || threshold <= 0 || threshold >= 1) {
            throw new IllegalArgumentException("VAD threshold must be between 0 and 1");
        }
        this.threshold = threshold;
        environment = OrtEnvironment.getEnvironment();
        try (var options = new OrtSession.SessionOptions()) {
            options.setInterOpNumThreads(1);
            options.setIntraOpNumThreads(1);
            session = environment.createSession(readModel(modelPath), options);
        } catch (OrtException | IOException error) {
            throw new IllegalStateException("Cannot load Silero VAD model", error);
        }
    }

    private static byte[] readModel(String path) throws IOException {
        if (path != null && !path.isBlank()) return Files.readAllBytes(Path.of(path));
        try (var stream = SileroVadDetector.class.getResourceAsStream(MODEL_RESOURCE)) {
            if (stream == null) throw new IOException("Missing bundled Silero model");
            return stream.readAllBytes();
        }
    }

    @Override
    public Detection detect(byte[] pcm) {
        if (closed) throw new IllegalStateException("VAD is closed");
        if (pcm == null || pcm.length % 4 != 0) {
            throw new IllegalArgumentException("Expected complete stereo PCM16 frames");
        }
        long voiceSamples = 0;
        for (int offset = 0; offset < pcm.length; offset += 4) {
            // Same 48 -> 16 kHz decimation as the existing TEN adapter.
            if (decimationPhase == 0) {
                int left = (short) ((pcm[offset] & 255) | (pcm[offset + 1] << 8));
                int right = (short) ((pcm[offset + 2] & 255) | (pcm[offset + 3] << 8));
                input[0][CONTEXT + pending++] = ((left + right) / 2) / 32768f;
                if (pending == WINDOW) {
                    if (infer() >= threshold) voiceSamples += WINDOW;
                    System.arraycopy(input[0], WINDOW, input[0], 0, CONTEXT);
                    pending = 0;
                }
            }
            decimationPhase = (decimationPhase + 1) % 3;
        }
        return new Detection(voiceSamples > 0, voiceSamples);
    }

    private float infer() {
        try (var audio = OnnxTensor.createTensor(environment, input);
             var memory = OnnxTensor.createTensor(environment, state);
             var rate = OnnxTensor.createTensor(environment, LongBuffer.wrap(new long[]{16000}), new long[0]);
             var result = session.run(Map.of("input", audio, "state", memory, "sr", rate))) {
            float probability = ((float[][]) result.get("output").orElseThrow().getValue())[0][0];
            state = (float[][][]) result.get("stateN").orElseThrow().getValue();
            return probability;
        } catch (OrtException error) {
            throw new IllegalStateException("Silero VAD inference failed", error);
        }
    }

    @Override
    public void close() {
        if (closed) return;
        closed = true;
        try {
            session.close();
        } catch (OrtException error) {
            throw new IllegalStateException("Cannot close Silero VAD", error);
        }
    }
}
