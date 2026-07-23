package com.gahyeonbot.services.assistant;

import org.junit.jupiter.api.Test;

import java.nio.ByteBuffer;
import java.nio.ByteOrder;

import static org.assertj.core.api.Assertions.assertThat;

class WavEncoderTest {
    @Test
    void writesPcmAsDiscordCompatibleWav() {
        byte[] pcm = {1, 2, 3, 4, 5, 6, 7, 8};

        byte[] wav = WavEncoder.pcmToWav(pcm);

        assertThat(new String(wav, 0, 4)).isEqualTo("RIFF");
        assertThat(new String(wav, 8, 4)).isEqualTo("WAVE");
        assertThat(new String(wav, 36, 4)).isEqualTo("data");
        assertThat(ByteBuffer.wrap(wav, 40, 4).order(ByteOrder.LITTLE_ENDIAN).getInt()).isEqualTo(pcm.length);
        assertThat(wav).endsWith(pcm);
    }
}
