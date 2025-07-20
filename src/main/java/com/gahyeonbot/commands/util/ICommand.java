package com.gahyeonbot.commands.util;

import net.dv8tion.jda.api.events.interaction.command.SlashCommandInteractionEvent;

import net.dv8tion.jda.api.interactions.commands.build.OptionData;

import java.util.List;

/**
 * Discord 슬래시 명령어를 정의하는 인터페이스.
 * 모든 명령어 클래스는 이 인터페이스를 구현해야 합니다.
 * 
 * @author GahyeonBot Team
 * @version 1.0
 */
public interface ICommand {
    
    /**
     * 명령어의 이름을 반환합니다.
     * 
     * @return 명령어 이름
     */
    String getName();
    
    /**
     * 명령어의 간단한 설명을 반환합니다.
     * 
     * @return 명령어 설명
     */
    String getDescription();
    
    /**
     * 명령어의 상세한 설명을 반환합니다.
     * 
     * @return 명령어 상세 설명
     */
    String getDetailedDescription();
    
    /**
     * 명령어의 옵션 목록을 반환합니다.
     * 
     * @return 명령어 옵션 목록
     */
    List<OptionData> getOptions();

    /**
     * 명령어를 실행합니다.
     * 
     * @param event 슬래시 명령어 상호작용 이벤트
     */
    void execute(SlashCommandInteractionEvent event);
}
