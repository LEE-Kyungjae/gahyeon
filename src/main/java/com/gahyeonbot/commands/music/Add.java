package com.gahyeonbot.commands.music;

import com.gahyeonbot.commands.base.ICommand;
import com.gahyeonbot.commands.base.Description;
import com.gahyeonbot.manager.music.AudioManager;
import com.gahyeonbot.manager.music.GuildMusicManager;
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

import static com.gahyeonbot.manager.music.AudioManager.playerManager;

public class Add implements ICommand {
    private final Map<Long, GuildMusicManager> musicManagers;
    private final SpotifySearchService spotifySearchService;

    public Add(AudioManager audioManager, Map<Long, GuildMusicManager> musicManagers, SpotifySearchService spotifySearchService) {
        this.musicManagers = musicManagers;
        this.spotifySearchService = spotifySearchService;
    }
    @Override
    public String getName() {
        return Description.ADD_NAME;
    }

    @Override
    public String getDescription() {
        return Description.ADD_DESC;
    }

    @Override
    public String getDetailedDescription() {
        return Description.ADD_DETAIL;
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
                guild.getIdLong(),
                id -> new GuildMusicManager(playerManager, guild.getAudioManager()) // AudioManager 전달
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
                String sourceUrl = track.getInfo().uri; // 스트리밍 출처 URL 가져오기

                if (!musicManager.player.startTrack(track, true)) {
                    musicManager.scheduler.queue(track);
                    event.reply("🎵 대기열에 추가되었습니다: **" + track.getInfo().title + "**").queue();
                } else {
                    EmbedBuilder embed = new EmbedBuilder();
                    embed.setTitle("🎵 재생 시작!")
                            .setDescription("**" + track.getInfo().title + "**")
                            .addField("아티스트", track.getInfo().author, true)
                            .addField("상태", "재생 중", false)
                            .addField("스트리밍 출처", "[여기 클릭](" + sourceUrl + ")", false) // 스트리밍 URL 추가
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
                    // SoundCloud에서 검색했으나 트랙을 찾을 수 없을 때
                    event.reply("SoundCloud에서 노래를 찾을 수 없습니다. 검색된 쿼리: **" + soundCloudQuery + "**").setEphemeral(true).queue();
                }
            }

            @Override
            public void noMatches() {
                // Spotify 결과 확인
                String spotifyDetails = track == null
                        ? "Spotify에서 곡을 찾을 수 없습니다."
                        : "Spotify에서 검색된 곡: **" + track.getName() + "** by **" + track.getArtists()[0].getName() + "**";

                // SoundCloud 결과 확인
                String soundCloudMessage = "SoundCloud 검색 쿼리: **" + soundCloudQuery + "**";

                // 사용자 피드백 제공
                event.reply(
                        "노래를 찾을 수 없습니다.\n\n" +
                                "🔎 Spotify 상태: " + spotifyDetails + "\n" +
                                "🔎 SoundCloud 상태: " + soundCloudMessage
                ).setEphemeral(true).queue();
            }

            @Override
            public void loadFailed(FriendlyException e) {
                event.reply("🚨 로딩 오류 발생: " + e.getMessage()).setEphemeral(true).queue();
                e.printStackTrace();  // 디버깅 로그 추가
            }
        });
    }
}