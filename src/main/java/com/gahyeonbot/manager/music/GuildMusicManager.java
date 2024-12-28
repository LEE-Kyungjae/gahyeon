package com.gahyeonbot.manager.music;

import com.sedmelluq.discord.lavaplayer.player.AudioPlayer;
import com.sedmelluq.discord.lavaplayer.player.AudioPlayerManager;
import com.sedmelluq.discord.lavaplayer.track.AudioTrack;
import net.dv8tion.jda.api.audio.AudioSendHandler;
import net.dv8tion.jda.api.managers.AudioManager;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.List;

/*
오디오 플레이어 생성 (AudioPlayer)
트랙 스케줄러 생성 및 등록 (TrackScheduler)
디스코드 오디오 전송 핸들러 생성 (AudioSendHandler)
*/
public class GuildMusicManager {
    private static final Logger logger = LoggerFactory.getLogger(GuildMusicManager.class);

    private final AudioPlayer player;
    private final TrackScheduler scheduler;
    private final AudioSendHandler sendHandler;

    public GuildMusicManager(AudioPlayerManager manager, AudioManager audioManager) {
        if (manager == null) {
            throw new IllegalArgumentException("AudioPlayerManager는 null일 수 없습니다.");
        }

        this.player = manager.createPlayer();
        this.scheduler = new TrackScheduler(player, audioManager);
        this.player.addListener(scheduler);

        // AudioSendHandler 캐싱
        this.sendHandler = new AudioPlayerSendHandler(player);

        String connectedChannelName = audioManager.getConnectedChannel() != null
                ? audioManager.getConnectedChannel().getName()
                : "연결 없음";

        logger.info("GuildMusicManager 초기화됨 - AudioPlayer 상태: {}, AudioManager 채널: {}",
                player.getPlayingTrack() != null ? "재생 중" : "대기 중", connectedChannelName);
    }

    public AudioSendHandler getSendHandler() {
        return sendHandler;
    }

    public boolean isPlaying() {
        return player.getPlayingTrack() != null;
    }

    public boolean isQueueEmpty() {
        return scheduler.isQueueEmpty();
    }

    public void stop() {
        player.stopTrack();
        scheduler.clearQueue();
        logger.info("음악 재생 중단 및 대기열 초기화");
    }

    public boolean playOrQueueTrack(AudioTrack track) {
        if (!player.startTrack(track, true)) {
            scheduler.queue(track);
            return false; // 대기열에 추가됨
        }
        return true; // 즉시 재생됨
    }

    public String getCurrentTrackTitle() {
        AudioTrack currentTrack = player.getPlayingTrack();
        return (currentTrack != null) ? currentTrack.getInfo().title : "현재 재생 중인 트랙이 없습니다.";
    }

    public void queueTrack(AudioTrack track) {
        scheduler.queue(track);
    }

    public AudioTrack getCurrentTrack() {
        return player.getPlayingTrack();
    }

    public boolean skipCurrentTrack() {
        if (isPlaying()) {
            scheduler.nextTrack();
            return true;
        }
        return false;
    }
    public boolean isPaused() {
        return player.isPaused();
    }

    public void setPaused(boolean paused) {
        player.setPaused(paused);
    }
    public List<AudioTrack> getQueue() {
        return scheduler.getQueue(); // TrackScheduler의 대기열 반환
    }
    public void pause() {
        player.setPaused(true);
    }
    public void resume() {
        player.setPaused(false);
    }
    public void clearQueue() {
        scheduler.clearQueue();
    }

    public void stopPlayback(AudioManager audioManager) {
        stop(); // 음악 정지 및 대기열 초기화
        if (audioManager != null && audioManager.isConnected()) {
            audioManager.closeAudioConnection();
        }
    }
}

