package com.gahyeonbot.services.ai;

import com.gahyeonbot.entity.GitHubTrending;
import com.gahyeonbot.entity.RepoReadmeCache;
import com.gahyeonbot.repository.GitHubTrendingRepository;
import com.gahyeonbot.repository.RepoReadmeCacheRepository;
import lombok.RequiredArgsConstructor;
import org.springframework.ai.tool.annotation.Tool;
import org.springframework.core.ParameterizedTypeReference;
import org.springframework.http.HttpMethod;
import org.springframework.http.ResponseEntity;
import org.springframework.http.client.SimpleClientHttpRequestFactory;
import org.springframework.stereotype.Component;
import org.springframework.web.client.RestTemplate;

import java.util.Map;

/**
 * 내부 지식의 마지막 수집 시각과 검색 인덱스 상태를 노출합니다.
 */
@Component
@RequiredArgsConstructor
public class KnowledgeFreshnessTools {

    private final GitHubTrendingRepository trendingRepository;
    private final RepoReadmeCacheRepository readmeRepository;
    private final PaperRagProperties paperRagProperties;
    private final RestTemplate healthClient = createHealthClient();

    @Tool(
            name = "get_internal_knowledge_freshness",
            description = """
                    내부 GitHub 수집 데이터와 HF Papers Qdrant 인덱스의 최신 상태를 확인한다.
                    사용자가 '최신', '오늘', 수집 기준일을 강조하거나 검색 결과가 비어 있을 때 사용한다.
                    """
    )
    public String getFreshness() {
        String githubSnapshot = trendingRepository.findTopByOrderBySnapshotDateDescIdDesc()
                .map(GitHubTrending::getSnapshotDate)
                .map(String::valueOf)
                .orElse("none");
        String readmeFetchedAt = readmeRepository.findTopByOrderByReadmeFetchedAtDescIdDesc()
                .map(RepoReadmeCache::getReadmeFetchedAt)
                .map(String::valueOf)
                .orElse("none");

        String paperStatus;
        if (!paperRagProperties.isEnabled()) {
            paperStatus = "disabled";
        } else {
            try {
                String url = paperRagProperties.getBaseUrl().replaceAll("/+$", "") + "/health";
                ResponseEntity<Map<String, Object>> response = healthClient.exchange(
                        url, HttpMethod.GET, null, new ParameterizedTypeReference<>() {});
                Map<String, Object> body = response.getBody();
                paperStatus = body == null
                        ? "unknown"
                        : "status=%s, collection=%s, points=%s".formatted(
                                body.get("status"), body.get("collection"), body.get("points"));
            } catch (Exception e) {
                paperStatus = "unavailable(" + e.getClass().getSimpleName() + ")";
            }
        }

        return """
                github_trending_snapshot: %s
                github_readme_fetched_at: %s
                hf_papers: %s
                """.formatted(githubSnapshot, readmeFetchedAt, paperStatus).trim();
    }

    private static RestTemplate createHealthClient() {
        SimpleClientHttpRequestFactory factory = new SimpleClientHttpRequestFactory();
        factory.setConnectTimeout(2_000);
        factory.setReadTimeout(5_000);
        return new RestTemplate(factory);
    }
}
