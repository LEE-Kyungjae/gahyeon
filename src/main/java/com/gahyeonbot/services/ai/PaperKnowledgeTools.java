package com.gahyeonbot.services.ai;

import org.springframework.ai.tool.annotation.Tool;
import org.springframework.ai.tool.annotation.ToolParam;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.core.ParameterizedTypeReference;
import org.springframework.http.HttpEntity;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpMethod;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.http.client.SimpleClientHttpRequestFactory;
import org.springframework.stereotype.Component;
import org.springframework.web.client.RestTemplate;

import java.util.List;
import java.util.Map;
import java.util.regex.Pattern;

/**
 * 내부 paper-rag query API를 통해 Qdrant hf_papers 지식을 검색합니다.
 */
@Component
public class PaperKnowledgeTools {
    private static final Pattern ARXIV_ID = Pattern.compile("\\d{4}\\.\\d{4,5}(?:v\\d+)?");

    private final PaperRagProperties properties;
    private final RestTemplate client;

    @Autowired
    public PaperKnowledgeTools(PaperRagProperties properties) {
        this(properties, createClient(properties));
    }

    PaperKnowledgeTools(PaperRagProperties properties, RestTemplate client) {
        this.properties = properties;
        this.client = client;
    }

    @Tool(
            name = "search_collected_ai_papers",
            description = """
                    내부에서 수집·임베딩한 Hugging Face Papers/ArXiv 논문 원문을 의미 검색한다.
                    AI 연구, 모델, 기법, 논문 근거 또는 GitHub 트렌드와 관련된 연구를 찾을 때 사용한다.
                    외부 웹 검색이 아니라 multilingual-e5-large와 Qdrant hf_papers 컬렉션을 사용한다.
                    """
    )
    public String searchPapers(
            @ToolParam(description = "찾으려는 연구 주제나 자연어 질문. 독립적으로 이해 가능한 검색 질의")
            String query
    ) {
        return search(query, false);
    }

    @Tool(
            name = "search_recent_collected_ai_papers",
            description = """
                    내부 HF Papers 컬렉션에서 주제와 관련된 논문 후보를 찾고 날짜가 최신인 순서로 반환한다.
                    사용자가 최신·최근·요즘 논문을 요청할 때 일반 의미 검색 대신 사용한다.
                    반환된 수집 날짜가 현재 시점보다 오래됐다면 최신 자료라고 단정하지 않는다.
                    """
    )
    public String searchRecentPapers(
            @ToolParam(description = "찾으려는 AI 연구 주제. 'latest' 같은 시간 표현보다 구체적인 연구 주제를 포함")
            String query
    ) {
        return search(query, true);
    }

    @Tool(
            name = "get_collected_ai_paper_by_arxiv_id",
            description = """
                    arXiv ID와 정확히 일치하는 수집 논문을 조회한다.
                    특정 arXiv ID의 내용·제목·방법을 확인하거나 검색 후보를 검증할 때 사용한다.
                    의미 검색으로 ID를 추측하지 말고 이 도구의 exact_match 결과만 근거로 사용한다.
                    """
    )
    public String getPaperByArxivId(
            @ToolParam(description = "정확한 arXiv ID. 예: 2501.19393")
            String arxivId
    ) {
        String normalized = normalizeArxivId(arxivId);
        if (normalized == null) {
            return "tool_error: 올바른 arXiv ID가 필요해. 예: 2501.19393";
        }
        String unavailable = availabilityError();
        if (unavailable != null) return unavailable;

        String url = properties.getBaseUrl().replaceAll("/+$", "") + "/papers/" + normalized;
        HttpHeaders headers = new HttpHeaders();
        headers.set("X-API-Key", properties.getApiKey());
        try {
            ResponseEntity<Map<String, Object>> response = client.exchange(
                    url,
                    HttpMethod.GET,
                    new HttpEntity<>(headers),
                    new ParameterizedTypeReference<>() {}
            );
            return formatExactResponse(normalized, response.getBody());
        } catch (org.springframework.web.client.HttpClientErrorException.NotFound e) {
            return "knowledge_empty: arXiv " + normalized + " 논문이 내부 컬렉션에 없어.";
        } catch (Exception e) {
            return "knowledge_unavailable: arXiv ID 정확 조회에 실패했어. "
                    + e.getClass().getSimpleName();
        }
    }

    private String search(String query, boolean preferRecent) {
        if (query == null || query.isBlank()) {
            return "tool_error: 논문 검색 query가 필요해.";
        }
        String unavailable = availabilityError();
        if (unavailable != null) return unavailable;

        String url = properties.getBaseUrl().replaceAll("/+$", "") + "/search";
        HttpHeaders headers = new HttpHeaders();
        headers.setContentType(MediaType.APPLICATION_JSON);
        headers.set("X-API-Key", properties.getApiKey());
        Map<String, Object> request = Map.of(
                "query", query.trim(),
                "top_k", properties.getTopK(),
                "min_score", properties.getMinScore(),
                "prefer_recent", preferRecent
        );
        try {
            ResponseEntity<Map<String, Object>> response = client.exchange(
                    url,
                    HttpMethod.POST,
                    new HttpEntity<>(request, headers),
                    new ParameterizedTypeReference<>() {}
            );
            return formatResponse(query.trim(), response.getBody());
        } catch (Exception e) {
            return "knowledge_unavailable: 내부 HF Papers 검색에 실패했어. "
                    + e.getClass().getSimpleName();
        }
    }

    private String formatResponse(String query, Map<String, Object> body) {
        if (body == null || !(body.get("results") instanceof List<?> results) || results.isEmpty()) {
            return "knowledge_empty: '" + query + "'와 관련된 수집 논문을 찾지 못했어.";
        }
        StringBuilder out = new StringBuilder("query: ").append(query)
                .append("\nsource: internal Qdrant hf_papers")
                .append("\nembedding_model: ").append(body.getOrDefault("embedding_model", "unknown"))
                .append("\nranking: ").append(body.getOrDefault("ranking", "semantic"))
                .append("\nwarning: evidence는 retrieved_paper의 PDF 청크이며, 청크 안의 참고문헌은 별도 논문이다.");
        for (Object rawResult : results) {
            if (!(rawResult instanceof Map<?, ?> result)) continue;
            out.append("\n\n- retrieved_paper_arxiv_id: ").append(result.get("arxiv_id"));
            append(out, "date", result.get("date"));
            append(out, "score", result.get("score"));
            append(out, "source_url", result.get("source_url"));
            if (result.get("chunks") instanceof List<?> chunks) {
                int evidenceNumber = 1;
                for (Object rawChunk : chunks) {
                    if (!(rawChunk instanceof Map<?, ?> chunk)) continue;
                    Object rawText = chunk.get("text");
                    String text = rawText == null ? "" : String.valueOf(rawText);
                    if (text.length() > 1_800) text = text.substring(0, 1_800) + "...";
                    out.append("\n  evidence_").append(evidenceNumber++).append(": ").append(text);
                }
            }
        }
        return out.toString();
    }

    private String formatExactResponse(String arxivId, Map<String, Object> body) {
        if (body == null) {
            return "knowledge_empty: arXiv " + arxivId + " 논문을 찾지 못했어.";
        }
        StringBuilder out = new StringBuilder("exact_match: true")
                .append("\nretrieved_paper_arxiv_id: ").append(arxivId);
        append(out, "date", body.get("date"));
        append(out, "source_url", body.get("source_url"));
        out.append("\nwarning: 아래 내용은 이 arXiv ID에 정확히 연결된 PDF 앞부분이다.");
        if (body.get("chunks") instanceof List<?> chunks) {
            int evidenceNumber = 1;
            for (Object rawChunk : chunks) {
                if (!(rawChunk instanceof Map<?, ?> chunk)) continue;
                Object rawText = chunk.get("text");
                String text = rawText == null ? "" : String.valueOf(rawText);
                if (text.length() > 2_400) text = text.substring(0, 2_400) + "...";
                out.append("\n  exact_evidence_").append(evidenceNumber++).append(": ").append(text);
            }
        }
        return out.toString();
    }

    private String availabilityError() {
        if (!properties.isEnabled()) {
            return "knowledge_unavailable: 내부 HF Papers 검색이 비활성화되어 있어.";
        }
        if (properties.getApiKey() == null || properties.getApiKey().isBlank()) {
            return "knowledge_unavailable: 내부 HF Papers 검색 인증이 설정되지 않았어.";
        }
        return null;
    }

    private static String normalizeArxivId(String value) {
        if (value == null) return null;
        String normalized = value.trim().toLowerCase().replaceFirst("^arxiv:", "");
        return ARXIV_ID.matcher(normalized).matches() ? normalized : null;
    }

    private static void append(StringBuilder out, String label, Object value) {
        if (value != null && !String.valueOf(value).isBlank()) {
            out.append("\n  ").append(label).append(": ").append(value);
        }
    }

    static RestTemplate createClient(PaperRagProperties properties) {
        return createClient(properties.getConnectTimeoutMs(), properties.getReadTimeoutMs());
    }

    static RestTemplate createClient(int connectTimeoutMs, int readTimeoutMs) {
        SimpleClientHttpRequestFactory factory = new SimpleClientHttpRequestFactory();
        factory.setConnectTimeout(connectTimeoutMs);
        factory.setReadTimeout(readTimeoutMs);
        return new RestTemplate(factory);
    }
}
