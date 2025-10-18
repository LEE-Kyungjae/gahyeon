package com.gahyeonbot.commands.general;

import com.gahyeonbot.commands.util.*;
import com.gahyeonbot.services.ai.OpenAiService;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import net.dv8tion.jda.api.events.interaction.command.SlashCommandInteractionEvent;
import net.dv8tion.jda.api.interactions.commands.OptionType;
import net.dv8tion.jda.api.interactions.commands.build.OptionData;

import java.util.List;

/**
 * OpenAI GPT를 사용한 AI 대화 명령어 클래스.
 * 사용자의 질문에 대해 AI가 응답합니다.
 *
 * @author GahyeonBot Team
 * @version 1.0
 */
@Slf4j
@RequiredArgsConstructor
public class Gahyeona extends AbstractCommand {

    private final OpenAiService openAiService;

    @Override
    public String getName() {
        return Description.GAHYEONA_NAME;
    }

    @Override
    public String getDescription() {
        return Description.GAHYEONA_DESC;
    }

    @Override
    public String getDetailedDescription() {
        return Description.GAHYEONA_DETAIL;
    }

    @Override
    public List<OptionData> getOptions() {
        return List.of(
                new OptionData(OptionType.STRING, "질문", "가현아에게 물어볼 질문을 입력하세요", true)
        );
    }

    @Override
    public void execute(SlashCommandInteractionEvent event) {
        log.info("명령어 실행 시작: {}", getName());

        // OpenAI 서비스 활성화 확인
        if (!openAiService.isEnabled()) {
            ResponseUtil.replyError(event, "OpenAI 서비스가 비활성화되어 있습니다. 관리자에게 문의하세요.");
            return;
        }

        // 질문 옵션 가져오기
        String question = event.getOption("질문").getAsString();

        if (question == null || question.trim().isEmpty()) {
            ResponseUtil.replyError(event, "질문을 입력해주세요.");
            return;
        }

        // 질문 길이 제한 (1000자)
        if (question.length() > 1000) {
            ResponseUtil.replyError(event, "질문이 너무 깁니다. 1000자 이하로 입력해주세요.");
            return;
        }

        // 즉시 응답 (대기 메시지)
        event.deferReply().queue();

        try {
            log.info("OpenAI 요청 - 사용자: {}, 질문: {}", event.getUser().getName(), question);

            String interactionId = event.getId();  // Discord Interaction ID (중복 방지용)
            Long userId = event.getUser().getIdLong();
            String username = event.getUser().getName();
            Long guildId = event.getGuild() != null ? event.getGuild().getIdLong() : null;

            // OpenAI API 호출
            String response = openAiService.chat(interactionId, userId, username, guildId, question);

            if (response == null || response.trim().isEmpty()) {
                event.getHook().editOriginal("AI 응답을 받지 못했습니다. 잠시 후 다시 시도해주세요.").queue();
                return;
            }

            // 응답 전송 (Discord 메시지 길이 제한: 2000자)
            if (response.length() > 2000) {
                response = response.substring(0, 1997) + "...";
            }

            String embedMessage = String.format("**질문:** %s\n\n**답변:**\n%s",
                    question.length() > 100 ? question.substring(0, 97) + "..." : question,
                    response);

            event.getHook().editOriginalEmbeds(
                    EmbedUtil.nomal(embedMessage).build()
            ).queue();

            log.info("OpenAI 응답 전송 완료 - 사용자: {}", event.getUser().getName());

        } catch (org.springframework.dao.DataIntegrityViolationException e) {
            log.warn("중복 Interaction 감지 - 다른 인스턴스가 이미 처리 중: {}", event.getUser().getName());
            // 다른 인스턴스가 처리 중이므로 조용히 종료 (사용자는 이미 응답을 받을 것)
            event.getHook().editOriginal("요청을 처리 중입니다...").queue();
        } catch (OpenAiService.RateLimitException e) {
            log.warn("Rate Limit 초과 - 사용자: {}, 메시지: {}", event.getUser().getName(), e.getMessage());
            event.getHook().editOriginal("⚠️ " + e.getMessage()).queue();
        } catch (OpenAiService.AdversarialPromptException e) {
            log.warn("적대적 프롬프트 감지 - 사용자: {}", event.getUser().getName());
            event.getHook().editOriginal("🚫 " + e.getMessage()).queue();
        } catch (IllegalArgumentException e) {
            log.warn("잘못된 요청 - 사용자: {}, 메시지: {}", event.getUser().getName(), e.getMessage());
            event.getHook().editOriginal(e.getMessage()).queue();
        } catch (Exception e) {
            log.error("OpenAI 명령어 실행 중 오류 발생", e);
            event.getHook().editOriginal("오류가 발생했습니다. 잠시 후 다시 시도해주세요.").queue();
        }
    }
}
