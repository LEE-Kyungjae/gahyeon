package com.gahyeonbot.service;

import com.gahyeonbot.commands.util.ResponseUtil;
import net.dv8tion.jda.api.entities.Message;
import net.dv8tion.jda.api.entities.channel.middleman.MessageChannel;
import net.dv8tion.jda.api.events.interaction.command.SlashCommandInteractionEvent;

import java.util.List;
import java.util.stream.Collectors;

public class MessageCleanService {

    public void deleteUserMessages(MessageChannel channel, SlashCommandInteractionEvent event, int remaining) {
        if (remaining <= 0) {
            ResponseUtil.replySuccess(event, "본인 채팅 삭제가 완료되었습니다.");
            return;
        }

        channel.getHistory().retrievePast(Math.min(remaining, 100)).queue(messages -> {
            List<Message> userMessages = messages.stream()
                    .filter(msg -> msg.getAuthor().equals(event.getUser()))
                    .limit(remaining)
                    .collect(Collectors.toList());

            if (userMessages.isEmpty()) {
                ResponseUtil.replyError(event, "더 이상 삭제할 본인 메시지가 없습니다.");
                return;
            }

            channel.purgeMessages(userMessages);
            deleteUserMessages(channel, event, remaining - userMessages.size());
        }, throwable -> {
            ResponseUtil.replyError(event, "채팅 삭제 중 오류가 발생했습니다.");
        });
    }

    public void deleteMessages(MessageChannel channel, SlashCommandInteractionEvent event, int remaining) {
        if (remaining <= 0) {
            ResponseUtil.replySuccess(event, "채팅창을 청소했습니다.");
            return;
        }

        channel.getHistory().retrievePast(Math.min(remaining, 100)).queue(messages -> {
            if (messages.isEmpty()) {
                ResponseUtil.replyError(event, "더 이상 삭제할 메시지가 없습니다.");
                return;
            }

            channel.purgeMessages(messages);
            deleteMessages(channel, event, remaining - messages.size());
        }, throwable -> {
            ResponseUtil.replyError(event, "채팅 삭제 중 오류가 발생했습니다.");
        });
    }
}
