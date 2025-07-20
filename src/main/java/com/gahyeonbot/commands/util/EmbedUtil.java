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

/**
 * Discord 임베드 메시지를 생성하는 유틸리티 클래스.
 * 다양한 상황에 맞는 임베드 메시지를 생성하는 정적 메서드들을 제공합니다.
 * 
 * @author GahyeonBot Team
 * @version 1.0
 */
public class EmbedUtil {

    /**
     * 현재 재생 중인 음악에 대한 임베드를 생성합니다.
     * 
     * @param event 슬래시 명령어 상호작용 이벤트
     * @param track 오디오 트랙
     * @param albumCoverUrl 앨범 커버 URL
     * @param streamUrl 스트리밍 URL
     * @return 재생 중 임베드
     */
    public static EmbedBuilder createNowPlayingEmbed(SlashCommandInteractionEvent event, AudioTrack track,String albumCoverUrl,String streamUrl) {
        EmbedBuilder embed = new EmbedBuilder()

                .setTitle("🎵 재생 시작!")
                .setDescription("**" + track.getInfo().title + "**")
                .addField("아티스트", track.getInfo().author, true)
                .addField("상태", "재생 중", false)
                .addField("스트리밍 출처", "[링크](" + streamUrl + ")", false) // 스트리밍 URL 추가
                .setFooter("요청자: " + event.getUser().getName(), event.getUser().getAvatarUrl())
                .setColor(Color.GREEN);
        setAlbumCover(embed, albumCoverUrl); // 앨범 커버 추가
        return embed;
    }

    /**
     * 대기열에 추가된 음악에 대한 임베드를 생성합니다.
     * 
     * @param track 오디오 트랙
     * @param requester 요청한 사용자
     * @return 대기열 추가 임베드
     */
    public static EmbedBuilder createQueueAddedEmbed(AudioTrack track, User requester) {
        EmbedBuilder embed = new EmbedBuilder();
        embed.setTitle("🎵 대기열에 추가됨")
                .setDescription("**" + track.getInfo().title + "**")
                .addField("아티스트", track.getInfo().author, true)
                .setFooter("요청자: " + requester.getName(), requester.getEffectiveAvatarUrl())
                .setColor(Color.YELLOW);
        return embed;
    }

    /**
     * 에러 메시지 임베드를 생성합니다.
     * 
     * @param errorMessage 에러 메시지
     * @return 에러 임베드
     */
    public static EmbedBuilder createErrorEmbed(String errorMessage) {
        EmbedBuilder embed = new EmbedBuilder();
        embed.setTitle("🚨 오류 발생")
                .setDescription(errorMessage)
                .setColor(Color.RED);
        return embed;
    }

    /**
     * 일반 메시지 임베드를 생성합니다.
     * 
     * @param errorMessage 메시지 내용
     * @return 일반 임베드
     */
    public static EmbedBuilder nomal(String errorMessage) {
        EmbedBuilder embed = new EmbedBuilder();
        embed.setTitle("")
               .setDescription(errorMessage)
               .setColor(Color.YELLOW);
        return embed;
    }

    /**
     * 정보 메시지 임베드를 생성합니다.
     * 
     * @param message 정보 메시지
     * @return 정보 임베드
     */
    public static EmbedBuilder createInfoEmbed(String message) {
        EmbedBuilder embed = new EmbedBuilder()
                .setTitle("ℹ️ 정보")
                .setDescription(message)
                .setColor(Color.BLUE);
        return embed;
    }
    
    /**
     * 명령어 목록 임베드를 생성합니다.
     * 
     * @param commands 명령어 목록
     * @param event 슬래시 명령어 상호작용 이벤트
     * @return 명령어 목록 임베드
     */
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
    
    /**
     * 음악 정지 임베드를 생성합니다.
     * 
     * @param event 슬래시 명령어 상호작용 이벤트
     * @return 음악 정지 임베드
     */
    public static EmbedBuilder createMusicStopEmbed(SlashCommandInteractionEvent event) {
        EmbedBuilder embed = new EmbedBuilder()
                .setTitle("🛑 재생 종료")
                .setDescription("음악 재생이 종료되었습니다.")
                .setColor(Color.RED)
                .setFooter("요청자: " + event.getUser().getName(), event.getUser().getAvatarUrl());
        return embed;
    }
    
    /**
     * 음악 일시정지 임베드를 생성합니다.
     * 
     * @param event 슬래시 명령어 상호작용 이벤트
     * @return 음악 일시정지 임베드
     */
    public static EmbedBuilder createPauseEmbed(SlashCommandInteractionEvent event) {
        return new EmbedBuilder()
                .setTitle("⏸️ 음악 일시정지")
                .setDescription("음악이 일시정지되었습니다.")
                .setColor(Color.YELLOW)
                .setFooter("요청자: " + event.getUser().getName(), event.getUser().getAvatarUrl());
    }
    
    /**
     * 음악 대기열 임베드를 생성합니다.
     * 
     * @param tracks 오디오 트랙 목록
     * @return 대기열 임베드
     */
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

    /**
     * 밀리초를 MM:SS 형식으로 변환합니다.
     * 
     * @param durationMillis 밀리초
     * @return MM:SS 형식의 문자열
     */
    private static String formatDuration(long durationMillis) {
        long minutes = (durationMillis / 1000) / 60;
        long seconds = (durationMillis / 1000) % 60;
        return String.format("%02d:%02d", minutes, seconds);
    }
    
    /**
     * 음악 재생 재개 임베드를 생성합니다.
     * 
     * @param event 슬래시 명령어 상호작용 이벤트
     * @return 음악 재생 재개 임베드
     */
    public static EmbedBuilder createResumeEmbed(SlashCommandInteractionEvent event) {
        return new EmbedBuilder()
                .setTitle("▶️ 음악 재생")
                .setDescription("음악 재생이 다시 시작되었습니다.")
                .setColor(Color.GREEN)
                .setFooter("요청자: " + event.getUser().getName(), event.getUser().getAvatarUrl());
    }
    
    /**
     * 트랙 스킵 임베드를 생성합니다.
     * 
     * @param event 슬래시 명령어 상호작용 이벤트
     * @param trackTitle 스킵된 트랙 제목
     * @return 트랙 스킵 임베드
     */
    public static EmbedBuilder createSkipEmbed(SlashCommandInteractionEvent event, String trackTitle) {
        return new EmbedBuilder()
                .setTitle("⏭️ 트랙 스킵")
                .setDescription("현재 트랙을 건너뛰었습니다: **" + trackTitle + "**")
                .setColor(Color.ORANGE)
                .setFooter("요청자: " + event.getUser().getName(), event.getUser().getAvatarUrl());
    }
    
    /**
     * 봇 제거 완료 임베드를 생성합니다.
     * 
     * @param removedBots 제거된 봇 목록
     * @return 봇 제거 완료 임베드
     */
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

    /**
     * 예약 취소 성공 임베드를 생성합니다.
     * 
     * @param reservationId 예약 ID
     * @return 예약 취소 성공 임베드
     */
    public static EmbedBuilder createReservationCancelledEmbed(int reservationId) {
        return new EmbedBuilder()
                .setTitle("✅ 예약 취소 완료")
                .setDescription("예약 ID **" + reservationId + "**이(가) 성공적으로 취소되었습니다.")
                .setColor(Color.GREEN);
    }
    
    /**
     * 예약 성공 임베드를 생성합니다.
     * 
     * @param reservationId 예약 ID
     * @param nickname 사용자 닉네임
     * @param minutes 예약 시간(분)
     * @return 예약 성공 임베드
     */
    public static EmbedBuilder createReservationEmbed(long reservationId, String nickname, int minutes) {
        return new EmbedBuilder()
                .setTitle("📅 예약 완료")
                .setDescription("**" + nickname + "**님의 퇴장이 **" + minutes + "분** 후로 예약되었습니다.")
                .addField("예약 ID", String.valueOf(reservationId), true)
                .setColor(Color.BLUE);
    }
    
    /**
     * 예약 목록 임베드를 생성합니다.
     * 
     * @param reservations 예약 목록
     * @return 예약 목록 임베드
     */
    public static EmbedBuilder createReservationListEmbed(List<Reservation> reservations) {
        EmbedBuilder embed = new EmbedBuilder();
        embed.setTitle("📋 예약된 작업 목록")
                .setColor(Color.BLUE);

        for (Reservation reservation : reservations) {
            embed.addField("ID: " + reservation.getId(), reservation.getDescription(), false);
        }

        return embed;
    }
    
    /**
     * 임베드에 앨범 커버를 설정합니다.
     * 
     * @param embed 임베드 빌더
     * @param albumCoverUrl 앨범 커버 URL
     */
    private static void setAlbumCover(EmbedBuilder embed, String albumCoverUrl) {
        if (albumCoverUrl != null && !albumCoverUrl.isBlank()) {
            embed.setThumbnail(albumCoverUrl); // Thumbnail로 앨범 커버 추가
        } else {
            //embed.setThumbnail("https://example.com/default-image.jpg"); // 기본 이미지 (옵션)
        }
    }
}
