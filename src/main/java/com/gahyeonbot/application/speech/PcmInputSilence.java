package com.gahyeonbot.application.speech;

import javax.sound.sampled.AudioFormat;
import javax.sound.sampled.AudioSystem;
import java.io.ByteArrayInputStream;

/** Exact digital silence only; quiet speech and unsupported audio are never suppressed. */
public final class PcmInputSilence {
    private PcmInputSilence() {}

    public static boolean isDigitalSilence(byte[] wav) {
        if (wav == null || wav.length < 44) return false;
        // Do not broaden the STT input contract to other containers accepted by Java Sound.
        if (wav[0] != 'R' || wav[1] != 'I' || wav[2] != 'F' || wav[3] != 'F'
                || wav[8] != 'W' || wav[9] != 'A' || wav[10] != 'V' || wav[11] != 'E') return false;
        try (var audio = AudioSystem.getAudioInputStream(new ByteArrayInputStream(wav))) {
            var format = audio.getFormat();
            if (!AudioFormat.Encoding.PCM_SIGNED.equals(format.getEncoding())
                    || format.getSampleSizeInBits() != 16 || audio.getFrameLength() <= 0) return false;
            byte[] buffer = new byte[4096];
            long count = 0;
            int read;
            while ((read = audio.read(buffer)) != -1) {
                if (read == 0) return false;
                count += read;
                for (int i = 0; i < read; i++) if (buffer[i] != 0) return false;
            }
            return count > 0 && count == audio.getFrameLength() * format.getFrameSize();
        } catch (Exception unsupportedOrMalformed) {
            return false;
        }
    }
}
