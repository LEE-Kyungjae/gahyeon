package com.gahyeonbot.commands.general;

import com.gahyeonbot.commands.util.*;
import com.gahyeonbot.services.ai.OpenAiService;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import net.dv8tion.jda.api.events.interaction.command.SlashCommandInteractionEvent;
import net.dv8tion.jda.api.interactions.DiscordLocale;
import net.dv8tion.jda.api.interactions.commands.OptionType;
import net.dv8tion.jda.api.interactions.commands.build.OptionData;
import org.springframework.stereotype.Component;

import java.util.List;
import java.util.Map;

/**
 * OpenAI GPT를 사용한 AI 대화 명령어 클래스.
 * 사용자의 질문에 대해 AI가 응답합니다.
 *
 * @author GahyeonBot Team
 * @version 1.0
 */
@Slf4j
@Component
@RequiredArgsConstructor
public class Gahyeona extends AbstractCommand {

    private final OpenAiService openAiService;

    @Override
    public String getName() {
        return Description.GAHYEONA_NAME;
    }

    @Override
    public Map<DiscordLocale, String> getNameLocalizations() {
        return localizeKorean(Description.GAHYEONA_NAME_KO);
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
                new OptionData(OptionType.STRING, "question", "가현아에게 물어볼 질문을 입력하세요", true)
        );
    }

    @Override
    public void execute(SlashCommandInteractionEvent event) {
        log.info("명령어 실행 시작: {}", getName());

        // 즉시 응답 (3초 이내 필수) - 동기로 처리하여 성공 확인
        try {
            event.deferReply().complete();
        } catch (Exception e) {
            log.error("deferReply 실패 - 다른 인스턴스가 처리 중이거나 타임아웃: {}", e.getMessage());
            return;
        }

        try {
            // OpenAI 서비스 활성화 확인
            if (!openAiService.isEnabled()) {
                event.getHook().editOriginal("❌ OpenAI 서비스가 비활성화되어 있습니다. 관리자에게 문의하세요.").complete();
                return;
            }

            // 질문 옵션 가져오기
            String question = event.getOption("question").getAsString();

            if (question == null || question.trim().isEmpty()) {
                event.getHook().editOriginal("❌ 질문을 입력해주세요.").complete();
                return;
            }

            // 질문 길이 제한 (1000자)
            if (question.length() > 1000) {
                event.getHook().editOriginal("❌ 질문이 너무 깁니다. 1000자 이하로 입력해주세요.").complete();
                return;
            }
            log.info("OpenAI 요청 - 사용자: {}, 질문: {}", event.getUser().getName(), question);

            String interactionId = event.getId();  // Discord Interaction ID (중복 방지용)
            Long userId = event.getUser().getIdLong();
            String username = event.getUser().getName();
            Long guildId = event.getGuild() != null ? event.getGuild().getIdLong() : null;

            // OpenAI API 호출
            String response = openAiService.chat(interactionId, userId, username, guildId, question);

            if (response == null || response.trim().isEmpty()) {
                event.getHook().editOriginal("AI 응답을 받지 못했습니다. 잠시 후 다시 시도해주세요.").complete();
                return;
            }

            // 응답 전송 (Discord 메시지 길이 제한: 2000자)
            if (response.length() > 2000) {
                response = response.substring(0, 1997) + "...";
            }

            // 동기로 응답 전송하여 성공 확인
            event.getHook().editOriginalEmbeds(
                    EmbedUtil.nomal(response).build()
            ).complete();

            log.info("OpenAI 응답 전송 완료 - 사용자: {}", event.getUser().getName());

        } catch (org.springframework.dao.DataIntegrityViolationException e) {
            log.warn("중복 Interaction 감지 - 다른 인스턴스가 이미 처리 중: {}", event.getUser().getName());
            // 다른 인스턴스가 처리 중이므로 조용히 종료 (사용자는 이미 응답을 받을 것)
            safeEditOriginal(event, "요청을 처리 중입니다...");
        } catch (OpenAiService.RateLimitException e) {
            log.warn("Rate Limit 초과 - 사용자: {}, 메시지: {}", event.getUser().getName(), e.getMessage());
            safeEditOriginal(event, "⚠️ " + e.getMessage());
        } catch (OpenAiService.AdversarialPromptException e) {
            log.warn("적대적 프롬프트 감지 - 사용자: {}", event.getUser().getName());
            safeEditOriginal(event, "🚫 " + e.getMessage());
        } catch (IllegalArgumentException e) {
            log.warn("잘못된 요청 - 사용자: {}, 메시지: {}", event.getUser().getName(), e.getMessage());
            safeEditOriginal(event, e.getMessage());
        } catch (OpenAiService.ChatProcessingException e) {
            OpenAiService.ChatProcessingException.ErrorType errorType = e.getErrorType();
            log.error("OpenAI 처리 오류 - 사용자: {}, 유형: {}", event.getUser().getName(), errorType, e);
            String userMessage;
            if (errorType == OpenAiService.ChatProcessingException.ErrorType.OPENAI_API_FAILURE) {
                userMessage = "AI 서버와 통신 중 문제가 발생했어요. 잠시 후 다시 시도해 주세요.";
            } else {
                userMessage = "시스템 오류가 발생했습니다. 잠시 후 다시 시도해 주세요.";
            }
            safeEditOriginal(event, userMessage);
        } catch (Exception e) {
            log.error("OpenAI 명령어 실행 중 오류 발생", e);
            safeEditOriginal(event, "오류가 발생했습니다. 잠시 후 다시 시도해주세요.");
        }
    }

    /**
     * InteractionHook이 만료되었거나 실패해도 안전하게 응답을 전송합니다.
     */
    private void safeEditOriginal(SlashCommandInteractionEvent event, String message) {
        try {
            event.getHook().editOriginal(message).complete();
        } catch (Exception e) {
            log.warn("응답 전송 실패 (InteractionHook 만료 가능) - 사용자: {}, 메시지: {}",
                    event.getUser().getName(), e.getMessage());
        }
    }

}
