package com.gahyeonbot.services.ai;

import com.gahyeonbot.entity.GitHubTrending;
import com.gahyeonbot.entity.RepoReadmeCache;
import com.gahyeonbot.repository.GitHubTrendingRepository;
import com.gahyeonbot.repository.RepoReadmeCacheRepository;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.ai.support.ToolCallbacks;

import java.time.LocalDate;
import java.time.OffsetDateTime;
import java.util.List;
import java.util.Optional;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.Mockito.when;

@ExtendWith(MockitoExtension.class)
class GitHubKnowledgeToolsTest {

    @Mock
    private GitHubTrendingRepository trendingRepository;

    @Mock
    private RepoReadmeCacheRepository readmeRepository;

    private GitHubKnowledgeTools tools;

    @BeforeEach
    void setUp() {
        tools = new GitHubKnowledgeTools(trendingRepository, readmeRepository);
    }

    @Test
    void returnsLatestCollectedSnapshotWithProvenance() {
        LocalDate date = LocalDate.of(2026, 7, 25);
        GitHubTrending repo = GitHubTrending.builder()
                .id(1L)
                .snapshotDate(date)
                .repoFullName("owner/project")
                .repoUrl("https://github.com/owner/project")
                .description("collected description")
                .language("Java")
                .starsTotal(1234)
                .starsPeriod(321)
                .build();
        when(trendingRepository.findTopByOrderBySnapshotDateDescIdDesc()).thenReturn(Optional.of(repo));
        when(trendingRepository.findBySnapshotDateOrderByStarsPeriodDesc(date)).thenReturn(List.of(repo));

        assertThat(tools.getLatestTrending())
                .contains("collected_at: 2026-07-25")
                .contains("source: internal github_trending snapshot")
                .contains("owner/project")
                .contains("https://github.com/owner/project");
    }

    @Test
    void repositoryDetailCombinesCollectedSnapshotAndReadme() {
        GitHubTrending snapshot = GitHubTrending.builder()
                .snapshotDate(LocalDate.of(2026, 7, 25))
                .repoFullName("owner/project")
                .repoUrl("https://github.com/owner/project")
                .description("description")
                .starsTotal(100)
                .build();
        RepoReadmeCache readme = RepoReadmeCache.builder()
                .repoFullName("owner/project")
                .repoUrl("https://github.com/owner/project")
                .readmeSha("abc")
                .readmeText("actual collected README")
                .readmeFetchedAt(OffsetDateTime.parse("2026-07-25T06:40:00+09:00"))
                .summaryKo("수집된 요약")
                .build();
        when(trendingRepository.findTopByRepoFullNameIgnoreCaseOrderBySnapshotDateDescIdDesc("OWNER/PROJECT"))
                .thenReturn(Optional.of(snapshot));
        when(readmeRepository.findTopByRepoFullNameIgnoreCaseOrderByReadmeFetchedAtDescIdDesc("OWNER/PROJECT"))
                .thenReturn(Optional.of(readme));

        assertThat(tools.getCollectedRepository("OWNER/PROJECT"))
                .contains("repository: owner/project")
                .contains("summary_ko: 수집된 요약")
                .contains("actual collected README")
                .contains("readme_fetched_at:");
    }

    @Test
    void doesNotFallBackToLiveGithubWhenKnowledgeIsMissing() {
        when(trendingRepository.findTopByRepoFullNameIgnoreCaseOrderBySnapshotDateDescIdDesc("owner/missing"))
                .thenReturn(Optional.empty());
        when(readmeRepository.findTopByRepoFullNameIgnoreCaseOrderByReadmeFetchedAtDescIdDesc("owner/missing"))
                .thenReturn(Optional.empty());

        assertThat(tools.getCollectedRepository("owner/missing"))
                .startsWith("knowledge_empty:")
                .contains("owner/missing");
    }

    @Test
    void springAiDiscoversInternalGithubTools() {
        assertThat(ToolCallbacks.from(tools))
                .extracting(callback -> callback.getToolDefinition().name())
                .containsExactlyInAnyOrder(
                        "get_collected_github_trending",
                        "get_collected_github_repository"
                );
    }
}
