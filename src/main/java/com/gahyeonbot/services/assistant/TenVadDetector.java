package com.gahyeonbot.services.assistant;

import com.sun.jna.Library;
import com.sun.jna.Native;
import com.sun.jna.Pointer;
import com.sun.jna.ptr.PointerByReference;

import java.io.IOException;
import java.io.InputStream;
import java.nio.file.Files;
import java.nio.file.Path;

/**
 * Per-speaker TEN VAD wrapper. Input is Discord's 48 kHz stereo, signed
 * 16-bit little-endian PCM. TEN VAD receives 16 kHz mono frames.
 */
final class TenVadDetector implements AutoCloseable {
    private static final String RESOURCE = "/native/ten-vad/linux-x64/libten_vad.so";
    private static volatile TenVadLibrary library;

    private final TenVadLibrary nativeLibrary;
    private final int hopSize;
    private final PointerByReference handle = new PointerByReference();
    private short[] pending;
    private int pendingSize;

    TenVadDetector(int hopSize, float threshold) {
        this.nativeLibrary = loadLibrary();
        this.hopSize = hopSize;
        this.pending = new short[hopSize * 2];
        int result = nativeLibrary.ten_vad_create(handle, hopSize, threshold);
        if (result != 0) throw new IllegalStateException("TEN VAD 초기화 실패: " + result);
    }

    Detection processDiscordPcm(byte[] pcm) {
        int voiceFrames = 0;
        int totalFrames = 0;
        float maxProbability = 0;
        for (int offset = 0; offset + 11 < pcm.length; offset += 12) {
            int left = sampleLittleEndian(pcm, offset);
            int right = sampleLittleEndian(pcm, offset + 2);
            append((short) ((left + right) / 2));
            if (pendingSize == hopSize) {
                float[] probability = new float[1];
                int[] flag = new int[1];
                int result = nativeLibrary.ten_vad_process(
                        handle.getValue(), pending, hopSize, probability, flag);
                if (result != 0) throw new IllegalStateException("TEN VAD 처리 실패: " + result);
                totalFrames++;
                if (flag[0] == 1) voiceFrames++;
                maxProbability = Math.max(maxProbability, probability[0]);
                pendingSize = 0;
            }
        }
        return new Detection(voiceFrames > 0, voiceFrames, totalFrames, maxProbability);
    }

    private void append(short sample) {
        if (pendingSize == pending.length) {
            short[] expanded = new short[pending.length * 2];
            System.arraycopy(pending, 0, expanded, 0, pending.length);
            pending = expanded;
        }
        pending[pendingSize++] = sample;
    }

    private static int sampleLittleEndian(byte[] pcm, int offset) {
        return (short) ((pcm[offset] & 0xff) | (pcm[offset + 1] << 8));
    }

    @Override
    public void close() {
        Pointer pointer = handle.getValue();
        if (pointer != null) nativeLibrary.ten_vad_destroy(handle);
        handle.setValue(null);
    }

    record Detection(boolean voice, int voiceFrames, int totalFrames, float probability) {}

    private interface TenVadLibrary extends Library {
        int ten_vad_create(PointerByReference handle, int hopSize, float threshold);
        int ten_vad_process(Pointer handle, short[] audioData, int length, float[] probability, int[] flag);
        int ten_vad_destroy(PointerByReference handle);
    }

    private static TenVadLibrary loadLibrary() {
        TenVadLibrary current = library;
        if (current != null) return current;
        synchronized (TenVadDetector.class) {
            if (library != null) return library;
            String explicit = System.getenv("TEN_VAD_LIBRARY_PATH");
            Path path = explicit == null || explicit.isBlank() ? extractLibrary() : Path.of(explicit);
            library = Native.load(path.toAbsolutePath().toString(), TenVadLibrary.class);
            return library;
        }
    }

    private static Path extractLibrary() {
        try (InputStream input = TenVadDetector.class.getResourceAsStream(RESOURCE)) {
            if (input == null) throw new IllegalStateException("TEN VAD 라이브러리가 JAR에 없습니다.");
            Path dir = Path.of(System.getProperty("java.io.tmpdir"), "gahyeonbot-ten-vad");
            Files.createDirectories(dir);
            Path target = dir.resolve("libten_vad.so");
            if (!Files.exists(target) || Files.size(target) == 0) {
                Files.copy(input, target, java.nio.file.StandardCopyOption.REPLACE_EXISTING);
            }
            target.toFile().setExecutable(true, true);
            return target;
        } catch (IOException e) {
            throw new IllegalStateException("TEN VAD 라이브러리 추출 실패", e);
        }
    }
}
