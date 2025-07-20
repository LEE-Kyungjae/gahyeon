package com.gahyeonbot.listeners;

import net.dv8tion.jda.api.events.guild.member.GuildMemberJoinEvent;
import net.dv8tion.jda.api.hooks.ListenerAdapter;
import org.jetbrains.annotations.NotNull;

import java.util.Objects;

/**
 * Discord 서버 가입 이벤트를 처리하는 리스너 클래스.
 * 새로운 멤버가 서버에 가입할 때의 이벤트를 처리합니다.
 * 
 * @author GahyeonBot Team
 * @version 1.0
 */
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
