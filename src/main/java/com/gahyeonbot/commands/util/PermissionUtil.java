package com.gahyeonbot.commands.util;

import net.dv8tion.jda.api.entities.Member;
import net.dv8tion.jda.api.events.interaction.command.SlashCommandInteractionEvent;

/**
 * Discord 권한 관련 유틸리티 클래스.
 * 사용자의 권한을 확인하는 정적 메서드들을 제공합니다.
 * 
 * @author GahyeonBot Team
 * @version 1.0
 */
public class PermissionUtil {
    
    /**
     * 사용자가 Admin 역할을 가지고 있는지 확인합니다.
     * 
     * @param event 슬래시 명령어 상호작용 이벤트
     * @return Admin 역할 보유 시 true, 그렇지 않으면 false
     */
    public static boolean isAdmin(SlashCommandInteractionEvent event) {
        Member member = event.getMember();
        if (member == null) return false;
        return member.getRoles().stream().anyMatch(role -> role.getName().equalsIgnoreCase("Admin"));
    }

    /**
     * 사용자가 Moderator 역할을 가지고 있는지 확인합니다.
     * 
     * @param event 슬래시 명령어 상호작용 이벤트
     * @return Moderator 역할 보유 시 true, 그렇지 않으면 false
     */
    public static boolean isModerator(SlashCommandInteractionEvent event) {
        Member member = event.getMember();
        if (member == null) return false;
        return member.getRoles().stream().anyMatch(role -> role.getName().equalsIgnoreCase("Moderator"));
    }

    /**
     * 사용자가 보이스 채널에 있는지 확인합니다.
     * 
     * @param event 슬래시 명령어 상호작용 이벤트
     * @return 보이스 채널에 있을 때 true, 그렇지 않으면 false
     */
    public static boolean isInVoiceChannel(SlashCommandInteractionEvent event) {
        Member member = event.getMember();
        return member != null && member.getVoiceState() != null && member.getVoiceState().getChannel() != null;
    }
    
    /**
     * 사용자가 다른 사용자를 보이스 채널에서 이동시킬 권한을 가지고 있는지 확인합니다.
     * 
     * @param event 슬래시 명령어 상호작용 이벤트
     * @return VOICE_MOVE_OTHERS 권한 보유 시 true, 그렇지 않으면 false
     */
    public static boolean hasVoiceKickPermission(SlashCommandInteractionEvent event) {
        Member member = event.getMember();
        if (member == null) return false;
        return member.hasPermission(net.dv8tion.jda.api.Permission.VOICE_MOVE_OTHERS);
    }
}
