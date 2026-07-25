package com.gahyeonbot.services.ai;

import com.gahyeonbot.entity.GitHubTrending;
import com.gahyeonbot.entity.RepoReadmeCache;
import com.gahyeonbot.repository.GitHubTrendingRepository;
import com.gahyeonbot.repository.RepoReadmeCacheRepository;
import org.springframework.ai.tool.annotation.Tool;
import org.springframework.ai.tool.annotation.ToolParam;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.core.ParameterizedTypeReference;
import org.springframework.http.HttpEntity;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpMethod;
import org.springframework.http.MediaType;
import org.springframework.stereotype.Component;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.client.RestTemplate;

import java.time.LocalDate;
import java.util.List;
import java.util.Map;

/**
 * Airflow가 수집한 GitHub 스냅샷과 README 캐시를 조회하는 에이전트 도구.
 *
 * 외부 GitHub API를 다시 호출하지 않으며, 수집 파이프라인이 PostgreSQL에
 * 저장한 데이터만 근거로 반환합니다.
 */
@Component
public class GitHubKnowledgeTools {

    private static final int MAX_TRENDING_RESULTS = 15;
    private static final int MAX_README_CHARS = 10_000;

    private final GitHubTrendingRepository trendingRepository;
    private final RepoReadmeCacheRepository readmeRepository;
    private final PaperRagProperties properties;
    private final RestTemplate hybridClient;

    @Autowired
    public GitHubKnowledgeTools(
            GitHubTrendingRepository trendingRepository,
            RepoReadmeCacheRepository readmeRepository,
            PaperRagProperties properties
    ) {
        this(trendingRepository, readmeRepository, properties,
                PaperKnowledgeTools.createClient(properties));
    }

    GitHubKnowledgeTools(
            GitHubTrendingRepository trendingRepository,
            RepoReadmeCacheRepository readmeRepository
    ) {
        this(trendingRepository, readmeRepository, new PaperRagProperties(), new RestTemplate());
    }

    GitHubKnowledgeTools(
            GitHubTrendingRepository trendingRepository,
            RepoReadmeCacheRepository readmeRepository,
            PaperRagProperties properties,
            RestTemplate hybridClient
    ) {
        this.trendingRepository = trendingRepository;
        this.readmeRepository = readmeRepository;
        this.properties = properties;
        this.hybridClient = hybridClient;
    }

    @Tool(
            name = "search_collected_github_repositories",
            description = """
                    내부에서 수집한 GitHub README를 BM25와 multilingual vector search로 함께 검색한다.
                    특정 기술, 기능, 라이브러리 또는 구현체에 맞는 저장소를 찾을 때 사용한다.
                    정확한 저장소 이름을 이미 알면 get_collected_github_repository를 사용한다.
                    """
    )
    public String searchRepositories(
            @ToolParam(description = "찾으려는 구현, 기술 또는 저장소 특징을 담은 독립적인 검색 질의")
            String query
    ) {
        if (query == null || query.isBlank()) {
            return "tool_error: GitHub repository 검색 query가 필요해.";
        }
        if (!properties.isEnabled() || properties.getApiKey() == null
                || properties.getApiKey().isBlank()) {
            return "knowledge_unavailable: 내부 GitHub hybrid 검색이 비활성화되어 있어.";
        }

        String url = properties.getBaseUrl().replaceAll("/+$", "") + "/github/search";
        HttpHeaders headers = new HttpHeaders();
        headers.setContentType(MediaType.APPLICATION_JSON);
        headers.set("X-API-Key", properties.getApiKey());
        Map<String, Object> request = Map.of(
                "query", query.trim(),
                "top_k", properties.getTopK(),
                "min_score", properties.getMinScore()
        );
        try {
            Map<String, Object> body = hybridClient.exchange(
                    url,
                    HttpMethod.POST,
                    new HttpEntity<>(request, headers),
                    new ParameterizedTypeReference<Map<String, Object>>() {}
            ).getBody();
            return formatHybridResults(query.trim(), body);
        } catch (Exception e) {
            return "knowledge_unavailable: 내부 GitHub hybrid 검색에 실패했어. "
                    + e.getClass().getSimpleName();
        }
    }

    @Tool(
            name = "get_collected_github_trending",
            description = """
                    Airflow가 가장 최근에 수집한 GitHub Trending 스냅샷을 조회한다.
                    최근 인기 저장소, 주간 GitHub 동향, 새 프로젝트 추천 질문에 사용한다.
                    외부 API가 아니라 내부 수집 데이터와 수집일을 근거로 반환한다.
                    """
    )
    @Transactional(readOnly = true)
    public String getLatestTrending() {
        LocalDate latestDate = trendingRepository.findTopByOrderBySnapshotDateDescIdDesc()
                .map(GitHubTrending::getSnapshotDate)
                .orElse(null);
        if (latestDate == null) {
            return "knowledge_empty: 수집된 GitHub Trending 스냅샷이 없어.";
        }

        List<GitHubTrending> repos = trendingRepository
                .findBySnapshotDateOrderByStarsPeriodDesc(latestDate)
                .stream()
                .limit(MAX_TRENDING_RESULTS)
                .toList();
        if (repos.isEmpty()) {
            return "knowledge_empty: " + latestDate + " GitHub Trending 스냅샷이 비어 있어.";
        }

        StringBuilder out = new StringBuilder("collected_at: ").append(latestDate)
                .append("\nsource: internal github_trending snapshot");
        for (GitHubTrending repo : repos) {
            out.append("\n\n- ").append(repo.getRepoFullName());
            append(out, "description", repo.getDescription());
            append(out, "language", repo.getLanguage());
            append(out, "stars_total", repo.getStarsTotal());
            append(out, "stars_period", repo.getStarsPeriod());
            append(out, "url", repo.getRepoUrl());
        }
        return out.toString();
    }

    @Tool(
            name = "get_collected_github_repository",
            description = """
                    내부 GitHub 수집 데이터에서 정확한 owner/repository 이름의 최신 스냅샷과 README를 조회한다.
                    트렌딩 목록에 나온 저장소의 기능, 사용법, 특징을 실제 수집 README로 확인할 때 사용한다.
                    저장소 이름은 owner/repository 형식으로 전달한다.
                    """
    )
    @Transactional(readOnly = true)
    public String getCollectedRepository(
            @ToolParam(description = "정확한 GitHub 저장소 전체 이름 (owner/repository)")
            String repoFullName
    ) {
        if (repoFullName == null || repoFullName.isBlank() || !repoFullName.contains("/")) {
            return "tool_error: repo_full_name은 owner/repository 형식이어야 해.";
        }
        String canonicalName = repoFullName.trim();
        GitHubTrending snapshot = trendingRepository
                .findTopByRepoFullNameIgnoreCaseOrderBySnapshotDateDescIdDesc(canonicalName)
                .orElse(null);
        RepoReadmeCache readme = readmeRepository
                .findTopByRepoFullNameIgnoreCaseOrderByReadmeFetchedAtDescIdDesc(canonicalName)
                .orElse(null);

        if (snapshot == null && readme == null) {
            return "knowledge_empty: 내부 수집 데이터에서 " + canonicalName + " 저장소를 찾지 못했어.";
        }

        String resolvedName = snapshot != null ? snapshot.getRepoFullName() : readme.getRepoFullName();
        StringBuilder out = new StringBuilder("repository: ").append(resolvedName);
        if (snapshot != null) {
            append(out, "snapshot_date", snapshot.getSnapshotDate());
            append(out, "description", snapshot.getDescription());
            append(out, "language", snapshot.getLanguage());
            append(out, "stars_total", snapshot.getStarsTotal());
            append(out, "stars_period", snapshot.getStarsPeriod());
            append(out, "source", snapshot.getRepoUrl());
        }
        if (readme != null) {
            append(out, "readme_fetched_at", readme.getReadmeFetchedAt());
            if (readme.getSummaryKo() != null && !readme.getSummaryKo().isBlank()) {
                out.append("\nsummary_ko: ").append(readme.getSummaryKo().trim());
            }
            String text = readme.getReadmeText();
            if (text != null && !text.isBlank()) {
                if (text.length() > MAX_README_CHARS) {
                    text = text.substring(0, MAX_README_CHARS) + "\n...[truncated]";
                }
                out.append("\n\nREADME:\n").append(text);
            }
        }
        return out.toString();
    }

    private static void append(StringBuilder out, String label, Object value) {
        if (value != null && !String.valueOf(value).isBlank()) {
            out.append("\n").append(label).append(": ").append(value);
        }
    }

    private String formatHybridResults(String query, Map<String, Object> body) {
        if (body == null || !(body.get("results") instanceof List<?> results) || results.isEmpty()) {
            return "knowledge_empty: '" + query + "'와 관련된 수집 GitHub 저장소를 찾지 못했어.";
        }
        StringBuilder out = new StringBuilder("query: ").append(query)
                .append("\nsource: internal Qdrant github_readmes")
                .append("\nretrievers: ").append(body.getOrDefault("retrievers", List.of("bm25", "vector")))
                .append("\nfusion: ").append(body.getOrDefault("fusion", "rrf"));
        for (Object rawResult : results) {
            if (!(rawResult instanceof Map<?, ?> result)) continue;
            out.append("\n\n- repository: ").append(result.get("repo_full_name"));
            append(out, "url", result.get("repo_url"));
            append(out, "readme_fetched_at", result.get("readme_fetched_at"));
            append(out, "score", result.get("score"));
            if (result.get("chunks") instanceof List<?> chunks) {
                int evidenceNumber = 1;
                for (Object rawChunk : chunks) {
                    if (!(rawChunk instanceof Map<?, ?> chunk)) continue;
                    Object rawText = chunk.get("text");
                    String text = rawText == null ? "" : String.valueOf(rawText);
                    if (text.length() > 1_200) text = text.substring(0, 1_200) + "...";
                    out.append("\n  matched_by: ").append(chunk.get("matched_by"));
                    out.append("\n  evidence_").append(evidenceNumber++).append(": ").append(text);
                }
            }
        }
        return out.toString();
    }
}
