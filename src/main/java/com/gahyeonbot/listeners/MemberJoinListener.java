package com.gahyeonbot.listeners;

import net.dv8tion.jda.api.events.guild.member.GuildMemberJoinEvent;
import net.dv8tion.jda.api.hooks.ListenerAdapter;
import org.jetbrains.annotations.NotNull;

import java.util.Objects;

public class MemberJoinListener extends ListenerAdapter {
    @Override
    public void onGuildMemberJoin(@NotNull GuildMemberJoinEvent event) {
        String message = "Hi " + event.getUser().getAsMention();
        Objects.requireNonNull(event.getGuild().getDefaultChannel())
                .asTextChannel()
                .sendMessage(message)
                .queue();
    }
}
