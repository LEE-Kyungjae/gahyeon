package com.gahyeonbot.commands.music;

import com.gahyeonbot.ICommand;
import com.gahyeonbot.config.Description;
import com.gahyeonbot.manager.AudioManager;
import com.gahyeonbot.manager.GuildMusicManager;
import com.gahyeonbot.service.SpotifySearchService;
import com.sedmelluq.discord.lavaplayer.player.AudioLoadResultHandler;
import com.sedmelluq.discord.lavaplayer.tools.FriendlyException;
import com.sedmelluq.discord.lavaplayer.track.AudioPlaylist;
import com.sedmelluq.discord.lavaplayer.track.AudioTrack;
import net.dv8tion.jda.api.EmbedBuilder;
import net.dv8tion.jda.api.entities.Guild;
import net.dv8tion.jda.api.events.interaction.command.SlashCommandInteractionEvent;
import net.dv8tion.jda.api.interactions.commands.OptionType;
import net.dv8tion.jda.api.interactions.commands.build.OptionData;

import java.awt.*;
import java.util.List;
import java.util.Map;

import static com.gahyeonbot.manager.AudioManager.playerManager;

public class Play implements ICommand {
    private final Map<Long, GuildMusicManager> musicManagers;
    private final SpotifySearchService spotifySearchService;

    public Play(AudioManager audioManager, Map<Long, GuildMusicManager> musicManagers, SpotifySearchService spotifySearchService) {
        this.musicManagers = musicManagers;
        this.spotifySearchService = spotifySearchService;
    }
    @Override
    public String getName() {
        return Description.PLAY_NAME;
    }

    @Override
    public String getDescription() {
        return Description.PLAY_DESC;
    }

    @Override
    public String getDetailedDescription() {
        return Description.PLAY_DETAIL;
    }

    @Override
    public List<OptionData> getOptions() {
        return List.of(
                new OptionData(OptionType.STRING, "노래정보", "노래 제목을 입력하세요.", true)
        );
    }

    @Override
    public void execute(SlashCommandInteractionEvent event) {
        String query = event.getOption("노래정보").getAsString();
        Guild guild = event.getGuild();

        if (guild == null) {
            event.reply("길드를 찾을 수 없습니다.").setEphemeral(true).queue();
            return;
        }
        GuildMusicManager musicManager = musicManagers.computeIfAbsent(
                guild.getIdLong(), id -> new GuildMusicManager(playerManager)
        );

        if (!guild.getAudioManager().isConnected()) {
            var voiceChannel = event.getMember().getVoiceState().getChannel();
            if (voiceChannel == null) {
                event.reply("먼저 보이스 채널에 입장하세요.").setEphemeral(true).queue();
                return;
            }
            guild.getAudioManager().openAudioConnection(voiceChannel);

            // 오디오 전송 핸들러 설정
            guild.getAudioManager().setSendingHandler(musicManager.getSendHandler());
        }
        // Spotify 트랙 검색
        var track = spotifySearchService.searchTrack(query);
        if (track == null) {
            event.reply("Spotify에서 곡을 찾을 수 없습니다.").setEphemeral(true).queue();
            return;
        }

//        String soundCloudQuery = audioManager.getSoundCloudTrackFromSpotify(query);
//        if (soundCloudQuery == null) {
//            event.reply("곡을 찾을 수 없습니다.").setEphemeral(true).queue();
//            return;
//        }

        String soundCloudQuery = "scsearch:" + track.getName() + " " + track.getArtists()[0].getName();
        playerManager.loadItem(soundCloudQuery, new AudioLoadResultHandler() {
            @Override
            public void trackLoaded(AudioTrack track) {
                if (!musicManager.player.startTrack(track, true)) {
                    musicManager.scheduler.queue(track);
                    event.reply("🎵 대기열에 추가되었습니다: **" + track.getInfo().title + "**").queue();
                } else {
                    EmbedBuilder embed = new EmbedBuilder();
                    embed.setTitle("🎵 재생 시작!")
                            .setDescription("**" + track.getInfo().title + "**")
                            .addField("아티스트", track.getInfo().author, true)
                            .addField("상태", "재생 중", false)
                            .setThumbnail(track.getInfo().uri) // 앨범 커버
                            .setFooter("요청자: " + event.getUser().getName(), event.getUser().getAvatarUrl())
                            .setColor(Color.GREEN);
                    event.replyEmbeds(embed.build()).queue();

                }
            }

            @Override
            public void playlistLoaded(AudioPlaylist playlist) {
                if (playlist.isSearchResult() && !playlist.getTracks().isEmpty()) {
                    AudioTrack firstTrack = playlist.getTracks().get(0);
                    trackLoaded(firstTrack);
                } else {
                    event.reply("노래를 찾을 수 없습니다.").setEphemeral(true).queue();
                }
            }

            @Override
            public void noMatches() {
                event.reply("노래를 찾을 수 없습니다.").setEphemeral(true).queue();
            }

            @Override
            public void loadFailed(FriendlyException e) {
                event.reply("🚨 로딩 오류 발생: " + e.getMessage()).setEphemeral(true).queue();
                e.printStackTrace();  // 디버깅 로그 추가
            }
        });
    }
}