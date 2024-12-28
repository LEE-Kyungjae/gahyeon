package com.gahyeonbot.service;

import net.dv8tion.jda.api.entities.Member;
import net.dv8tion.jda.api.entities.channel.middleman.AudioChannel;
import net.dv8tion.jda.api.events.interaction.command.SlashCommandInteractionEvent;

import java.util.ArrayList;
import java.util.List;
/*
봇 상태 관리 및 유저와의 상호작용 지원.
봇 연결 제어, 명령어 실행 처리.
*/
public class BotManagerService {

    public List<Member> removeBotsFromChannel(SlashCommandInteractionEvent event, AudioChannel channel) {
        List<Member> botsToRemove = new ArrayList<>();
        for (Member member : channel.getMembers()) {
            if (member.getUser().isBot()) {
                botsToRemove.add(member);
                event.getGuild().kickVoiceMember(member).queue(
                        success -> event.getChannel().sendMessage(member.getEffectiveName() + " 봇을 내보냈습니다.").queue(),
                        error -> event.getChannel().sendMessage("오류: " + member.getEffectiveName() + " 봇을 내보낼 수 없습니다.").queue()
                );
            }
        }
        return botsToRemove;
    }
}
