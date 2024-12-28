package com.gahyeonbot.commands.out;

import com.gahyeonbot.commands.util.*;
import com.gahyeonbot.manager.scheduler.LeaveSchedulerManager;
import com.gahyeonbot.models.Reservation;
import net.dv8tion.jda.api.events.interaction.command.SlashCommandInteractionEvent;
import net.dv8tion.jda.api.interactions.commands.build.OptionData;

import java.util.List;

public class SearchOut extends AbstractCommand {

    private final LeaveSchedulerManager schedulerManager;

    public SearchOut(LeaveSchedulerManager schedulerManager) {
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
    public List<OptionData> getOptions() {
        return List.of();
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
}
