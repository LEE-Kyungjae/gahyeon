package com.gahyeonbot.commands.util;

import com.gahyeonbot.models.Reservation;
import com.sedmelluq.discord.lavaplayer.track.AudioTrack;
import net.dv8tion.jda.api.EmbedBuilder;
import net.dv8tion.jda.api.entities.Member;
import net.dv8tion.jda.api.entities.User;
import net.dv8tion.jda.api.events.interaction.command.SlashCommandInteractionEvent;

import java.awt.*;
import java.util.List;
import java.util.StringJoiner;

public class EmbedUtil {

    //Add 임베드
    public static EmbedBuilder createNowPlayingEmbed(SlashCommandInteractionEvent event, AudioTrack track) {
        return new EmbedBuilder()
                .setTitle("🎵 재생 시작!")
                .setDescription("**" + track.getInfo().title + "**")
                .addField("아티스트", track.getInfo().author, true)
                .addField("상태", "재생 중", false)
                .setFooter("요청자: " + event.getUser().getName(), event.getUser().getAvatarUrl())
                .setColor(Color.GREEN);
    }

    public static EmbedBuilder createQueueAddedEmbed(AudioTrack track, User requester) {
        EmbedBuilder embed = new EmbedBuilder();
        embed.setTitle("🎵 대기열에 추가됨")
                .setDescription("**" + track.getInfo().title + "**")
                .addField("아티스트", track.getInfo().author, true)
                .setFooter("요청자: " + requester.getName(), requester.getEffectiveAvatarUrl())
                .setColor(Color.YELLOW);
        return embed;
    }

    public static EmbedBuilder createErrorEmbed(String errorMessage) {
        EmbedBuilder embed = new EmbedBuilder();
        embed.setTitle("🚨 오류 발생")
                .setDescription(errorMessage)
                .setColor(Color.RED);
        return embed;
    }

    public static EmbedBuilder nomal(String errorMessage) {
        EmbedBuilder embed = new EmbedBuilder();
        embed.setTitle("")
               .setDescription(errorMessage)
               .setColor(Color.YELLOW);
        return embed;
    }

    public static EmbedBuilder createInfoEmbed(String message) {
        return new EmbedBuilder()
                .setTitle("ℹ️ 정보")
                .setDescription(message)
                .setColor(Color.BLUE);
    }
    public static EmbedBuilder createCommandListEmbed(List<ICommand> commands, SlashCommandInteractionEvent event) {
        EmbedBuilder embed = new EmbedBuilder();
        embed.setTitle("📜 명령어 목록")
                .setColor(Color.CYAN)
                .setDescription("아래는 봇이 지원하는 명령어 목록입니다.")
                .setFooter("가현봇 | 도움말", event.getJDA().getSelfUser().getEffectiveAvatarUrl());

        for (ICommand command : commands) {
            String detailedDescription = command.getDetailedDescription();
            String description = command.getDescription();

            String fieldValue = description;
            if (detailedDescription != null && !detailedDescription.isEmpty()) {
                fieldValue += "\n**사용법:** " + detailedDescription;
            }

            embed.addField("/" + command.getName(), fieldValue, false);
        }

        return embed;
    }
    public static EmbedBuilder createMusicStopEmbed(SlashCommandInteractionEvent event) {
        return new EmbedBuilder()
                .setTitle("🛑 재생 종료")
                .setDescription("음악 재생이 종료되었습니다.")
                .setColor(Color.RED)
                .setFooter("요청자: " + event.getUser().getName(), event.getUser().getAvatarUrl());
    }
    public static EmbedBuilder createPauseEmbed(SlashCommandInteractionEvent event) {
        return new EmbedBuilder()
                .setTitle("⏸️ 음악 일시정지")
                .setDescription("음악이 일시정지되었습니다.")
                .setColor(Color.YELLOW)
                .setFooter("요청자: " + event.getUser().getName(), event.getUser().getAvatarUrl());
    }
    public static EmbedBuilder createQueueEmbed(List<AudioTrack> tracks) {
        EmbedBuilder embed = new EmbedBuilder();
        embed.setTitle("🎶 현재 대기열")
                .setColor(Color.BLUE);

        StringJoiner queueMessage = new StringJoiner("\n");
        for (int i = 0; i < tracks.size(); i++) {
            AudioTrack track = tracks.get(i);
            queueMessage.add((i + 1) + ". " + track.getInfo().title + " - " + formatDuration(track.getDuration()));
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
        return new EmbedBuilder()
                .setTitle("▶️ 음악 재생")
                .setDescription("음악 재생이 다시 시작되었습니다.")
                .setColor(Color.GREEN)
                .setFooter("요청자: " + event.getUser().getName(), event.getUser().getAvatarUrl());
    }
    public static EmbedBuilder createSkipEmbed(SlashCommandInteractionEvent event, String trackTitle) {
        return new EmbedBuilder()
                .setTitle("⏭️ 트랙 스킵")
                .setDescription("현재 트랙을 건너뛰었습니다: **" + trackTitle + "**")
                .setColor(Color.ORANGE)
                .setFooter("요청자: " + event.getUser().getName(), event.getUser().getAvatarUrl());
    }
    public static EmbedBuilder createBotOutEmbed(List<Member> removedBots) {
        EmbedBuilder embed = new EmbedBuilder();
        embed.setTitle("🤖 봇 제거 완료")
                .setColor(Color.RED);

        StringBuilder description = new StringBuilder("다음 봇이 채널에서 제거되었습니다:\n");
        for (Member bot : removedBots) {
            description.append("- ").append(bot.getEffectiveName()).append("\n");
        }

        embed.setDescription(description.toString());
        return embed;
    }

    public static EmbedBuilder createCancelSuccessEmbed(long reservationId) {
        return new EmbedBuilder()
                .setTitle("✅ 예약 취소 완료")
                .setDescription("예약 ID " + reservationId + "가 성공적으로 취소되었습니다.")
                .setColor(Color.GREEN);
    }
    public static EmbedBuilder createReservationEmbed(long reservationId, String nickname, int minutes) {
        return new EmbedBuilder()
                .setTitle("🕒 예약 생성 완료")
                .setDescription(nickname + "님의 나가기 예약이 생성되었습니다.")
                .addField("예약 ID", String.valueOf(reservationId), false)
                .addField("예정 시간", minutes + "분 후", false)
                .setColor(Color.BLUE);
    }
    public static EmbedBuilder createReservationListEmbed(List<Reservation> reservations) {
        EmbedBuilder embed = new EmbedBuilder();
        embed.setTitle("📋 예약된 작업 목록")
                .setColor(Color.BLUE);

        for (Reservation reservation : reservations) {
            embed.addField("ID: " + reservation.getId(), reservation.getDescription(), false);
        }

        return embed;
    }
}
