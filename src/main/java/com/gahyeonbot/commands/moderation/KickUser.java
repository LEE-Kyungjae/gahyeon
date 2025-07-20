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
import java.util.concurrent.TimeUnit;

/**
 * 특정 사용자를 서버에서 추방하는 명령어.
 * 관리자 권한이 필요하며, 지정된 시간 후에 사용자를 추방합니다.
 * 
 * @author GahyeonBot Team
 * @version 1.0
 */
public class KickUser extends AbstractCommand implements ICommand {
    private final LeaveSchedulerManager schedulerManager;

    /**
     * KickUser 생성자.
     * 
     * @param schedulerManager 스케줄러 매니저
     */
    public KickUser(LeaveSchedulerManager schedulerManager) {
        this.schedulerManager = schedulerManager;
    }

    @Override
    public String getName() {
        return Description.OUT_NAME;
    }

    @Override
    public String getDescription() {
        return Description.OUT_DESC;
    }

    @Override
    public String getDetailedDescription() {
        return Description.OUT_DETAIL;
    }

    @Override
    public void execute(SlashCommandInteractionEvent event) {
        logger.info("명령어 실행 시작: {}", getName());

        var member = event.getMember();

        if (member == null || member.getVoiceState() == null || member.getVoiceState().getChannel() == null) {
            ResponseUtil.replyError(event, "오류: 보이스 채널에 접속 중이 아닙니다.");
            return;
        }

        // 시간 처리
        int minutes = resolveTime(event);
        if (minutes <= 0) {
            ResponseUtil.replyError(event, "시간을 올바르게 지정해주세요.");
            return;
        }

        var nickname = member.getEffectiveName();

        // 예약 생성
        var task = schedulerManager.scheduleTask(() -> {
            member.getGuild().kickVoiceMember(member).queue(
                    success -> ResponseUtil.sendMessageToChannel(event, nickname + "님을 보이스 채널에서 내보냈습니다."),
                    failure -> ResponseUtil.sendMessageToChannel(event, "오류 발생: " + failure.getMessage())
            );
        }, minutes, TimeUnit.MINUTES);

        // 예약 추가
        long reservationId = schedulerManager.addReservation(new Reservation(
                schedulerManager.generateId(),
                member.getIdLong(),
                nickname,
                member.getGuild().getIdLong(),
                task,
                "나가기 예약"
        ));

        // 응답 전송
        var embed = EmbedUtil.createReservationEmbed(reservationId, nickname, minutes);
        ResponseUtil.replyEmbed(event, embed);
    }

    private int resolveTime(SlashCommandInteractionEvent event) {
        var presetOption = event.getOption("preset");
        var timeOption = event.getOption("time");

        if (presetOption != null) {
            return Integer.parseInt(presetOption.getAsString());
        }
        if (timeOption != null) {
            return timeOption.getAsInt();
        }
        return -1; // 시간 미지정
    }

    @Override
    public List<OptionData> getOptions() {
        List<OptionData> options = new ArrayList<>();
        options.add(new OptionData(OptionType.USER, "user", "추방할 사용자", true));
        options.add(new OptionData(OptionType.INTEGER, "time", "추방까지 남은 시간(분)", true)
                .setMinValue(1)
                .setMaxValue(60));
        return options;
    }
}
