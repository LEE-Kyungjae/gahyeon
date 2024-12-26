package com.gahyeonbot.commands.out;

import com.gahyeonbot.commands.ICommand;
import com.gahyeonbot.commands.Description;
import com.gahyeonbot.manager.scheduler.LeaveSchedulerManager;
import com.gahyeonbot.models.Reservation;
import net.dv8tion.jda.api.events.interaction.command.SlashCommandInteractionEvent;
import net.dv8tion.jda.api.interactions.commands.OptionType;
import net.dv8tion.jda.api.interactions.commands.build.OptionData;

import java.util.ArrayList;
import java.util.List;
import java.util.Optional;
import java.util.concurrent.TimeUnit;

public class Out implements ICommand {

    private final LeaveSchedulerManager schedulerManager;

    public Out(LeaveSchedulerManager schedulerManager) {
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
    public List<OptionData> getOptions() {
        List<OptionData> data = new ArrayList<>();
        data.add(new OptionData(OptionType.STRING, "preset", "선택형 시간지정", false)
                .addChoice("1시간", "60")
                .addChoice("2시간", "120")
                .addChoice("3시간", "180")
                .addChoice("4시간", "240"));
        data.add(new OptionData(OptionType.INTEGER, "time", "직접 HHMM/HMM/MM 형식 시간 입력 (예: 130 → 1시간 30분)", false)
                .setMinValue(1)
                .setMaxValue(1000));
        return data;
    }

    @Override
    public void execute(SlashCommandInteractionEvent event) {
        var member = event.getMember();

        if (member == null || member.getVoiceState() == null || member.getVoiceState().getChannel() == null) {
            event.reply("오류: 보이스 채널에 접속 중이 아닙니다.").setEphemeral(true).queue();
            return;
        }

        // 예약 시간 확인
        Optional<String> timeOption = Optional.ofNullable(event.getOption("time")).map(opt -> opt.getAsString());
        if (timeOption.isEmpty()) {
            event.reply("시간을 지정해주세요.").setEphemeral(true).queue();
            return;
        }

        int minute = Integer.parseInt(timeOption.get());
        var nickname = member.getEffectiveName();

        // 예약 생성
        var task = schedulerManager.scheduleTask(() -> {
            member.getGuild().kickVoiceMember(member).queue(
                    success -> event.getHook().sendMessage(nickname + "님을 보이스 채널에서 내보냈습니다.").queue(),
                    failure -> event.getHook().sendMessage("오류 발생: " + failure.getMessage()).queue()
            );
        }, minute, TimeUnit.MINUTES);

        // 예약 추가
        long reservationId = schedulerManager.addReservation(new Reservation(
                schedulerManager.generateId(),
                member.getIdLong(),
                nickname,
                member.getGuild().getIdLong(),
                task,
                "나가기 예약"
        ));

        event.reply("예약이 생성되었습니다! 예약 ID: " + reservationId).queue();
    }
}
