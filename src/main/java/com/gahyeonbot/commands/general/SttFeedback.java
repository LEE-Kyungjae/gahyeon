package com.gahyeonbot.commands.general;

import com.gahyeonbot.adapters.discord.DiscordIdentityMapper;
import com.gahyeonbot.application.speech.SttLearningService;
import com.gahyeonbot.commands.util.AbstractCommand;
import net.dv8tion.jda.api.events.interaction.command.SlashCommandInteractionEvent;
import net.dv8tion.jda.api.interactions.DiscordLocale;
import net.dv8tion.jda.api.interactions.commands.OptionType;
import net.dv8tion.jda.api.interactions.commands.build.OptionData;
import org.springframework.stereotype.Component;
import java.util.List;
import java.util.Map;

@Component
public class SttFeedback extends AbstractCommand {
    private final SttLearningService learning;
    private final DiscordIdentityMapper identities;
    public SttFeedback(SttLearningService learning, DiscordIdentityMapper identities) {
        this.learning = learning;
        this.identities = identities;
    }
    @Override public String getName() { return "stt-feedback"; }
    @Override public Map<DiscordLocale, String> getNameLocalizations() { return localizeKorean("음성정정"); }
    @Override public String getDescription() { return "본인의 음성 인식 기록을 조회하고 정정합니다."; }
    @Override public String getDetailedDescription() { return "/음성정정"; }
    @Override public List<OptionData> getOptions() {
        return List.of(new OptionData(OptionType.STRING, "action", "동작", true)
                        .addChoice("최근 기록", "recent").addChoice("정정", "correct")
                        .addChoice("교정 중지", "disable").addChoice("학습 기록 삭제", "clear"),
                new OptionData(OptionType.STRING, "record", "전사 기록 ID", false).setMaxLength(64),
                new OptionData(OptionType.STRING, "expected", "실제로 말한 문장", false).setMaxLength(512));
    }
    @Override public void execute(SlashCommandInteractionEvent event) {
        if (event.getGuild() == null) {
            event.reply("서버 안에서만 사용할 수 있습니다.").setEphemeral(true).queue();
            return;
        }
        // Actor and server come only from the authenticated Discord event, never user-supplied options.
        event.deferReply(true).queue(hook -> {
            try {
                long actor = identities.toActorId(event.getUser().getIdLong(), event.getUser().getName()).value();
                String scope = "discord:" + event.getGuild().getId();
                String action = event.getOption("action").getAsString();
                String result;
                if (action.equals("recent")) {
                    var records = learning.recent(actor, scope);
                    result = records.isEmpty() ? "최근 전사 기록이 없습니다." : records.stream()
                            .map(o -> o.id() + "\n인식: " + shortText(o.raw()) + "\n적용: " + shortText(o.effective()))
                            .reduce((a, b) -> a + "\n\n" + b).orElseThrow();
                } else if (action.equals("clear")) {
                    learning.clear(actor, scope);
                    result = "이 서버의 본인 STT 학습 기록을 삭제했습니다.";
                } else {
                    if (event.getOption("record") == null) throw new IllegalArgumentException("전사 기록 ID가 필요합니다.");
                    String id = event.getOption("record").getAsString();
                    if (action.equals("disable")) {
                        learning.disable(actor, scope, id);
                        result = "해당 문장의 자동 교정을 중지했습니다.";
                    } else if (action.equals("correct")) {
                        if (event.getOption("expected") == null) throw new IllegalArgumentException("실제로 말한 문장이 필요합니다.");
                        String state = learning.correct(actor, scope, id, event.getOption("expected").getAsString());
                        result = switch (state) {
                            case "ACTIVE" -> "정정을 저장했습니다. 자동 교정 활성 상태입니다.";
                            case "VALIDATING" -> "정정을 저장했습니다. 추가 발화 검증 중입니다.";
                            case "BLOCKED" -> "정정을 저장했습니다. 해당 문장의 자동 교정은 중지 상태입니다.";
                            default -> "정정을 저장했습니다. 사례 수집 중입니다.";
                        };
                    } else throw new IllegalArgumentException("지원하지 않는 동작입니다.");
                }
                hook.editOriginal(result).setAllowedMentions(List.of()).queue();
            } catch (IllegalArgumentException invalid) {
                hook.editOriginal(invalid.getMessage()).setAllowedMentions(List.of()).queue();
            } catch (RuntimeException failure) {
                logger.warn("STT feedback failed type={}", failure.getClass().getSimpleName());
                hook.editOriginal("STT 학습 기록을 처리하지 못했습니다.").queue();
            }
        });
    }
    private static String shortText(String value) {
        return value.replace('\n', ' ').substring(0, Math.min(value.length(), 100));
    }
}
