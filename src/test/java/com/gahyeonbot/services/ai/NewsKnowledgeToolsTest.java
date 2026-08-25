package com.gahyeonbot.services.ai;

import com.gahyeonbot.entity.NewsArticle;
import com.gahyeonbot.repository.NewsArticleRepository;
import com.gahyeonbot.services.news.NewsEventRanker;
import com.gahyeonbot.services.news.PersonalizedNewsProperties;
import org.junit.jupiter.api.Test;
import org.springframework.ai.support.ToolCallbacks;

import java.time.OffsetDateTime;
import java.util.List;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.when;

class NewsKnowledgeToolsTest {
    @Test
    void exposesVerifiedRecentNewsAsAKoreanAgentToolWithSources() {
        PersonalizedNewsProperties properties = new PersonalizedNewsProperties();
        properties.setLookbackHours(30);
        properties.setMaximumItems(5);
        NewsArticleRepository repository = mock(NewsArticleRepository.class);
        NewsEventRanker ranker = mock(NewsEventRanker.class);
        GlmService glm = mock(GlmService.class);
        NewsArticle source = NewsArticle.builder()
                .sourceName("Official")
                .canonicalUrl("https://official.example/news")
                .build();
        var event = new NewsEventRanker.NewsEvent(
                "Global headline", "Global summary",
                OffsetDateTime.parse("2026-08-22T10:00:00+09:00"), 10, List.of(source));
        when(repository.findByPublishedAtAfterOrderByPublishedAtDesc(any())).thenReturn(List.of(source));
        when(ranker.rank(any(), any(), any(), any(Integer.class))).thenReturn(List.of(event));
        when(glm.translateNewsToKorean(event.title(), event.summary())).thenReturn(
                new GlmService.KoreanNewsTranslation("세계 주요 소식", "핵심 내용을 한국어로 전합니다."));

        NewsKnowledgeTools tools = new NewsKnowledgeTools(properties, repository, ranker, glm);

        assertThat(tools.getRecentPersonalizedNews())
                .contains("세계 주요 소식")
                .contains("핵심 내용을 한국어로 전합니다.")
                .contains("https://official.example/news")
                .doesNotContain("Global headline");
        assertThat(ToolCallbacks.from(tools))
                .extracting(callback -> callback.getToolDefinition().name())
                .containsExactly("get_recent_personalized_news");
    }
}
