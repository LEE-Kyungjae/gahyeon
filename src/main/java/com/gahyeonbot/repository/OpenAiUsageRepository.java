package com.gahyeonbot.repository;

import com.gahyeonbot.entity.OpenAiUsage;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;

import java.time.LocalDateTime;
import java.util.List;

/**
 * OpenAI API 사용 내역 Repository.
 * Rate Limiting 및 사용량 통계 조회를 지원합니다.
 *
 * @author GahyeonBot Team
 * @version 1.0
 */
@Repository
public interface OpenAiUsageRepository extends JpaRepository<OpenAiUsage, Long> {

    /**
     * 특정 사용자의 특정 시간 이후 사용 횟수 조회
     *
     * @param userId 사용자 ID
     * @param since 시작 시간
     * @return 사용 횟수
     */
    @Query("SELECT COUNT(u) FROM OpenAiUsage u WHERE u.userId = :userId AND u.createdAt >= :since AND u.success = true")
    long countByUserIdAndCreatedAtAfter(@Param("userId") Long userId, @Param("since") LocalDateTime since);

    /**
     * 전체 사용자의 특정 시간 이후 사용 횟수 조회
     *
     * @param since 시작 시간
     * @return 사용 횟수
     */
    @Query("SELECT COUNT(u) FROM OpenAiUsage u WHERE u.createdAt >= :since AND u.success = true")
    long countByCreatedAtAfter(@Param("since") LocalDateTime since);

    /**
     * 특정 사용자의 최근 사용 내역 조회 (중복 질문 체크용)
     *
     * @param userId 사용자 ID
     * @param since 시작 시간
     * @return 사용 내역 리스트
     */
    @Query("SELECT u FROM OpenAiUsage u WHERE u.userId = :userId AND u.createdAt >= :since ORDER BY u.createdAt DESC")
    List<OpenAiUsage> findRecentUsageByUserId(@Param("userId") Long userId, @Param("since") LocalDateTime since);

    /**
     * 특정 사용자의 특정 프롬프트 최근 사용 여부 확인 (10초 내 중복 체크)
     *
     * @param userId 사용자 ID
     * @param prompt 프롬프트
     * @param since 시작 시간
     * @return 사용 내역 (있으면 중복)
     */
    @Query("SELECT u FROM OpenAiUsage u WHERE u.userId = :userId AND u.prompt = :prompt AND u.createdAt >= :since")
    List<OpenAiUsage> findDuplicatePrompt(@Param("userId") Long userId, @Param("prompt") String prompt, @Param("since") LocalDateTime since);

    /**
     * 월간 전체 사용 횟수 조회
     *
     * @param monthStart 월 시작 시간
     * @return 사용 횟수
     */
    @Query("SELECT COUNT(u) FROM OpenAiUsage u WHERE u.createdAt >= :monthStart AND u.success = true")
    long countMonthlyUsage(@Param("monthStart") LocalDateTime monthStart);
}
