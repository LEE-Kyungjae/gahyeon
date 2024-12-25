package com.gahyeonbot.manager.music;

import com.sedmelluq.discord.lavaplayer.player.AudioPlayer;
import com.sedmelluq.discord.lavaplayer.player.AudioPlayerManager;
import net.dv8tion.jda.api.audio.AudioSendHandler;
import net.dv8tion.jda.api.managers.AudioManager;

/*
오디오 플레이어 생성 (AudioPlayer)
트랙 스케줄러 생성 및 등록 (TrackScheduler)
디스코드 오디오 전송 핸들러 생성 (AudioSendHandler)
*/
public class GuildMusicManager {
    public final AudioPlayer player;
    public final TrackScheduler scheduler;

    public GuildMusicManager(AudioPlayerManager manager, AudioManager audioManager) {
        this.player = manager.createPlayer();
        this.scheduler = new TrackScheduler(player, audioManager);
        this.player.addListener(scheduler);
    }

    public AudioSendHandler getSendHandler() {
        return new AudioPlayerSendHandler(player);
    }
}


