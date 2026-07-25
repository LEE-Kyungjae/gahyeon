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

/**
 * 내부 paper-rag query API를 통해 Qdrant hf_papers 지식을 검색합니다.
 */
@Component
public class PaperKnowledgeTools {

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
        if (query == null || query.isBlank()) {
            return "tool_error: 논문 검색 query가 필요해.";
        }
        if (!properties.isEnabled()) {
            return "knowledge_unavailable: 내부 HF Papers 검색이 비활성화되어 있어.";
        }
        if (properties.getApiKey() == null || properties.getApiKey().isBlank()) {
            return "knowledge_unavailable: 내부 HF Papers 검색 인증이 설정되지 않았어.";
        }

        String url = properties.getBaseUrl().replaceAll("/+$", "") + "/search";
        HttpHeaders headers = new HttpHeaders();
        headers.setContentType(MediaType.APPLICATION_JSON);
        headers.set("X-API-Key", properties.getApiKey());
        Map<String, Object> request = Map.of(
                "query", query.trim(),
                "top_k", properties.getTopK(),
                "min_score", properties.getMinScore()
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
                .append("\nembedding_model: ").append(body.getOrDefault("embedding_model", "unknown"));
        for (Object rawResult : results) {
            if (!(rawResult instanceof Map<?, ?> result)) continue;
            out.append("\n\n- arxiv_id: ").append(result.get("arxiv_id"));
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

    private static void append(StringBuilder out, String label, Object value) {
        if (value != null && !String.valueOf(value).isBlank()) {
            out.append("\n  ").append(label).append(": ").append(value);
        }
    }

    private static RestTemplate createClient(PaperRagProperties properties) {
        SimpleClientHttpRequestFactory factory = new SimpleClientHttpRequestFactory();
        factory.setConnectTimeout(properties.getConnectTimeoutMs());
        factory.setReadTimeout(properties.getReadTimeoutMs());
        return new RestTemplate(factory);
    }
}
