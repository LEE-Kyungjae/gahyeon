package com.gahyeonbot.services.ai;

import com.gahyeonbot.entity.GitHubTrending;
import com.gahyeonbot.entity.RepoReadmeCache;
import com.gahyeonbot.repository.GitHubTrendingRepository;
import com.gahyeonbot.repository.RepoReadmeCacheRepository;
import lombok.RequiredArgsConstructor;
import org.springframework.ai.tool.annotation.Tool;
import org.springframework.ai.tool.annotation.ToolParam;
import org.springframework.stereotype.Component;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDate;
import java.util.List;

/**
 * Airflow가 수집한 GitHub 스냅샷과 README 캐시를 조회하는 에이전트 도구.
 *
 * 외부 GitHub API를 다시 호출하지 않으며, 수집 파이프라인이 PostgreSQL에
 * 저장한 데이터만 근거로 반환합니다.
 */
@Component
@RequiredArgsConstructor
public class GitHubKnowledgeTools {

    private static final int MAX_TRENDING_RESULTS = 15;
    private static final int MAX_README_CHARS = 10_000;

    private final GitHubTrendingRepository trendingRepository;
    private final RepoReadmeCacheRepository readmeRepository;

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
}
