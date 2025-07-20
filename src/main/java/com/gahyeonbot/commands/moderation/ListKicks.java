package com.gahyeonbot.commands.moderation;

import com.gahyeonbot.commands.util.AbstractCommand;
import com.gahyeonbot.commands.util.ICommand;
import com.gahyeonbot.commands.util.Description;
import com.gahyeonbot.commands.util.ResponseUtil;
import com.gahyeonbot.commands.util.EmbedUtil;
import com.gahyeonbot.core.scheduler.LeaveSchedulerManager;
import com.gahyeonbot.models.Reservation;
import net.dv8tion.jda.api.events.interaction.command.SlashCommandInteractionEvent;
import net.dv8tion.jda.api.interactions.commands.OptionMapping;
import net.dv8tion.jda.api.interactions.commands.OptionType;
import net.dv8tion.jda.api.interactions.commands.build.OptionData;

import java.util.ArrayList;
import java.util.List;

/**
 * 예약된 추방 목록을 조회하는 명령어.
 * 관리자 권한이 필요하며, 현재 예약된 모든 추방을 확인할 수 있습니다.
 * 
 * @author GahyeonBot Team
 * @version 1.0
 */
public class ListKicks extends AbstractCommand implements ICommand {
    private final LeaveSchedulerManager schedulerManager;

    /**
     * ListKicks 생성자.
     * 
     * @param schedulerManager 스케줄러 매니저
     */
    public ListKicks(LeaveSchedulerManager schedulerManager) {
        this.schedulerManager = schedulerManager;
    }

    @Override
    public String getName() {
        return Description.SEARCHOUT_NAME;
    }

    @Override
    public String getDescription() {
        return Description.SEARCHOUT_DESC;
    }

    @Override
    public String getDetailedDescription() {
        return Description.SEARCHOUT_DETAIL;
    }

    @Override
    public void execute(SlashCommandInteractionEvent event) {
        logger.info("명령어 실행 시작: {}", getName());

        var member = event.getMember();

        if (member == null) {
            ResponseUtil.replyError(event, "사용자 정보를 찾을 수 없습니다.");
            return;
        }

        List<Reservation> reservations = schedulerManager.getReservations(member.getIdLong());

        if (reservations.isEmpty()) {
            ResponseUtil.replyError(event, "예약된 작업이 없습니다.");
        } else {
            var embed = EmbedUtil.createReservationListEmbed(reservations);
            ResponseUtil.replyEmbed(event, embed);
        }
    }

    @Override
    public List<OptionData> getOptions() {
        return new ArrayList<>();
    }
}
