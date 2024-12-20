package com.gahyeonbot.commands.out;

import com.gahyeonbot.ICommand;
import com.gahyeonbot.config.Description;
import com.gahyeonbot.manager.LeaveSchedulerManager;
import com.gahyeonbot.models.Reservation;
import net.dv8tion.jda.api.entities.Member;
import net.dv8tion.jda.api.entities.channel.concrete.VoiceChannel;
import net.dv8tion.jda.api.events.interaction.command.SlashCommandInteractionEvent;
import net.dv8tion.jda.api.interactions.commands.OptionType;
import net.dv8tion.jda.api.interactions.commands.build.OptionData;

import java.util.ArrayList;
import java.util.List;
import java.util.Objects;
import java.util.Optional;
import java.util.concurrent.TimeUnit;

public class WithOut implements ICommand {

    private final LeaveSchedulerManager schedulerManager;

    public WithOut(LeaveSchedulerManager schedulerManager) {
        this.schedulerManager = schedulerManager;
    }

    @Override
    public String getName() {
        return Description.WITHOUT_NAME;
    }

    @Override
    public String getDescription() {
        return Description.WITHOUT_DESC;
    }

    @Override
    public String getDetailedDescription() {
        return Description.WITHOUT_DETAIL;
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
                .setMaxValue(1440));  // 최대 24시간
        return data;
    }

    @Override
    public void execute(SlashCommandInteractionEvent event) {
        var member = event.getMember();

        if (member == null || member.getVoiceState() == null || member.getVoiceState().getChannel() == null) {
            event.reply("오류: 보이스 채널에 접속 중이 아닙니다.").setEphemeral(true).queue();
            return;
        }

        String presetValue = Optional.ofNullable(event.getOption("preset")).map(opt -> opt.getAsString()).orElse(null);
        String customValue = Optional.ofNullable(event.getOption("time")).map(opt -> opt.getAsString()).orElse(null);

        if (presetValue != null && customValue != null) {
            event.reply("오류: 'preset'과 'time' 중 하나만 선택해야 합니다.").setEphemeral(true).queue();
            return;
        }
        if (presetValue == null && customValue == null) {
            event.reply("오류: 시간을 지정해야 합니다.").setEphemeral(true).queue();
            return;
        }

        int totalMinutes = presetValue != null ? Integer.parseInt(presetValue)
                : calculateMinutes(customValue);

        if (totalMinutes <= 0) {
            event.reply("잘못된 시간 입력입니다. HHMM/HMM/MM 형식으로 입력해주세요.").setEphemeral(true).queue();
            return;
        }

        VoiceChannel voiceChannel = (VoiceChannel) member.getVoiceState().getChannel();
        List<Member> members = voiceChannel.getMembers();

        var task = schedulerManager.scheduleTask(() -> {
            for (Member voiceMember : members) {
                voiceMember.getGuild().kickVoiceMember(voiceMember).queue(
                        success -> event.getHook().sendMessage(voiceMember.getEffectiveName() + "님을 보이스 채널에서 내보냈습니다.").queue(),
                        failure -> event.getHook().sendMessage("오류 발생: " + failure.getMessage()).queue()
                );
            }
        }, totalMinutes, TimeUnit.MINUTES);

        long reservationId = schedulerManager.addReservation(new Reservation(
                schedulerManager.generateId(),
                member.getIdLong(),
                member.getEffectiveName(),
                member.getGuild().getIdLong(),
                task,
                "함께 나가기 예약"
        ));

        event.reply("예약이 생성되었습니다! 예약 ID: " + reservationId).queue();
    }

    private int calculateMinutes(String timeInput) {
        try {
            int time = Integer.parseInt(timeInput);

            if (time <= 0 || time > 2400) return -1;

            if (timeInput.length() == 4) {
                int hour = time / 100;
                int minute = time % 100;
                return (hour > 24 || minute >= 60) ? -1 : hour * 60 + minute;
            }

            if (timeInput.length() == 3) {
                int hour = time / 100;
                int minute = time % 100;
                return (hour > 24 || minute >= 60) ? -1 : hour * 60 + minute;
            }

            if (timeInput.length() <= 2) {
                return time >= 60 ? time : -1;
            }

            return -1;
        } catch (NumberFormatException e) {
            return -1;
        }
    }
}
