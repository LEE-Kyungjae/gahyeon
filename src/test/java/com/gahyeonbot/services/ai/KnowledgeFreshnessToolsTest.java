package com.gahyeonbot.services.ai;

import com.gahyeonbot.entity.GitHubTrending;
import com.gahyeonbot.entity.RepoReadmeCache;
import com.gahyeonbot.repository.GitHubTrendingRepository;
import com.gahyeonbot.repository.RepoReadmeCacheRepository;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.ai.support.ToolCallbacks;

import java.time.LocalDate;
import java.time.OffsetDateTime;
import java.util.Optional;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.Mockito.when;

@ExtendWith(MockitoExtension.class)
class KnowledgeFreshnessToolsTest {

    @Mock
    private GitHubTrendingRepository trendingRepository;

    @Mock
    private RepoReadmeCacheRepository readmeRepository;

    @Test
    void reportsCollectedDatesAndDisabledPaperIndexWithoutNetwork() {
        GitHubTrending trending = GitHubTrending.builder()
                .snapshotDate(LocalDate.of(2026, 7, 25))
                .build();
        RepoReadmeCache readme = RepoReadmeCache.builder()
                .readmeFetchedAt(OffsetDateTime.parse("2026-07-25T06:40:00+09:00"))
                .build();
        when(trendingRepository.findTopByOrderBySnapshotDateDescIdDesc()).thenReturn(Optional.of(trending));
        when(readmeRepository.findTopByOrderByReadmeFetchedAtDescIdDesc()).thenReturn(Optional.of(readme));
        PaperRagProperties properties = new PaperRagProperties();
        properties.setEnabled(false);

        KnowledgeFreshnessTools tools = new KnowledgeFreshnessTools(
                trendingRepository, readmeRepository, properties);

        assertThat(tools.getFreshness())
                .contains("github_trending_snapshot: 2026-07-25")
                .contains("github_readme_fetched_at: 2026-07-25T06:40+09:00")
                .contains("hf_papers: disabled");
        assertThat(ToolCallbacks.from(tools))
                .extracting(callback -> callback.getToolDefinition().name())
                .containsExactly("get_internal_knowledge_freshness");
    }
}
