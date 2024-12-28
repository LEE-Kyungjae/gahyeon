package com.gahyeonbot.commands.util;

import net.dv8tion.jda.api.EmbedBuilder;
import net.dv8tion.jda.api.entities.channel.middleman.MessageChannel;
import net.dv8tion.jda.api.events.interaction.command.SlashCommandInteractionEvent;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

public class ResponseUtil {
    private static final Logger logger = LoggerFactory.getLogger(ResponseUtil.class);
    public static void replyError(SlashCommandInteractionEvent event, String errorMessage) {
        logger.error("replyError: {}", errorMessage);
        EmbedBuilder embed = EmbedUtil.createErrorEmbed(errorMessage);
        event.replyEmbeds(embed.build()).setEphemeral(true).queue();
    }

    public static void replySuccess(SlashCommandInteractionEvent event, String successMessage) {
        logger.info("replySuccess: {}", successMessage);
        EmbedBuilder embed = EmbedUtil.nomal(successMessage);
        event.replyEmbeds(embed.build()).queue();
    }

    public static void replyEmbed(SlashCommandInteractionEvent event, EmbedBuilder embed) {
        logger.info("replyEmbed");
        event.replyEmbeds(embed.build()).queue();
    }

    public static void replyEphemeralEmbed(SlashCommandInteractionEvent event, EmbedBuilder embed) {
        logger.info("replyEphemeralEmbed");
        event.replyEmbeds(embed.build()).setEphemeral(true).queue();
    }

    public static void sendMessageToChannel(SlashCommandInteractionEvent event, String message) {
        logger.info("sendMessageToChannel: {}", message);
        MessageChannel channel = event.getChannel();
        channel.sendMessage(message).queue();
    }
}
