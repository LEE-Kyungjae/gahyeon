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
import org.springframework.http.MediaType;
import org.springframework.test.web.client.MockRestServiceServer;
import org.springframework.web.client.RestTemplate;

import java.time.LocalDate;
import java.time.OffsetDateTime;
import java.util.List;
import java.util.Optional;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.Mockito.when;
import static org.springframework.test.web.client.ExpectedCount.once;
import static org.springframework.test.web.client.match.MockRestRequestMatchers.header;
import static org.springframework.test.web.client.match.MockRestRequestMatchers.requestTo;
import static org.springframework.test.web.client.response.MockRestResponseCreators.withSuccess;

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
                        "search_collected_github_repositories",
                        "get_collected_github_trending",
                        "get_collected_github_repository"
                );
    }

    @Test
    void formatsBm25VectorRrfResultsFromInternalIndex() {
        PaperRagProperties properties = new PaperRagProperties();
        properties.setEnabled(true);
        properties.setBaseUrl("http://knowledge.internal:8765");
        properties.setApiKey("secret");
        RestTemplate client = new RestTemplate();
        MockRestServiceServer server = MockRestServiceServer.bindTo(client).build();
        server.expect(once(), requestTo("http://knowledge.internal:8765/github/search"))
                .andExpect(header("X-API-Key", "secret"))
                .andRespond(withSuccess("""
                        {
                          "fusion": "rrf",
                          "retrievers": ["bm25", "vector"],
                          "results": [{
                            "repo_full_name": "owner/rag-agent",
                            "repo_url": "https://github.com/owner/rag-agent",
                            "readme_fetched_at": "2026-07-25T00:00:00Z",
                            "score": 0.032,
                            "chunks": [{
                              "matched_by": ["bm25", "vector"],
                              "text": "Agent memory with retrieval augmented generation"
                            }]
                          }]
                        }
                        """, MediaType.APPLICATION_JSON));

        String result = new GitHubKnowledgeTools(
                trendingRepository, readmeRepository, properties, client)
                .searchRepositories("RAG agent memory");

        assertThat(result)
                .contains("source: internal Qdrant github_readmes")
                .contains("retrievers: [bm25, vector]")
                .contains("fusion: rrf")
                .contains("owner/rag-agent")
                .contains("matched_by: [bm25, vector]");
        server.verify();
    }
}
