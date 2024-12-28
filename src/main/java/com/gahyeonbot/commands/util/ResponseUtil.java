package com.gahyeonbot.commands.util;

import net.dv8tion.jda.api.EmbedBuilder;
import net.dv8tion.jda.api.entities.channel.middleman.MessageChannel;
import net.dv8tion.jda.api.events.interaction.command.SlashCommandInteractionEvent;

public class ResponseUtil {

    public static void replyError(SlashCommandInteractionEvent event, String errorMessage) {
        EmbedBuilder embed = EmbedUtil.createErrorEmbed(errorMessage);
        event.replyEmbeds(embed.build()).setEphemeral(true).queue();
    }

    public static void replySuccess(SlashCommandInteractionEvent event, String successMessage) {
        EmbedBuilder embed = EmbedUtil.nomal(successMessage);
        event.replyEmbeds(embed.build()).queue();
    }

    public static void replyEmbed(SlashCommandInteractionEvent event, EmbedBuilder embed) {
        event.replyEmbeds(embed.build()).queue();
    }

    public static void replyEphemeralEmbed(SlashCommandInteractionEvent event, EmbedBuilder embed) {
        event.replyEmbeds(embed.build()).setEphemeral(true).queue();
    }

    public static void sendMessageToChannel(SlashCommandInteractionEvent event, String message) {
        MessageChannel channel = event.getChannel();
        channel.sendMessage(message).queue();
    }
}
