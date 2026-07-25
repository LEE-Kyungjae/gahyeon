package com.gahyeonbot.services.ai;

import org.junit.jupiter.api.Test;
import org.springframework.ai.support.ToolCallbacks;
import org.springframework.http.HttpMethod;
import org.springframework.http.MediaType;
import org.springframework.test.web.client.MockRestServiceServer;
import org.springframework.web.client.RestTemplate;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.client.ExpectedCount.once;
import static org.springframework.test.web.client.match.MockRestRequestMatchers.header;
import static org.springframework.test.web.client.match.MockRestRequestMatchers.jsonPath;
import static org.springframework.test.web.client.match.MockRestRequestMatchers.method;
import static org.springframework.test.web.client.match.MockRestRequestMatchers.requestTo;
import static org.springframework.test.web.client.response.MockRestResponseCreators.withSuccess;

class PaperKnowledgeToolsTest {

    @Test
    void searchesInternalQdrantThroughAuthenticatedQueryApi() {
        PaperRagProperties properties = properties(true, "secret");
        RestTemplate client = new RestTemplate();
        MockRestServiceServer server = MockRestServiceServer.bindTo(client).build();
        server.expect(once(), requestTo("http://paper-rag.internal:8765/search"))
                .andExpect(method(HttpMethod.POST))
                .andExpect(header("X-API-Key", "secret"))
                .andExpect(jsonPath("$.query").value("agent memory"))
                .andExpect(jsonPath("$.top_k").value(5))
                .andExpect(jsonPath("$.prefer_recent").value(false))
                .andRespond(withSuccess("""
                        {
                          "embedding_model": "intfloat/multilingual-e5-large",
                          "results": [{
                            "arxiv_id": "2607.12345",
                            "date": "20260725",
                            "score": 0.82,
                            "source_url": "https://arxiv.org/abs/2607.12345",
                            "chunks": [{"chunk": 1, "score": 0.82, "text": "grounded evidence"}]
                          }]
                        }
                        """, MediaType.APPLICATION_JSON));

        String result = new PaperKnowledgeTools(properties, client).searchPapers("agent memory");

        assertThat(result)
                .contains("source: internal Qdrant hf_papers")
                .contains("intfloat/multilingual-e5-large")
                .contains("2607.12345")
                .contains("grounded evidence")
                .contains("https://arxiv.org/abs/2607.12345");
        server.verify();
    }

    @Test
    void retrievesExactPaperByArxivId() {
        PaperRagProperties properties = properties(true, "secret");
        RestTemplate client = new RestTemplate();
        MockRestServiceServer server = MockRestServiceServer.bindTo(client).build();
        server.expect(once(), requestTo("http://paper-rag.internal:8765/papers/2501.19393"))
                .andExpect(method(HttpMethod.GET))
                .andExpect(header("X-API-Key", "secret"))
                .andRespond(withSuccess("""
                        {
                          "arxiv_id": "2501.19393",
                          "date": "20250131",
                          "source_url": "https://arxiv.org/abs/2501.19393",
                          "chunks": [{"chunk": 0, "text": "s1: Simple test-time scaling"}]
                        }
                        """, MediaType.APPLICATION_JSON));

        String result = new PaperKnowledgeTools(properties, client)
                .getPaperByArxivId("arXiv:2501.19393");

        assertThat(result)
                .contains("exact_match: true")
                .contains("retrieved_paper_arxiv_id: 2501.19393")
                .contains("s1: Simple test-time scaling");
        server.verify();
    }

    @Test
    void reportsUnavailableWithoutCallingNetworkWhenDisabled() {
        PaperKnowledgeTools tools = new PaperKnowledgeTools(properties(false, "secret"), new RestTemplate());

        assertThat(tools.searchPapers("RAG"))
                .startsWith("knowledge_unavailable:");
    }

    @Test
    void reportsUnavailableWhenAuthenticationIsMissing() {
        PaperKnowledgeTools tools = new PaperKnowledgeTools(properties(true, ""), new RestTemplate());

        assertThat(tools.searchPapers("RAG"))
                .contains("인증이 설정되지 않았어");
    }

    @Test
    void springAiDiscoversPaperSearchTool() {
        PaperKnowledgeTools tools = new PaperKnowledgeTools(properties(false, ""), new RestTemplate());

        assertThat(ToolCallbacks.from(tools))
                .extracting(callback -> callback.getToolDefinition().name())
                .containsExactlyInAnyOrder(
                        "search_collected_ai_papers",
                        "search_recent_collected_ai_papers",
                        "get_collected_ai_paper_by_arxiv_id");
    }

    private PaperRagProperties properties(boolean enabled, String apiKey) {
        PaperRagProperties properties = new PaperRagProperties();
        properties.setEnabled(enabled);
        properties.setBaseUrl("http://paper-rag.internal:8765");
        properties.setApiKey(apiKey);
        properties.setTopK(5);
        properties.setMinScore(0.35);
        return properties;
    }
}
