package com.gahyeonbot.services.ai;

import com.gahyeonbot.entity.RepoReadmeCache;
import com.gahyeonbot.repository.RepoReadmeCacheRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.core.ParameterizedTypeReference;
import org.springframework.http.HttpEntity;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpMethod;
import org.springframework.http.MediaType;
import org.springframework.scheduling.annotation.Async;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Service;
import org.springframework.web.client.RestTemplate;

import java.util.ArrayList;
import java.util.Comparator;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/**
 * PostgreSQL README 캐시의 최신 revision을 내부 Qdrant hybrid index로 동기화합니다.
 */
@Service
@RequiredArgsConstructor
@Slf4j
public class GitHubReadmeIndexSyncService {

    private final RepoReadmeCacheRepository readmeRepository;
    private final PaperRagProperties properties;

    @Async
    @Scheduled(
            initialDelayString = "${paper-rag.github-sync-initial-delay-ms:120000}",
            fixedDelayString = "${paper-rag.github-sync-fixed-delay-ms:21600000}"
    )
    public void syncLatestReadmes() {
        if (!properties.isEnabled() || !properties.isGithubSyncEnabled()) {
            return;
        }
        if (properties.getApiKey() == null || properties.getApiKey().isBlank()) {
            log.warn("GitHub README index 동기화 생략: 내부 검색 API 키가 없습니다.");
            return;
        }

        Map<String, RepoReadmeCache> latestByRepository = new LinkedHashMap<>();
        readmeRepository.findAll().stream()
                .sorted(Comparator.comparing(RepoReadmeCache::getReadmeFetchedAt).reversed())
                .forEach(readme -> latestByRepository.putIfAbsent(
                        readme.getRepoFullName().toLowerCase(), readme));
        if (latestByRepository.isEmpty()) {
            log.info("GitHub README index 동기화 생략: 캐시가 비어 있습니다.");
            return;
        }

        List<RepoReadmeCache> readmes = new ArrayList<>(latestByRepository.values());
        int batchSize = Math.max(1, Math.min(properties.getGithubSyncBatchSize(), 50));
        int indexed = 0;
        int unchanged = 0;
        try {
            for (int start = 0; start < readmes.size(); start += batchSize) {
                int end = Math.min(start + batchSize, readmes.size());
                boolean finalize = end == readmes.size();
                Map<String, Object> result = sendBatch(readmes.subList(start, end), finalize);
                if (result == null) {
                    result = Map.of();
                }
                indexed += number(result.get("indexed_documents"));
                unchanged += number(result.get("unchanged_documents"));
            }
            log.info("GitHub README hybrid index 동기화 완료 - 전체: {}, 변경: {}, 동일: {}",
                    readmes.size(), indexed, unchanged);
        } catch (Exception e) {
            log.error("GitHub README hybrid index 동기화 실패 - 처리: {}/{}",
                    indexed + unchanged, readmes.size(), e);
        }
    }

    private Map<String, Object> sendBatch(List<RepoReadmeCache> readmes, boolean finalize) {
        String url = properties.getBaseUrl().replaceAll("/+$", "") + "/github/index";
        HttpHeaders headers = new HttpHeaders();
        headers.setContentType(MediaType.APPLICATION_JSON);
        headers.set("X-API-Key", properties.getApiKey());
        List<Map<String, Object>> documents = readmes.stream()
                .map(readme -> {
                    Map<String, Object> document = new LinkedHashMap<>();
                    document.put("repo_full_name", readme.getRepoFullName());
                    document.put("repo_url", readme.getRepoUrl());
                    document.put("readme_sha", readme.getReadmeSha());
                    document.put("readme_text", readme.getReadmeText());
                    if (readme.getReadmeFetchedAt() != null) {
                        document.put("readme_fetched_at", readme.getReadmeFetchedAt().toString());
                    }
                    return document;
                })
                .toList();
        RestTemplate client = PaperKnowledgeTools.createClient(
                properties.getConnectTimeoutMs(),
                Math.max(properties.getReadTimeoutMs(), 120_000));
        return client.exchange(
                url,
                HttpMethod.POST,
                new HttpEntity<>(Map.of("documents", documents, "finalize", finalize), headers),
                new ParameterizedTypeReference<Map<String, Object>>() {}
        ).getBody();
    }

    private static int number(Object value) {
        return value instanceof Number number ? number.intValue() : 0;
    }
}
