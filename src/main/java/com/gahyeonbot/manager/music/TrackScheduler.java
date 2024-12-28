package com.gahyeonbot.manager.music;

import net.dv8tion.jda.api.managers.AudioManager;
import com.sedmelluq.discord.lavaplayer.player.AudioPlayer;
import com.sedmelluq.discord.lavaplayer.player.event.AudioEventAdapter;
import com.sedmelluq.discord.lavaplayer.track.AudioTrack;
import com.sedmelluq.discord.lavaplayer.track.AudioTrackEndReason;

import java.util.List;
import java.util.concurrent.BlockingQueue;
import java.util.concurrent.LinkedBlockingQueue;

/*
음악 대기열 관리
음악 재생 자동 전환
이벤트 리스너로 트랙 종료 감지
대기열 초기화 및 상태 확인
*/
public class TrackScheduler extends AudioEventAdapter {

    private final AudioPlayer player;
    private final TrackQueue trackQueue; // 대기열 관리 클래스
    private final AudioManager audioManager;

    public TrackScheduler(AudioPlayer player, AudioManager audioManager) {
        this.player = player;
        this.audioManager = audioManager;
        this.trackQueue = new TrackQueue();
    }

    public void queue(AudioTrack track) {
        if (!player.startTrack(track, true)) {
            trackQueue.addTrack(track);
        }
    }

    public List<AudioTrack> getQueue() {
        return trackQueue.getTracks();
    }

    public boolean isQueueEmpty() {
        return trackQueue.isEmpty();
    }

    public void nextTrack() {
        AudioTrack nextTrack = trackQueue.pollTrack();
        if (nextTrack != null) {
            player.startTrack(nextTrack, false);
        } else {
            closeConnection();
        }
    }

    public void clearQueue() {
        trackQueue.clear();
    }

    private void closeConnection() {
        if (audioManager != null && audioManager.getConnectedChannel() != null) {
            audioManager.closeAudioConnection();
            System.out.println("보이스 채널 연결이 종료되었습니다.");
        }
    }

    @Override
    public void onTrackEnd(AudioPlayer player, AudioTrack track, AudioTrackEndReason endReason) {
        if (endReason.mayStartNext) {
            nextTrack();
        } else {
            System.out.println("트랙 종료: " + track.getInfo().title + " (이유: " + endReason + ")");
            nextTrack();
        }
    }
}
