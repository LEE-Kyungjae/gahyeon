package com.gahyeonbot.adapters.discord.notification;

import com.gahyeonbot.entity.NewsArticle;
import com.gahyeonbot.services.ai.GlmService;
import com.gahyeonbot.services.news.NewsEventRanker;
import org.junit.jupiter.api.Test;

import java.time.OffsetDateTime;
import java.time.ZoneId;
import java.util.List;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

class PersonalizedNewsCampaignServiceTest {
    private final GlmService glmService = mock(GlmService.class);
    private final PersonalizedNewsCampaignService service =
            new PersonalizedNewsCampaignService(null, null, null, null, null, null, glmService);

    @Test
    void translatesForeignNewsToKoreanBeforeFormatting() {
        OffsetDateTime publishedAt = OffsetDateTime.parse("2026-08-18T08:00:00+09:00");
        var event = new NewsEventRanker.NewsEvent(
                "NASA announces new lunar mission", "The launch is planned for 2028.",
                publishedAt, 10, List.of(article("https://official.example/moon")));
        when(glmService.translateNewsToKorean(event.title(), event.summary())).thenReturn(
                new GlmService.KoreanNewsTranslation(
                        "NASA, 새 달 탐사 임무 발표", "발사는 2028년으로 계획되어 있습니다."));

        String message = service.format(service.localizeToKorean(List.of(event)), ZoneId.of("Asia/Seoul"));

        assertThat(message)
                .contains("NASA, 새 달 탐사 임무 발표")
                .contains("발사는 2028년으로 계획되어 있습니다.")
                .doesNotContain("announces new lunar mission")
                .doesNotContain("The launch is planned");
    }

    @Test
    void preservesKoreanNewsWithoutCallingTranslator() {
        OffsetDateTime publishedAt = OffsetDateTime.parse("2026-08-18T08:00:00+09:00");
        var event = new NewsEventRanker.NewsEvent(
                "한국형 발사체 시험 성공", "발사체가 목표 궤도에 진입했습니다.",
                publishedAt, 10, List.of(article("https://official.example/rocket")));

        assertThat(service.localizeToKorean(List.of(event))).containsExactly(event);
        verify(glmService, never()).translateNewsToKorean(event.title(), event.summary());
    }

    @Test
    void neverShowsForeignOriginalWhenTranslationFails() {
        OffsetDateTime publishedAt = OffsetDateTime.parse("2026-08-18T08:00:00+09:00");
        var event = new NewsEventRanker.NewsEvent(
                "Foreign headline", "Foreign summary", publishedAt, 10,
                List.of(article("https://official.example/foreign")));

        String message = service.format(service.localizeToKorean(List.of(event)), ZoneId.of("Asia/Seoul"));

        assertThat(message).isBlank();
    }

    @Test
    void preservesCompleteSourceUrlsInsteadOfTruncatingAnEvent() {
        String longUrl = "https://official.example/" + "a".repeat(1750);
        NewsArticle firstSource = article("https://official.example/first");
        NewsArticle oversizedSource = article(longUrl);
        OffsetDateTime publishedAt = OffsetDateTime.parse("2026-08-18T08:00:00+09:00");
        var first = new NewsEventRanker.NewsEvent("First", "Summary", publishedAt, 10, List.of(firstSource));
        var oversized = new NewsEventRanker.NewsEvent("Oversized", "Summary", publishedAt, 9,
                List.of(oversizedSource));

        String message = service.format(List.of(first, oversized), ZoneId.of("Asia/Seoul"));

        assertThat(message).contains("https://official.example/first");
        assertThat(message).doesNotContain("Oversized").doesNotContain(longUrl);
        assertThat(message.length()).isLessThanOrEqualTo(1900);
    }

    private NewsArticle article(String url) {
        return NewsArticle.builder()
                .sourceName("Official")
                .canonicalUrl(url)
                .build();
    }
}
