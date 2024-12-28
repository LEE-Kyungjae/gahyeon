package com.gahyeonbot.manager.music;

import com.sedmelluq.discord.lavaplayer.player.AudioPlayer;
import com.sedmelluq.discord.lavaplayer.track.playback.AudioFrame;
import net.dv8tion.jda.api.audio.AudioSendHandler;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.nio.ByteBuffer;

/**
 * AudioPlayerSendHandler
 * - Discord API의 AudioSendHandler를 구현하여 LavaPlayer의 오디오 데이터를 Discord 보이스 채널로 전송.
 */
public class AudioPlayerSendHandler implements AudioSendHandler {
    private static final Logger logger = LoggerFactory.getLogger(AudioPlayerSendHandler.class);
    private static final ByteBuffer EMPTY_BUFFER = ByteBuffer.allocate(0); // 재사용 가능한 빈 ByteBuffer

    private final AudioPlayer audioPlayer;
    private AudioFrame lastFrame;

    /**
     * AudioPlayerSendHandler 생성자
     *
     * @param audioPlayer LavaPlayer의 AudioPlayer 인스턴스
     */
    public AudioPlayerSendHandler(AudioPlayer audioPlayer) {
        this.audioPlayer = audioPlayer;
    }

    /**
     * 오디오 데이터를 제공할 수 있는지 확인.
     *
     * @return true면 오디오 데이터 제공 가능, false면 불가능.
     */
    @Override
    public boolean canProvide() {
        lastFrame = audioPlayer.provide();
        if (lastFrame == null) {
            logger.warn("AudioPlayer가 오디오 데이터를 제공하지 못했습니다.");
            return false;
        }
        return true;
    }

    /**
     * 20ms 길이의 오디오 데이터를 제공.
     *
     * @return 오디오 데이터가 담긴 ByteBuffer.
     */
    @Override
    public ByteBuffer provide20MsAudio() {
        if (lastFrame == null) {
            logger.warn("Null 오디오 프레임 제공. 빈 데이터 반환.");
            return EMPTY_BUFFER;
        }
        return ByteBuffer.wrap(lastFrame.getData());
    }

    /**
     * 오디오 데이터가 Opus 형식인지 확인.
     *
     * @return 항상 true (LavaPlayer는 Opus 데이터를 제공합니다).
     */
    @Override
    public boolean isOpus() {
        return true;
    }
}
