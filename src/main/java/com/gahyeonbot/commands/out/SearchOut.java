package com.gahyeonbot.commands;

import com.gahyeonbot.commands.base.ICommand;
import com.gahyeonbot.manager.scheduler.LeaveSchedulerManager;
import com.gahyeonbot.models.Reservation;
import net.dv8tion.jda.api.events.interaction.command.SlashCommandInteractionEvent;
import net.dv8tion.jda.api.interactions.commands.build.OptionData;

import java.util.List;

public class SearchOut implements ICommand {

    private final LeaveSchedulerManager schedulerManager;

    public SearchOut(LeaveSchedulerManager schedulerManager) {
        this.schedulerManager = schedulerManager;
    }

    @Override
    public String getName() {
        return "searchout";
    }

    @Override
    public String getDescription() {
        return "예약된 작업 목록을 조회합니다.";
    }

    @Override
    public String getDetailedDescription() {
        return "사용자의 예약된 나가기 작업 목록을 확인합니다.";
    }

    @Override
    public List<OptionData> getOptions() {
        return List.of();
    }

    @Override
    public void execute(SlashCommandInteractionEvent event) {
        var member = event.getMember();

        if (member == null) {
            event.reply("사용자 정보를 찾을 수 없습니다.").setEphemeral(true).queue();
            return;
        }

        List<Reservation> reservations = schedulerManager.getReservations(member.getIdLong());

        if (reservations.isEmpty()) {
            event.reply("예약된 작업이 없습니다.").setEphemeral(true).queue();
            return;
        }

        StringBuilder message = new StringBuilder("**예약된 작업 목록:**\n");
        for (Reservation reservation : reservations) {
            message.append("ID: ").append(reservation.getId())
                    .append(" - ").append(reservation.getDescription())
                    .append("\n");
        }

        event.reply(message.toString()).queue();
    }
}
