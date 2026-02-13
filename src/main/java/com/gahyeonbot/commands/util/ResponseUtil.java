package com.gahyeonbot.commands.util;

import net.dv8tion.jda.api.EmbedBuilder;
import net.dv8tion.jda.api.entities.channel.middleman.MessageChannel;
import net.dv8tion.jda.api.events.interaction.command.SlashCommandInteractionEvent;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/**
 * Discord 명령어 응답을 처리하는 유틸리티 클래스.
 * 에러, 성공, 임베드 메시지 등을 일관된 방식으로 응답합니다.
 * 
 * @author GahyeonBot Team
 * @version 1.0
 */
public class ResponseUtil {
    private static final Logger logger = LoggerFactory.getLogger(ResponseUtil.class);
    
    /**
     * 에러 메시지를 임시 응답으로 전송합니다.
     * 
     * @param event 슬래시 명령어 상호작용 이벤트
     * @param errorMessage 에러 메시지
     */
    public static void replyError(SlashCommandInteractionEvent event, String errorMessage) {
        logger.error("replyError: {}", errorMessage);
        EmbedBuilder embed = EmbedUtil.createErrorEmbed(errorMessage);
        sendEmbed(event, embed, true);
    }

    /**
     * 성공 메시지를 일반 응답으로 전송합니다.
     * 
     * @param event 슬래시 명령어 상호작용 이벤트
     * @param successMessage 성공 메시지
     */
    public static void replySuccess(SlashCommandInteractionEvent event, String successMessage) {
        logger.info("replySuccess: {}", successMessage);
        EmbedBuilder embed = EmbedUtil.createNormalEmbed(successMessage);
        sendEmbed(event, embed, false);
    }

    /**
     * 임베드 메시지를 일반 응답으로 전송합니다.
     * 
     * @param event 슬래시 명령어 상호작용 이벤트
     * @param embed 전송할 임베드
     */
    public static void replyEmbed(SlashCommandInteractionEvent event, EmbedBuilder embed) {
        logger.info("replyEmbed");
        sendEmbed(event, embed, false);
    }

    /**
     * 임베드 메시지를 임시 응답으로 전송합니다.
     * 
     * @param event 슬래시 명령어 상호작용 이벤트
     * @param embed 전송할 임베드
     */
    public static void replyEphemeralEmbed(SlashCommandInteractionEvent event, EmbedBuilder embed) {
        logger.info("replyEphemeralEmbed");
        sendEmbed(event, embed, true);
    }

    /**
     * 채널에 일반 텍스트 메시지를 전송합니다.
     * 
     * @param event 슬래시 명령어 상호작용 이벤트
     * @param message 전송할 메시지
     */
    public static void sendMessageToChannel(SlashCommandInteractionEvent event, String message) {
        logger.info("sendMessageToChannel: {}", message);
        MessageChannel channel = event.getChannel();
        channel.sendMessage(message).queue();
    }

    private static void sendEmbed(SlashCommandInteractionEvent event, EmbedBuilder embed, boolean ephemeral) {
        if (event.isAcknowledged()) {
            event.getHook().sendMessageEmbeds(embed.build()).setEphemeral(ephemeral).queue();
        } else {
            event.replyEmbeds(embed.build()).setEphemeral(ephemeral).queue();
        }
    }
}
