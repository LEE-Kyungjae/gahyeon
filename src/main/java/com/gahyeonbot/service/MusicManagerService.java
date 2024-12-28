package com.gahyeonbot.service;

import com.gahyeonbot.commands.util.EmbedUtil;
import com.gahyeonbot.commands.util.ResponseUtil;
import com.gahyeonbot.manager.music.AudioManager;
import com.gahyeonbot.manager.music.GuildMusicManager;
import com.sedmelluq.discord.lavaplayer.player.AudioLoadResultHandler;
import com.sedmelluq.discord.lavaplayer.tools.FriendlyException;
import com.sedmelluq.discord.lavaplayer.track.AudioPlaylist;
import com.sedmelluq.discord.lavaplayer.track.AudioTrack;
import net.dv8tion.jda.api.entities.Guild;
import net.dv8tion.jda.api.events.interaction.command.SlashCommandInteractionEvent;

import java.util.Map;

public class MusicManagerService {
    private final Map<Long, GuildMusicManager> musicManagers;
    private final AudioManager audioManager;

    public MusicManagerService(Map<Long, GuildMusicManager> musicManagers, AudioManager audioManager) {
        this.musicManagers = musicManagers;
        this.audioManager = audioManager;
    }

    public GuildMusicManager getOrCreateGuildMusicManager(Guild guild) {
        return musicManagers.computeIfAbsent(
                guild.getIdLong(),
                id -> new GuildMusicManager(audioManager.getPlayerManager(), guild.getAudioManager())
        );
    }

    public boolean ensureConnectedToVoiceChannel(SlashCommandInteractionEvent event, Guild guild, GuildMusicManager musicManager) {
        if (guild.getAudioManager().isConnected()) return true;

        var voiceChannel = event.getMember().getVoiceState().getChannel();
        if (voiceChannel == null) {
            ResponseUtil.replyError(event, "먼저 보이스 채널에 입장하세요.");
            return false;
        }

        guild.getAudioManager().openAudioConnection(voiceChannel);
        guild.getAudioManager().setSelfDeafened(true);
        guild.getAudioManager().setSendingHandler(musicManager.getSendHandler());
        return true;
    }

    public void loadAndPlay(SlashCommandInteractionEvent event, String streamUrl, GuildMusicManager musicManager, String query,String albumCoverUrl) {
        audioManager.getPlayerManager().loadItem(streamUrl, new AudioLoadResultHandler() {
            @Override
            public void trackLoaded(AudioTrack track) {
                handleTrackLoaded(event, musicManager, track, albumCoverUrl,streamUrl);
            }

            @Override
            public void playlistLoaded(AudioPlaylist playlist) {
                if (!playlist.getTracks().isEmpty()) {
                    handleTrackLoaded(event, musicManager, playlist.getTracks().get(0),albumCoverUrl, streamUrl);
                } else {
                    ResponseUtil.replyError(event, "재생 가능한 트랙이 없습니다.");
                }
            }

            @Override
            public void noMatches() {
                ResponseUtil.replyError(event, "노래를 찾을 수 없습니다: **" + query + "**");
            }

            @Override
            public void loadFailed(FriendlyException e) {
                ResponseUtil.replyError(event, "🚨 로딩 오류 발생: " + e.getMessage());
            }
        });
    }

    private void handleTrackLoaded(SlashCommandInteractionEvent event, GuildMusicManager musicManager, AudioTrack track, String albumCoverUrl,String streamUrl ) {

        if (!musicManager.playOrQueueTrack(track)) {
            ResponseUtil.replyEmbed(event, EmbedUtil.createQueueAddedEmbed(track, event.getUser()));
        } else {
            ResponseUtil.replyEmbed(event, EmbedUtil.createNowPlayingEmbed(event, track, albumCoverUrl, track.getInfo().uri));
        }
    }

}
