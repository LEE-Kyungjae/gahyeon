package com.gahyeonbot.listeners;

import net.dv8tion.jda.api.events.message.MessageReceivedEvent;
import net.dv8tion.jda.api.hooks.ListenerAdapter;
import org.jetbrains.annotations.NotNull;

/**
 * Discord 메시지 이벤트를 처리하는 리스너 클래스.
 * 사용자가 보낸 메시지를 감지하고 처리합니다.
 * 
 * @author GahyeonBot Team
 * @version 1.0
 */
public class MessageListener extends ListenerAdapter {
    @Override
    public void onMessageReceived(@NotNull MessageReceivedEvent event) {
        if (event.getAuthor().isBot()) return;

        String message = event.getMessage().getContentRaw();
        if (message.contains("ping")) {
            event.getChannel().sendMessage("pong2").queue();
        }
    }
}
