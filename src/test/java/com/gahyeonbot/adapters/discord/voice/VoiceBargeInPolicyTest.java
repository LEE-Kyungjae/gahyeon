package com.gahyeonbot.adapters.discord.voice;

import org.junit.jupiter.api.Test;

import static org.assertj.core.api.Assertions.assertThat;

class VoiceBargeInPolicyTest {
    @Test
    void blocksARecentMicrophoneEchoWithoutBlockingMeaningfulBargeIn() {
        var policy = new VoiceBargeInPolicy();
        policy.rememberBotSpeech("괜찮아요. 천천히 이야기해도 돼요.", 1_000);

        assertThat(policy.isLikelySelfEcho("괜찮아요 천천히 이야기해도 돼요", 2_000)).isTrue();
        assertThat(policy.isLikelySelfEcho("아니, 지금은 다른 이야기를 할게", 2_000)).isFalse();
    }

    @Test
    void expiresEchoMemoryAndIgnoresTinyFragments() {
        var policy = new VoiceBargeInPolicy();
        policy.rememberBotSpeech("잠깐만요. 정리해서 답할게요.", 1_000);

        assertThat(policy.isLikelySelfEcho("잠깐", 2_000)).isFalse();
        assertThat(policy.isLikelySelfEcho("잠깐만요 정리해서 답할게요", 31_001)).isFalse();
        assertThat(policy.isLikelySelfEcho("네", 2_000)).isFalse();
    }
}
