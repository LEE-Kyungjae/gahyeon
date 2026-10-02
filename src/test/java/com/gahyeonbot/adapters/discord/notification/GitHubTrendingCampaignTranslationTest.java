package com.gahyeonbot.adapters.discord.notification;

import com.gahyeonbot.entity.GitHubTrendingEvent;
import com.gahyeonbot.repository.RepoReadmeCacheRepository;
import com.gahyeonbot.services.ai.GlmService;
import org.junit.jupiter.api.Test;

import java.util.Optional;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.when;

class GitHubTrendingCampaignTranslationTest {
    @Test
    void translatesEnglishDescriptionWhenNoKoreanReadmeSummaryExists() {
        RepoReadmeCacheRepository cache = mock(RepoReadmeCacheRepository.class);
        GlmService glm = mock(GlmService.class);
        GitHubTrendingCampaignService service = new GitHubTrendingCampaignService(
                null, null, null, cache, glm, null);
        GitHubTrendingEvent event = GitHubTrendingEvent.builder()
                .repoFullName("AprilNEA/OpenLogi")
                .description("A native local-first alternative with no telemetry.")
                .build();
        when(cache.findTopByRepoFullNameOrderByReadmeFetchedAtDescIdDesc("AprilNEA/OpenLogi"))
                .thenReturn(Optional.empty());
        when(glm.translateNewsToKorean(
                "AprilNEA/OpenLogi 저장소", event.getDescription())).thenReturn(
                new GlmService.KoreanNewsTranslation(
                        "AprilNEA/OpenLogi 저장소", "텔레메트리가 없는 로컬 우선 대안입니다."));

        assertThat(service.resolveDescriptionForDigest(event))
                .isEqualTo("텔레메트리가 없는 로컬 우선 대안입니다.")
                .doesNotContain("local-first");
    }
}
