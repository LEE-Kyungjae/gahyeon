package com.gahyeonbot.entity;

import jakarta.persistence.*;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.LocalDateTime;

/**
 * OpenAI API 사용 내역을 저장하는 엔티티.
 * 사용자별, 시간대별 API 호출을 추적하여 비용 관리와 Rate Limiting에 사용됩니다.
 *
 * @author GahyeonBot Team
 * @version 1.0
 */
@Entity
@Table(name = "openai_usage", indexes = {
        @Index(name = "idx_user_id", columnList = "user_id"),
        @Index(name = "idx_created_at", columnList = "created_at"),
        @Index(name = "idx_user_created", columnList = "user_id, created_at")
})
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class OpenAiUsage {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    /**
     * Discord Interaction ID (중복 방지용)
     * 여러 봇 인스턴스가 병렬 실행되어도 같은 요청은 한 번만 처리
     */
    @Column(name = "interaction_id", unique = true, nullable = false, length = 100)
    private String interactionId;

    /**
     * Discord 사용자 ID (숫자)
     */
    @Column(name = "user_id", nullable = false)
    private Long userId;

    /**
     * Discord 사용자 이름
     */
    @Column(name = "username", nullable = false, length = 100)
    private String username;

    /**
     * Discord 서버(Guild) ID
     */
    @Column(name = "guild_id")
    private Long guildId;

    /**
     * 사용자 질문 (원본)
     */
    @Column(name = "prompt", nullable = false, columnDefinition = "TEXT")
    private String prompt;

    /**
     * AI 응답 (원본)
     */
    @Column(name = "response", columnDefinition = "TEXT")
    private String response;

    /**
     * 프롬프트 토큰 수
     */
    @Column(name = "prompt_tokens")
    private Integer promptTokens;

    /**
     * 응답 토큰 수
     */
    @Column(name = "response_tokens")
    private Integer responseTokens;

    /**
     * 전체 토큰 수
     */
    @Column(name = "total_tokens")
    private Integer totalTokens;

    /**
     * 사용된 모델 (예: gpt-4o-mini)
     */
    @Column(name = "model", length = 50)
    private String model;

    /**
     * 요청 성공 여부
     */
    @Column(name = "success", nullable = false)
    @Builder.Default
    private Boolean success = true;

    /**
     * 에러 메시지 (실패 시)
     */
    @Column(name = "error_message", columnDefinition = "TEXT")
    private String errorMessage;

    /**
     * 생성 시간
     */
    @Column(name = "created_at", nullable = false)
    @Builder.Default
    private LocalDateTime createdAt = LocalDateTime.now();
}
