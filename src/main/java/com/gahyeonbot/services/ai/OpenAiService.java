package com.gahyeonbot.services.ai;

import com.gahyeonbot.config.AppCredentialsConfig;
import com.gahyeonbot.entity.OpenAiUsage;
import com.gahyeonbot.repository.OpenAiUsageRepository;
import com.gahyeonbot.services.weather.WeatherRagService;
import com.gahyeonbot.services.weather.WeatherService;
import jakarta.annotation.PostConstruct;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.ai.chat.client.ChatClient;
import org.springframework.ai.openai.OpenAiChatModel;
import org.springframework.core.ParameterizedTypeReference;
import org.springframework.core.io.ClassPathResource;
import org.springframework.http.*;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.client.RestTemplate;

import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.time.LocalDateTime;
import java.util.*;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.locks.Lock;
import java.util.concurrent.locks.ReentrantLock;

/**
 * OpenAI API 서비스 클래스 (엄격한 Rate Limiting 및 보안 강화).
 * GPT 모델을 사용하여 대화형 AI 응답을 제공합니다.
 *
 * 비용 절감 및 보안 전략:
 * 1. OpenAI Moderation API: 프롬프트 인젝션 자동 차단 (최우선 방어선)
 * 2. 키워드 필터: 공백/특수문자 우회 방지 (보조 방어선)
 * 3. Rate Limiting: 사용자당 1시간 10회, 하루 30회 제한
 * 4. 봇 전체 제한: 하루 50회, 월 100회
 * 5. 중복 차단: 10초 내 재요청 차단
 * 6. 캐싱: 반복 질문 10분 TTL
 * 7. DB 로깅: 모든 요청 기록 및 비용 추적
 *
 * @author GahyeonBot Team
 * @version 2.0
 */
@Slf4j
@Service
@RequiredArgsConstructor
public class OpenAiService {

    private final OpenAiChatModel chatModel;
    private final OpenAiUsageRepository usageRepository;
    private final AppCredentialsConfig appCredentialsConfig;
    private final ConversationHistoryService conversationHistoryService;
    private final WeatherService weatherService;
    private final WeatherRagService weatherRagService;

    private String apiKey;
    private boolean isEnabled = false;
    private RestTemplate restTemplate;
    private String systemPrompt;

    // 캐시: 최근 질문과 답변 저장 (10분 TTL)
    private final Map<String, CachedResponse> responseCache = new ConcurrentHashMap<>();

    // 사용자별 Lock: 동일 사용자의 동시 요청 방지 (ShardManager 동시성 제어)
    private final Map<Long, Lock> userLocks = new ConcurrentHashMap<>();

    // Rate Limiting 상수
    private static final int HOURLY_LIMIT_PER_USER = 75;      // 사용자당 1시간 제한
    private static final int DAILY_LIMIT_PER_USER = 30;       // 사용자당 하루 제한
    private static final int DAILY_LIMIT_TOTAL = 50;          // 봇 전체 하루 제한
    private static final int MONTHLY_LIMIT_TOTAL = 100;       // 봇 전체 월 제한
    private static final int DUPLICATE_CHECK_SECONDS = 10;    // 중복 요청 차단 시간
    private static final int MAX_PROMPT_LENGTH = 1000;        // 프롬프트 최대 길이
    private static final int CACHE_TTL_MINUTES = 10;          // 캐시 유효 시간

    // 적대적 프롬프트 키워드 (공백/특수문자 우회 방지)
    private static final List<String> ADVERSARIAL_KEYWORDS = Arrays.asList(
            // 영문 키워드
            "ignore", "disregard", "forget", "override", "bypass",
            "jailbreak", "promptinjection", "systemprompt",
            "ignoreprevious", "ignoreyour", "youarenow", "actas",
            "pretendyouare", "developmode", "danmode",
            // 한글 키워드
            "무시", "우회", "탈옥", "프롬프트주입", "시스템명령",
            "이전지시", "너는이제", "역할수행", "개발자모드"
    );

    @PostConstruct
    public void initialize() {
        // AppCredentialsConfig에서 API 키 가져오기
        this.apiKey = appCredentialsConfig.getOpenaiApiKey();

        if (apiKey == null || apiKey.isEmpty() || apiKey.startsWith("your_")) {
            log.warn("OPENAI_API_KEY가 설정되지 않았습니다. OpenAI 기능이 비활성화됩니다.");
            this.isEnabled = false;
            return;
        }

        try {
            // RestTemplate 초기화
            this.restTemplate = new RestTemplate();

            // 시스템 프롬프트 로드
            loadSystemPrompt();

            this.isEnabled = true;
            log.info("OpenAI 서비스가 활성화되었습니다. 모델: gpt-4o-mini (가현이 캐릭터 + Rate Limiting + Moderation API 적용)");
        } catch (Exception e) {
            log.error("OpenAI 초기화 실패. OpenAI 기능이 비활성화됩니다.", e);
            this.isEnabled = false;
        }
    }

    /**
     * 사용자 질문에 대해 AI 응답을 생성합니다.
     * 모든 Rate Limiting 및 보안 검사를 통과해야 합니다.
     *
     * 다중 인스턴스 대응:
     * - Interaction ID 기반 중복 방지 (여러 봇 인스턴스 병렬 실행 시)
     * - DB UNIQUE 제약조건으로 첫 번째 인스턴스만 처리
     *
     * ShardManager 동시성 제어:
     * - 동일 사용자의 요청은 Lock으로 순차 처리 (Race Condition 방지)
     * - 다른 사용자의 요청은 병렬 처리 (성능 유지)
     *
     * @param interactionId Discord Interaction ID (중복 방지용)
     * @param userId 사용자 ID
     * @param username 사용자 이름
     * @param guildId 서버 ID
     * @param userMessage 사용자의 질문 또는 메시지
     * @return AI의 응답 텍스트
     * @throws RateLimitException Rate Limit 초과 시
     * @throws AdversarialPromptException 적대적 프롬프트 감지 시
     */
    public String chat(String interactionId, Long userId, String username, Long guildId, String userMessage) throws RateLimitException, AdversarialPromptException {
        // 사용자별 Lock 획득 (동일 사용자의 동시 요청 방지)
        Lock userLock = userLocks.computeIfAbsent(userId, k -> new ReentrantLock());
        userLock.lock();
        try {
            return chatInternal(interactionId, userId, username, guildId, userMessage);
        } finally {
            userLock.unlock();
        }
    }

    /**
     * 내부 chat 메서드 (Lock으로 보호됨)
     */
    @Transactional
    private String chatInternal(String interactionId, Long userId, String username, Long guildId, String userMessage) throws RateLimitException, AdversarialPromptException {
        if (!isEnabled) {
            throw new RateLimitException("OpenAI 서비스가 비활성화되어 있습니다.");
        }

        if (userMessage == null || userMessage.trim().isEmpty()) {
            throw new IllegalArgumentException("빈 메시지가 전달되었습니다.");
        }

        // 1. 프롬프트 길이 검사
        if (userMessage.length() > MAX_PROMPT_LENGTH) {
            log.warn("프롬프트 길이 초과 - 사용자: {}, 길이: {}", username, userMessage.length());
            throw new IllegalArgumentException("질문이 너무 깁니다. " + MAX_PROMPT_LENGTH + "자 이하로 입력해주세요.");
        }

        // 2. OpenAI Moderation API 체크 (가장 강력한 필터)
        try {
            boolean isFlagged = checkModeration(userMessage);
            if (isFlagged) {
                log.warn("OpenAI Moderation 차단 - 사용자: {}", username);
                logUsage(interactionId, userId, username, guildId, userMessage, null, false, "Moderation API 차단");
                throw new AdversarialPromptException("부적절한 요청이 감지되었습니다.");
            }
        } catch (AdversarialPromptException e) {
            throw e; // 이미 차단된 경우 그대로 throw
        } catch (Exception e) {
            log.error("Moderation API 호출 실패 - 키워드 필터로 대체", e);
            // Moderation API 실패 시 키워드 필터로 대체
        }

        // 3. 키워드 기반 적대적 프롬프트 차단 (보조 필터)
        if (containsAdversarialKeyword(userMessage)) {
            log.warn("키워드 필터 차단 - 사용자: {}, 메시지: {}", username, userMessage);
            logUsage(interactionId, userId, username, guildId, userMessage, null, false, "키워드 필터 차단");
            throw new AdversarialPromptException("부적절한 요청이 감지되었습니다.");
        }

        // 4. 캐시 확인 (동일 질문에 대한 응답)
        String cacheKey = generateCacheKey(userMessage);
        CachedResponse cached = responseCache.get(cacheKey);
        if (cached != null && !cached.isExpired()) {
            log.info("캐시 히트 - 사용자: {}", username);
            logUsage(interactionId, userId, username, guildId, userMessage, cached.response, true, null);
            return cached.response;
        }

        // 5. 중복 요청 차단 (10초 내)
        LocalDateTime since = LocalDateTime.now().minusSeconds(DUPLICATE_CHECK_SECONDS);
        List<OpenAiUsage> duplicates = usageRepository.findDuplicatePrompt(userId, userMessage, since);
        if (!duplicates.isEmpty()) {
            log.warn("중복 요청 차단 - 사용자: {}, 메시지: {}", username, userMessage);
            throw new RateLimitException("같은 질문을 너무 빨리 다시 물어봤습니다. 잠시 후 다시 시도해주세요.");
        }

        // 6. 사용자당 Rate Limiting (1시간)
        LocalDateTime oneHourAgo = LocalDateTime.now().minusHours(1);
        long hourlyUsage = usageRepository.countByUserIdAndCreatedAtAfter(userId, oneHourAgo);
        if (hourlyUsage >= HOURLY_LIMIT_PER_USER) {
            log.warn("1시간 제한 초과 - 사용자: {}, 사용: {}/{}", username, hourlyUsage, HOURLY_LIMIT_PER_USER);
            throw new RateLimitException("1시간당 " + HOURLY_LIMIT_PER_USER + "회 제한을 초과했습니다. 잠시 후 다시 시도해주세요.");
        }

        // 7. 사용자당 Rate Limiting (하루)
        LocalDateTime oneDayAgo = LocalDateTime.now().minusDays(1);
        long dailyUsage = usageRepository.countByUserIdAndCreatedAtAfter(userId, oneDayAgo);
        if (dailyUsage >= DAILY_LIMIT_PER_USER) {
            log.warn("하루 제한 초과 - 사용자: {}, 사용: {}/{}", username, dailyUsage, DAILY_LIMIT_PER_USER);
            throw new RateLimitException("하루 " + DAILY_LIMIT_PER_USER + "회 제한을 초과했습니다. 내일 다시 시도해주세요.");
        }

        // 8. 전체 하루 제한
        long totalDailyUsage = usageRepository.countByCreatedAtAfter(oneDayAgo);
        if (totalDailyUsage >= DAILY_LIMIT_TOTAL) {
            log.warn("전체 하루 제한 초과 - 사용: {}/{}", totalDailyUsage, DAILY_LIMIT_TOTAL);
            throw new RateLimitException("오늘의 AI 사용 한도가 모두 소진되었습니다. 내일 다시 시도해주세요.");
        }

        // 9. 전체 월간 제한
        LocalDateTime monthStart = LocalDateTime.now().withDayOfMonth(1).withHour(0).withMinute(0).withSecond(0);
        long monthlyUsage = usageRepository.countMonthlyUsage(monthStart);
        if (monthlyUsage >= MONTHLY_LIMIT_TOTAL) {
            log.warn("월간 제한 초과 - 사용: {}/{}", monthlyUsage, MONTHLY_LIMIT_TOTAL);
            throw new RateLimitException("이번 달 AI 사용 한도가 모두 소진되었습니다. 다음 달에 다시 시도해주세요.");
        }

        // 10. 대화 히스토리 컨텍스트 빌드
        String conversationContext = "";
        try {
            conversationContext = conversationHistoryService.buildContext(userId);
            if (!conversationContext.isEmpty()) {
                log.debug("대화 컨텍스트 로드 - 사용자: {}, 컨텍스트 길이: {}자", username, conversationContext.length());
            }
        } catch (Exception e) {
            log.warn("대화 컨텍스트 로드 실패 - 무시하고 계속 진행", e);
        }

        // 10-1. 날씨 컨텍스트 빌드
        String weatherContext = "";
        try {
            weatherContext = weatherRagService.searchWeatherContext(userMessage);
            if (weatherContext.isEmpty()) {
                weatherContext = weatherService.getWeatherContext();
            }
        } catch (Exception e) {
            log.warn("날씨 컨텍스트 로드 실패 - 무시하고 계속 진행", e);
        }

        // 11. OpenAI API 호출
        try {
            log.info("OpenAI 요청 시작 - 사용자: {}, 메시지 길이: {} 문자", username, userMessage.length());

            // 컨텍스트 조합: 날씨 + 대화 히스토리 + 현재 질문
            StringBuilder contextBuilder = new StringBuilder();
            if (!weatherContext.isEmpty()) {
                contextBuilder.append(weatherContext).append("\n\n");
            }
            if (!conversationContext.isEmpty()) {
                contextBuilder.append(conversationContext).append("\n\n");
            }
            contextBuilder.append("[현재 질문]\n").append(userMessage);
            String fullUserMessage = contextBuilder.toString();

            ChatClient chatClient = ChatClient.create(chatModel);
            String response = chatClient.prompt()
                    .system(systemPrompt)
                    .user(fullUserMessage)
                    .call()
                    .content();

            log.info("OpenAI 응답 성공 - 사용자: {}, 응답 길이: {} 문자", username, response.length());

            // 12. 대화 히스토리 저장
            try {
                conversationHistoryService.saveConversation(userId, userMessage, response);
            } catch (Exception e) {
                log.warn("대화 히스토리 저장 실패 - 무시하고 계속 진행", e);
            }

            // 13. 캐시에 저장
            responseCache.put(cacheKey, new CachedResponse(response, LocalDateTime.now()));

            // 14. DB 로깅
            logUsage(interactionId, userId, username, guildId, userMessage, response, true, null);

            return response;

        } catch (Exception e) {
            log.error("OpenAI API 호출 실패 - 사용자: {}, 메시지: {}", username, userMessage, e);
            logUsage(interactionId, userId, username, guildId, userMessage, null, false, e.getMessage());
            throw new ChatProcessingException(ChatProcessingException.ErrorType.OPENAI_API_FAILURE,
                    "AI 응답을 받지 못했습니다. 잠시 후 다시 시도해주세요.", e);
        }
    }

    /**
     * 사용량을 DB에 로깅합니다.
     *
     * @throws org.springframework.dao.DataIntegrityViolationException 이미 처리된 interaction_id인 경우
     */
    private void logUsage(String interactionId, Long userId, String username, Long guildId, String prompt, String response, boolean success, String errorMessage) {
        try {
            OpenAiUsage usage = OpenAiUsage.builder()
                    .interactionId(interactionId)
                    .userId(userId)
                    .username(username)
                    .guildId(guildId)
                    .prompt(prompt)
                    .response(response)
                    .model("gpt-4o-mini")
                    .success(success)
                    .errorMessage(errorMessage)
                    .createdAt(LocalDateTime.now())
                    .build();

            usageRepository.save(usage);
        } catch (org.springframework.dao.DataIntegrityViolationException e) {
            // UNIQUE 제약조건 위반: 다른 인스턴스가 이미 처리 중
            log.warn("중복 Interaction ID 감지 - 다른 인스턴스가 처리 중: {}", interactionId);
            throw e;
        } catch (Exception e) {
            log.error("사용량 로깅 실패", e);
        }
    }

    /**
     * 적대적 프롬프트 키워드가 포함되어 있는지 검사합니다.
     * 공백, 특수문자를 제거하여 우회 시도를 차단합니다.
     *
     * 예: "무 시", "무.시", "i g n o r e" 모두 감지
     */
    private boolean containsAdversarialKeyword(String message) {
        // 공백과 ASCII 특수문자만 제거 (한글/영문 유지)
        String normalized = message.replaceAll("[\\s\\p{Punct}]", "").toLowerCase();

        for (String keyword : ADVERSARIAL_KEYWORDS) {
            String normalizedKeyword = keyword.replaceAll("[\\s\\p{Punct}]", "").toLowerCase();
            if (normalized.contains(normalizedKeyword)) {
                log.warn("키워드 필터 매칭 - 메시지: '{}', 정규화: '{}', 매칭 키워드: '{}'",
                        message, normalized, keyword);
                return true;
            }
        }
        return false;
    }

    /**
     * 캐시 키 생성 (질문 정규화)
     */
    private String generateCacheKey(String message) {
        return message.trim().toLowerCase();
    }

    /**
     * 시스템 프롬프트를 리소스에서 로드합니다.
     */
    private void loadSystemPrompt() {
        try {
            ClassPathResource resource = new ClassPathResource("prompts/gahyeon_system_prompt.txt");
            this.systemPrompt = new String(resource.getInputStream().readAllBytes(), StandardCharsets.UTF_8);
            log.info("가현이 시스템 프롬프트 로드 완료 ({}자)", systemPrompt.length());
        } catch (IOException e) {
            log.warn("시스템 프롬프트 로드 실패, 기본 프롬프트 사용", e);
            this.systemPrompt = "너는 '가현이'야. 친근하고 밝은 20대 여성이야. 반말로 짧게 대화해.";
        }
    }

    /**
     * 서비스 활성화 상태를 확인합니다.
     */
    public boolean isEnabled() {
        return isEnabled;
    }

    /**
     * 캐시된 응답 클래스
     */
    private static class CachedResponse {
        String response;
        LocalDateTime createdAt;

        CachedResponse(String response, LocalDateTime createdAt) {
            this.response = response;
            this.createdAt = createdAt;
        }

        boolean isExpired() {
            return LocalDateTime.now().isAfter(createdAt.plusMinutes(CACHE_TTL_MINUTES));
        }
    }

    /**
     * OpenAI Moderation API를 사용하여 프롬프트의 적절성을 검사합니다.
     *
     * @param message 검사할 메시지
     * @return true: 부적절한 콘텐츠 감지됨 (차단해야 함), false: 안전함
     */
    private boolean checkModeration(String message) {
        try {
            HttpHeaders headers = new HttpHeaders();
            headers.setContentType(MediaType.APPLICATION_JSON);
            headers.setBearerAuth(apiKey);

            Map<String, String> body = Map.of("input", message);
            HttpEntity<Map<String, String>> request = new HttpEntity<>(body, headers);

            ResponseEntity<Map<String, Object>> response = restTemplate.exchange(
                    "https://api.openai.com/v1/moderations",
                    HttpMethod.POST,
                    request,
                    new ParameterizedTypeReference<>() {
                    }
            );

            if (response.getStatusCode() == HttpStatus.OK) {
                Map<String, Object> responseBody = response.getBody();
                if (responseBody != null) {
                    Object resultsObj = responseBody.get("results");
                    if (resultsObj instanceof List<?> results && !results.isEmpty()) {
                        Object first = results.get(0);
                        if (first instanceof Map<?, ?> firstResult) {
                            Object flaggedObj = firstResult.get("flagged");
                            if (flaggedObj instanceof Boolean flagged && flagged) {
                                log.warn("Moderation API 차단: 부적절한 콘텐츠 감지");
                                return true;
                            }
                        }
                    }
                }
            }
            return false;

        } catch (Exception e) {
            log.error("Moderation API 호출 실패 - 키워드 필터로 대체", e);
            // API 호출 실패 시 false 반환 (키워드 필터가 대신 처리)
            return false;
        }
    }

    /**
     * Rate Limit 예외
     */
    public static class RateLimitException extends Exception {
        public RateLimitException(String message) {
            super(message);
        }
    }

    /**
     * 적대적 프롬프트 예외
     */
    public static class AdversarialPromptException extends Exception {
        public AdversarialPromptException(String message) {
            super(message);
        }
    }

    /**
     * OpenAI 처리 중 발생한 일반 오류
     */
    public static class ChatProcessingException extends RuntimeException {
        public enum ErrorType {
            OPENAI_API_FAILURE,
            UNKNOWN
        }

        private final ErrorType errorType;

        public ChatProcessingException(ErrorType errorType, String message, Throwable cause) {
            super(message, cause);
            this.errorType = errorType;
        }

        public ErrorType getErrorType() {
            return errorType;
        }
    }
}
