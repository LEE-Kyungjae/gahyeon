package com.gahyeonbot.adapters.unreal;

import com.gahyeonbot.core.speech.AudioOutput;

import java.util.ArrayList;
import java.util.List;

/**
 * Deterministic waveform-guided fallback for PCM WAV providers that expose no phoneme timing.
 * This is deliberately labelled heuristic: PCM energy supplies speech/silence timing and weight,
 * while Korean vowel classes supply mouth shape. It is not exact forced alignment.
 */
public final class PcmWavKoreanVisemeTimeline implements UnrealVisemeTimelinePort {
    private static final int MAX_CUES = 256;
    private static final int WINDOW_MILLIS = 20;

    @Override
    public List<UnrealVisemeCue> align(String text, AudioOutput audio) {
        PcmInfo pcm = pcmInfo(audio);
        if (pcm == null || text == null || text.isBlank()) return List.of();
        List<Integer> speakable = text.codePoints()
                .filter(PcmWavKoreanVisemeTimeline::speakable)
                .boxed()
                .toList();
        if (speakable.isEmpty()) return List.of();

        List<EnergyWindow> active = activeWindows(audio.data(), pcm);
        if (active.isEmpty()) return List.of();
        int count = Math.min(Math.min(MAX_CUES, speakable.size()), active.size());
        var cues = new ArrayList<UnrealVisemeCue>(count);
        for (int index = 0; index < count; index++) {
            int sourceIndex = (int) ((long) index * speakable.size() / count);
            int windowIndex = (int) ((long) index * active.size() / count);
            EnergyWindow window = active.get(windowIndex);
            long atMs = window.atMs();
            long voicedRunEndMs = atMs + window.durationMs();
            for (int scan = windowIndex + 1; scan < active.size(); scan++) {
                EnergyWindow following = active.get(scan);
                if (following.atMs() > voicedRunEndMs) break;
                voicedRunEndMs = Math.max(
                        voicedRunEndMs, following.atMs() + following.durationMs());
            }
            long nextCueAtMs = pcm.durationMs();
            if (index + 1 < count) {
                int nextWindowIndex = (int) ((long) (index + 1) * active.size() / count);
                nextCueAtMs = active.get(nextWindowIndex).atMs();
            }
            // Hold a semantic mouth shape across its audible syllable instead of
            // flashing it for one 20 ms analysis window. Never bridge a real pause.
            long cueMs = Math.min(180, Math.max(
                    WINDOW_MILLIS, Math.min(nextCueAtMs, voicedRunEndMs) - atMs));
            cueMs = Math.min(cueMs, Math.max(1, pcm.durationMs() - atMs));
            cues.add(new UnrealVisemeCue(
                    semantic(speakable.get(sourceIndex)), atMs, cueMs, window.weight()));
        }
        return List.copyOf(cues);
    }

    @Override
    public String source() {
        return "waveform-guided";
    }

    static long pcmWavDurationMs(AudioOutput audio) {
        PcmInfo info = pcmInfo(audio);
        return info == null ? -1 : info.durationMs();
    }

    private static PcmInfo pcmInfo(AudioOutput audio) {
        if (audio == null || !("audio/wav".equals(audio.mediaType())
                || "audio/x-wav".equals(audio.mediaType()))) return null;
        byte[] bytes = audio.data();
        if (bytes.length < 44 || !fourCc(bytes, 0, "RIFF") || !fourCc(bytes, 8, "WAVE")) return null;
        int offset = 12;
        int format = -1;
        int channels = 0;
        long sampleRate = 0;
        int blockAlign = 0;
        int bitsPerSample = 0;
        long dataBytes = -1;
        int dataOffset = -1;
        while (offset <= bytes.length - 8) {
            long chunkBytes = u32(bytes, offset + 4);
            long dataStart = (long) offset + 8;
            if (chunkBytes > Integer.MAX_VALUE || dataStart + chunkBytes > bytes.length) return null;
            if (fourCc(bytes, offset, "fmt ") && chunkBytes >= 16) {
                format = u16(bytes, offset + 8);
                channels = u16(bytes, offset + 10);
                sampleRate = u32(bytes, offset + 12);
                blockAlign = u16(bytes, offset + 20);
                bitsPerSample = u16(bytes, offset + 22);
            } else if (fourCc(bytes, offset, "data")) {
                dataBytes = chunkBytes;
                dataOffset = (int) dataStart;
            }
            long next = dataStart + chunkBytes + (chunkBytes & 1L);
            if (next > Integer.MAX_VALUE || next <= offset) return null;
            offset = (int) next;
        }
        if (format != 1 || (channels != 1 && channels != 2) || bitsPerSample != 16
                || sampleRate < 8_000 || sampleRate > 192_000
                || blockAlign != channels * 2 || dataBytes <= 0
                || dataBytes % blockAlign != 0 || dataOffset < 0) return null;
        long frames = dataBytes / blockAlign;
        return new PcmInfo(sampleRate, channels, blockAlign, dataOffset, (int) dataBytes,
                Math.max(1, frames * 1_000 / sampleRate));
    }

    private static List<EnergyWindow> activeWindows(byte[] bytes, PcmInfo pcm) {
        int framesPerWindow = Math.max(1, (int) (pcm.sampleRate() * WINDOW_MILLIS / 1_000));
        int totalFrames = pcm.dataBytes() / pcm.blockAlign();
        var levels = new ArrayList<Double>((totalFrames + framesPerWindow - 1) / framesPerWindow);
        double peak = 0;
        for (int firstFrame = 0; firstFrame < totalFrames; firstFrame += framesPerWindow) {
            int lastFrame = Math.min(totalFrames, firstFrame + framesPerWindow);
            double squareSum = 0;
            int sampleCount = 0;
            for (int frame = firstFrame; frame < lastFrame; frame++) {
                int frameOffset = pcm.dataOffset() + frame * pcm.blockAlign();
                for (int channel = 0; channel < pcm.channels(); channel++) {
                    int sampleOffset = frameOffset + channel * 2;
                    int sample = (short) (Byte.toUnsignedInt(bytes[sampleOffset])
                            | Byte.toUnsignedInt(bytes[sampleOffset + 1]) << 8);
                    squareSum += (double) sample * sample;
                    sampleCount++;
                }
            }
            double rms = sampleCount == 0 ? 0 : Math.sqrt(squareSum / sampleCount);
            levels.add(rms);
            peak = Math.max(peak, rms);
        }
        if (peak < 180) return List.of();
        var sorted = new ArrayList<>(levels);
        sorted.sort(Double::compareTo);
        double noiseFloor = sorted.get(Math.min(sorted.size() - 1, sorted.size() / 5));
        double adaptive = Math.max(noiseFloor * 2.5, peak * 0.08);
        // A continuously voiced clip has no low-energy percentile; never let the
        // estimated floor raise the gate above the signal that defined the peak.
        double threshold = Math.max(180, Math.min(peak * 0.60, adaptive));
        boolean[] voiced = new boolean[levels.size()];
        for (int index = 0; index < levels.size(); index++) voiced[index] = levels.get(index) >= threshold;
        // A 20 ms dilation keeps unvoiced consonants attached while preserving real pauses.
        boolean[] expanded = voiced.clone();
        for (int index = 0; index < voiced.length; index++) if (voiced[index]) {
            if (index > 0) expanded[index - 1] = true;
            if (index + 1 < expanded.length) expanded[index + 1] = true;
        }
        var result = new ArrayList<EnergyWindow>();
        for (int index = 0; index < expanded.length; index++) if (expanded[index]) {
            long atMs = (long) index * WINDOW_MILLIS;
            long durationMs = Math.min(WINDOW_MILLIS, pcm.durationMs() - atMs);
            double normalized = Math.min(1, levels.get(index) / Math.max(threshold, peak * 0.65));
            double weight = Math.max(0.35, 0.35 + normalized * 0.65);
            result.add(new EnergyWindow(atMs, Math.max(1, durationMs), weight));
        }
        return List.copyOf(result);
    }

    private record PcmInfo(long sampleRate, int channels, int blockAlign, int dataOffset,
                           int dataBytes, long durationMs) {}
    private record EnergyWindow(long atMs, long durationMs, double weight) {}

    private static boolean speakable(int codePoint) {
        return Character.isLetterOrDigit(codePoint) || codePoint >= 0xAC00 && codePoint <= 0xD7A3;
    }

    private static String semantic(int codePoint) {
        if (codePoint < 0xAC00 || codePoint > 0xD7A3) return "aa";
        int vowel = (codePoint - 0xAC00) / 28 % 21;
        return switch (vowel) {
            case 0, 2 -> "aa";                 // ㅏ ㅑ
            case 1, 3, 4, 5, 6, 7 -> "E";    // ㅐ ㅒ ㅓ ㅔ ㅕ ㅖ
            case 8, 9, 10, 11, 12 -> "O";    // ㅗ ㅘ ㅙ ㅚ ㅛ
            case 13, 14, 15, 16, 17, 18 -> "U"; // ㅜ ㅝ ㅞ ㅟ ㅠ ㅡ
            default -> "I";                    // ㅢ ㅣ
        };
    }

    private static int u16(byte[] bytes, int offset) {
        return Byte.toUnsignedInt(bytes[offset]) | Byte.toUnsignedInt(bytes[offset + 1]) << 8;
    }

    private static long u32(byte[] bytes, int offset) {
        return Integer.toUnsignedLong(Byte.toUnsignedInt(bytes[offset])
                | Byte.toUnsignedInt(bytes[offset + 1]) << 8
                | Byte.toUnsignedInt(bytes[offset + 2]) << 16
                | Byte.toUnsignedInt(bytes[offset + 3]) << 24);
    }

    private static boolean fourCc(byte[] bytes, int offset, String expected) {
        if (offset < 0 || offset + 4 > bytes.length) return false;
        for (int index = 0; index < 4; index++) {
            if (bytes[offset + index] != (byte) expected.charAt(index)) return false;
        }
        return true;
    }
}
