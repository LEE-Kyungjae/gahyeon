package com.gahyeonbot.commands.util;

import com.gahyeonbot.models.Reservation;
import com.sedmelluq.discord.lavaplayer.track.AudioTrack;
import net.dv8tion.jda.api.EmbedBuilder;
import net.dv8tion.jda.api.entities.Member;
import net.dv8tion.jda.api.entities.User;
import net.dv8tion.jda.api.events.interaction.command.SlashCommandInteractionEvent;
import net.dv8tion.jda.api.interactions.DiscordLocale;

import java.awt.*;
import java.time.Instant;
import java.time.format.DateTimeFormatter;
import java.util.List;
import java.util.StringJoiner;

public class EmbedUtil {

    private static final Color BRAND_PRIMARY = new Color(0x06B6D4);
    private static final Color BRAND_SUCCESS = new Color(0x06B6A0);
    private static final Color BRAND_WARNING = new Color(0xF59E0B);
    private static final Color BRAND_ERROR   = new Color(0xEF4444);

    private static final String BOT_NAME = "가현봇";
    private static final DateTimeFormatter RESERVATION_TIME_FORMATTER = DateTimeFormatter.ofPattern("MM-dd HH:mm");

    private static String botAvatarUrl;

    public static void init(String avatarUrl) {
        botAvatarUrl = avatarUrl;
    }

    private static EmbedBuilder base(Color color) {
        EmbedBuilder eb = new EmbedBuilder()
                .setColor(color)
                .setTimestamp(Instant.now());
        if (botAvatarUrl != null) {
            eb.setAuthor(BOT_NAME, null, botAvatarUrl);
        }
        return eb;
    }

    public static EmbedBuilder createNowPlayingEmbed(SlashCommandInteractionEvent event, AudioTrack track, String albumCoverUrl, String streamUrl) {
        EmbedBuilder embed = base(BRAND_PRIMARY)
                .setTitle(track.getInfo().title, streamUrl)
                .setDescription("재생 시작")
                .addField("아티스트", track.getInfo().author, true)
                .addField("상태", "재생 중", true)
                .setFooter(event.getUser().getName(), event.getUser().getAvatarUrl());
        setAlbumCover(embed, albumCoverUrl);
        return embed;
    }

    public static EmbedBuilder createQueueAddedEmbed(AudioTrack track, User requester) {
        return base(BRAND_PRIMARY)
                .setTitle("대기열에 추가됨")
                .setDescription("**" + track.getInfo().title + "**")
                .addField("아티스트", track.getInfo().author, true)
                .setFooter(requester.getName(), requester.getEffectiveAvatarUrl());
    }

    public static EmbedBuilder createErrorEmbed(String errorMessage) {
        return base(BRAND_ERROR)
                .setTitle("오류 발생")
                .setDescription(errorMessage);
    }

    public static EmbedBuilder createNormalEmbed(String message) {
        return base(BRAND_PRIMARY)
                .setDescription(message);
    }

    /** @deprecated Use {@link #createNormalEmbed(String)} instead. */
    @Deprecated
    public static EmbedBuilder nomal(String message) {
        return createNormalEmbed(message);
    }

    public static EmbedBuilder createInfoEmbed(String message) {
        return base(BRAND_PRIMARY)
                .setTitle("정보")
                .setDescription(message);
    }

    public static EmbedBuilder createCommandListEmbed(List<ICommand> commands, SlashCommandInteractionEvent event) {
        EmbedBuilder embed = base(BRAND_PRIMARY)
                .setTitle("명령어 목록")
                .setDescription("아래는 봇이 지원하는 명령어 목록입니다.");

        DiscordLocale userLocale = event.getUserLocale();

        for (ICommand command : commands) {
            String detailedDescription = command.getDetailedDescription();
            String description = command.getDescription();
            String commandName = command.getName();

            if (userLocale != null) {
                commandName = command.getNameLocalizations().getOrDefault(userLocale, commandName);
            }

            String fieldValue = description;
            if (detailedDescription != null && !detailedDescription.isEmpty()) {
                fieldValue += "\n`" + detailedDescription + "`";
            }

            embed.addField("/" + commandName, fieldValue, false);
        }

        return embed;
    }

    public static EmbedBuilder createMusicStopEmbed(SlashCommandInteractionEvent event) {
        return base(BRAND_WARNING)
                .setTitle("재생 종료")
                .setDescription("음악 재생이 종료되었습니다.")
                .setFooter(event.getUser().getName(), event.getUser().getAvatarUrl());
    }

    public static EmbedBuilder createPauseEmbed(SlashCommandInteractionEvent event) {
        return base(BRAND_PRIMARY)
                .setTitle("음악 일시정지")
                .setDescription("음악이 일시정지되었습니다.")
                .setFooter(event.getUser().getName(), event.getUser().getAvatarUrl());
    }

    public static EmbedBuilder createQueueEmbed(List<AudioTrack> tracks) {
        EmbedBuilder embed = base(BRAND_PRIMARY)
                .setTitle("현재 대기열");

        StringJoiner queueMessage = new StringJoiner("\n");
        for (int i = 0; i < tracks.size(); i++) {
            AudioTrack track = tracks.get(i);
            queueMessage.add("`" + (i + 1) + ".` " + track.getInfo().title + " \u2014 " + formatDuration(track.getDuration()));
        }

        embed.setDescription(queueMessage.toString());
        return embed;
    }

    private static String formatDuration(long durationMillis) {
        long minutes = (durationMillis / 1000) / 60;
        long seconds = (durationMillis / 1000) % 60;
        return String.format("%02d:%02d", minutes, seconds);
    }

    public static EmbedBuilder createResumeEmbed(SlashCommandInteractionEvent event) {
        return base(BRAND_PRIMARY)
                .setTitle("음악 재생")
                .setDescription("음악 재생이 다시 시작되었습니다.")
                .setFooter(event.getUser().getName(), event.getUser().getAvatarUrl());
    }

    public static EmbedBuilder createSkipEmbed(SlashCommandInteractionEvent event, String trackTitle) {
        return base(BRAND_PRIMARY)
                .setTitle("트랙 스킵")
                .setDescription("현재 트랙을 건너뛰었습니다: **" + trackTitle + "**")
                .setFooter(event.getUser().getName(), event.getUser().getAvatarUrl());
    }

    public static EmbedBuilder createBotOutEmbed(List<Member> removedBots) {
        EmbedBuilder embed = base(BRAND_WARNING)
                .setTitle("봇 제거 완료");

        StringBuilder description = new StringBuilder("다음 봇이 채널에서 제거되었습니다:\n");
        for (Member bot : removedBots) {
            description.append("- ").append(bot.getEffectiveName()).append("\n");
        }

        embed.setDescription(description.toString());
        return embed;
    }

    public static EmbedBuilder createReservationCancelledEmbed(int reservationId) {
        return base(BRAND_SUCCESS)
                .setTitle("예약 취소 완료")
                .setDescription("예약 ID **" + reservationId + "**이(가) 성공적으로 취소되었습니다.");
    }

    public static EmbedBuilder createReservationEmbed(long reservationId, String nickname, int minutes) {
        String executeAt = java.time.LocalDateTime.now().plusMinutes(minutes).format(RESERVATION_TIME_FORMATTER);
        return base(BRAND_PRIMARY)
                .setTitle("예약 완료")
                .setDescription("**" + nickname + "**님의 퇴장이 **" + minutes + "분** 후로 예약되었습니다.")
                .addField("예약 ID", String.valueOf(reservationId), true)
                .addField("실행 예정", executeAt, true);
    }

    public static EmbedBuilder createReservationListEmbed(List<Reservation> reservations) {
        EmbedBuilder embed = base(BRAND_PRIMARY)
                .setTitle("예약된 작업 목록");

        for (Reservation reservation : reservations) {
            String value = String.format(
                    "%s\n대상: %s\n남은 시간: %d분\n실행 예정: %s",
                    reservation.getDescription(),
                    reservation.getMemberName(),
                    reservation.getRemainingMinutes(),
                    reservation.getExecuteAt().format(RESERVATION_TIME_FORMATTER)
            );
            embed.addField("ID: " + reservation.getId(), value, false);
        }

        return embed;
    }

    private static void setAlbumCover(EmbedBuilder embed, String albumCoverUrl) {
        if (albumCoverUrl != null && !albumCoverUrl.isBlank()) {
            embed.setThumbnail(albumCoverUrl);
        }
    }
}
