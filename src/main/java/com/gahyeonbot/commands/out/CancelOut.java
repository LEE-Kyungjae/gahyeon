package com.gahyeonbot.commands.out;

import com.gahyeonbot.commands.util.Description;
import com.gahyeonbot.commands.util.ICommand;
import com.gahyeonbot.commands.util.ResponseUtil;
import com.gahyeonbot.commands.util.EmbedUtil;
import com.gahyeonbot.manager.scheduler.LeaveSchedulerManager;
import net.dv8tion.jda.api.events.interaction.command.SlashCommandInteractionEvent;
import net.dv8tion.jda.api.interactions.commands.OptionType;
import net.dv8tion.jda.api.interactions.commands.build.OptionData;

import java.util.List;

public class CancelOut implements ICommand {

    private final LeaveSchedulerManager schedulerManager;

    public CancelOut(LeaveSchedulerManager schedulerManager) {
        this.schedulerManager = schedulerManager;
    }

    @Override
    public String getName() {
        return Description.CANCLEOUT_NAME;
    }

    @Override
    public String getDescription() {
        return Description.CANCLEOUT_DESC;
    }

    @Override
    public String getDetailedDescription() {
        return Description.CANCLEOUT_DETAIL;
    }

    @Override
    public List<OptionData> getOptions() {
        return List.of(new OptionData(OptionType.INTEGER, "id", "취소할 예약 ID", true));
    }

    @Override
    public void execute(SlashCommandInteractionEvent event) {
        long reservationId = event.getOption("id").getAsLong();
        boolean success = schedulerManager.cancelReservation(reservationId);

        if (success) {
            var embed = EmbedUtil.createCancelSuccessEmbed(reservationId);
            ResponseUtil.replyEmbed(event, embed);
        } else {
            ResponseUtil.replyError(event, "취소할 수 있는 예약이 없습니다. 예약 ID를 확인하세요.");
        }
    }
}
