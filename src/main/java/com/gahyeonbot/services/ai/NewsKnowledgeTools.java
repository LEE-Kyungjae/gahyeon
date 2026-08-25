package com.gahyeonbot.services.ai;

import com.gahyeonbot.entity.NewsArticle;
import com.gahyeonbot.repository.NewsArticleRepository;
import com.gahyeonbot.services.news.NewsEventRanker;
import com.gahyeonbot.services.news.PersonalizedNewsProperties;
import lombok.RequiredArgsConstructor;
import org.springframework.ai.tool.annotation.Tool;
import org.springframework.stereotype.Component;

import java.time.OffsetDateTime;
import java.util.List;

/** Read-only conversational access to the verified personalized-news store. */
@Component
@RequiredArgsConstructor
public class NewsKnowledgeTools {
    private final PersonalizedNewsProperties properties;
    private final NewsArticleRepository articleRepository;
    private final NewsEventRanker ranker;
    private final GlmService glmService;

    @Tool(
            name = "get_recent_personalized_news",
            description = """
                    수집된 맞춤뉴스 저장소에서 오늘 또는 최근의 검증된 주요 뉴스를 조회한다.
                    사용자가 오늘 뉴스, 최신 뉴스, 주요 소식, 맞춤뉴스를 요청할 때 사용한다.
                    공식 출처 또는 복수 독립 출처로 검증된 사건과 발행 시각, 원문 URL을 반환한다.
                    반환 결과의 collected_window와 발행 시각을 근거로 최신성을 명시하고 한국어로 답한다.
                    """
    )
    public String getRecentPersonalizedNews() {
        int lookbackHours = Math.max(1, properties.getLookbackHours());
        int maximumItems = Math.max(1, properties.getMaximumItems());
        OffsetDateTime now = OffsetDateTime.now();
        List<NewsArticle> articles = articleRepository.findByPublishedAtAfterOrderByPublishedAtDesc(
                now.minusHours(lookbackHours));
        var events = ranker.rank(articles, properties.getTopics(), now, maximumItems);
        if (events.isEmpty()) {
            return "knowledge_empty: 최근 %d시간 동안 검증된 맞춤뉴스가 없어."
                    .formatted(lookbackHours);
        }

        StringBuilder output = new StringBuilder()
                .append("source: internal verified personalized_news\n")
                .append("collected_window_hours: ").append(lookbackHours)
                .append("\nresult_count: ").append(events.size());
        int index = 1;
        for (NewsEventRanker.NewsEvent event : events) {
            Localized localized = localize(event);
            if (localized == null) continue;
            output.append("\n\n- event: ").append(index++)
                    .append("\n  title_ko: ").append(localized.title())
                    .append("\n  summary_ko: ").append(localized.summary())
                    .append("\n  published_at: ").append(event.publishedAt());
            for (NewsArticle source : event.sources()) {
                output.append("\n  source: ").append(source.getSourceName())
                        .append(" | ").append(source.getCanonicalUrl());
            }
        }
        return index == 1
                ? "knowledge_unavailable: 검증된 뉴스의 한국어 변환에 실패했어."
                : output.toString();
    }

    private Localized localize(NewsEventRanker.NewsEvent event) {
        String summary = event.summary() == null ? "" : event.summary();
        if (containsHangul(event.title()) && (summary.isBlank() || containsHangul(summary))) {
            return new Localized(event.title(), summary);
        }
        GlmService.KoreanNewsTranslation translated =
                glmService.translateNewsToKorean(event.title(), summary);
        return translated == null ? null : new Localized(translated.title(), translated.summary());
    }

    private static boolean containsHangul(String text) {
        return text != null && text.codePoints().anyMatch(codePoint ->
                (codePoint >= 0xAC00 && codePoint <= 0xD7A3)
                        || (codePoint >= 0x3131 && codePoint <= 0x318E));
    }

    private record Localized(String title, String summary) {}
}
