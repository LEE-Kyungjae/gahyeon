package com.gahyeonbot.adapters.admin;

import com.gahyeonbot.application.knowledge.*;
import org.junit.jupiter.api.Test;
import org.springframework.http.MediaType;
import org.springframework.test.web.servlet.setup.MockMvcBuilders;

import java.util.List;

import static org.mockito.Mockito.*;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.*;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.*;

class OntologyAdminControllerTest {
    private static final String TOKEN = "test-only-ontology-admin-token-000000";

    @Test void everyEndpointRequiresExistingAdminAuthorityBeforeServiceCalls() throws Exception {
        var properties = properties(true);
        var ingestion = mock(OntologyIngestionService.class);
        var graph = mock(OntologyGraphService.class);
        var rag = mock(OntologyRagService.class);
        var mvc = MockMvcBuilders.standaloneSetup(new OntologyAdminController(
                new GahyeonAdminAuthorization(properties), ingestion, graph, rag)).build();
        mvc.perform(get("/admin/gahyeon/ontology/schema")).andExpect(status().isUnauthorized());
        mvc.perform(post("/admin/gahyeon/ontology/ingest").contentType(MediaType.APPLICATION_JSON)
                .content("{\"document\":null,\"ontology\":null}")).andExpect(status().isUnauthorized());
        mvc.perform(post("/admin/gahyeon/ontology/documents/id").contentType(MediaType.APPLICATION_JSON)
                .content("{\"serviceId\":\"gahyeon\",\"ontology\":null}")).andExpect(status().isUnauthorized());
        mvc.perform(post("/admin/gahyeon/ontology/graph/search").contentType(MediaType.APPLICATION_JSON)
                .content("{\"serviceId\":\"gahyeon\",\"query\":\"새벽\",\"limit\":5,\"maxHops\":2}"))
                .andExpect(status().isUnauthorized());
        mvc.perform(post("/admin/gahyeon/ontology/search").contentType(MediaType.APPLICATION_JSON)
                .content("{\"serviceId\":\"gahyeon\",\"query\":\"새벽\",\"limit\":5}"))
                .andExpect(status().isUnauthorized());
        verifyNoInteractions(ingestion, graph, rag);
    }

    @Test void disabledAdministrationRemainsUnavailable() throws Exception {
        var mvc = MockMvcBuilders.standaloneSetup(new OntologyAdminController(
                new GahyeonAdminAuthorization(properties(false)), mock(OntologyIngestionService.class),
                mock(OntologyGraphService.class), mock(OntologyRagService.class))).build();
        mvc.perform(get("/admin/gahyeon/ontology/schema").header(GahyeonAdminAuthorization.TOKEN_HEADER, TOKEN))
                .andExpect(status().isNotFound());
    }

    @Test void authorizedSearchPreservesExplicitSubjectAndReturnsSchema() throws Exception {
        var rag = mock(OntologyRagService.class);
        var request = new KnowledgeBaseService.SearchRequest("gahyeon", "user-a", "새벽", 5);
        when(rag.search(request)).thenReturn(new OntologyRagService.Result(List.of(), true, false));
        var mvc = MockMvcBuilders.standaloneSetup(new OntologyAdminController(
                new GahyeonAdminAuthorization(properties(true)), mock(OntologyIngestionService.class),
                mock(OntologyGraphService.class), rag)).build();
        mvc.perform(get("/admin/gahyeon/ontology/schema").header(GahyeonAdminAuthorization.TOKEN_HEADER, TOKEN))
                .andExpect(status().isOk()).andExpect(jsonPath("$.schemaVersion").value(1));
        mvc.perform(post("/admin/gahyeon/ontology/search").header(GahyeonAdminAuthorization.TOKEN_HEADER, TOKEN)
                .contentType(MediaType.APPLICATION_JSON)
                .content("{\"serviceId\":\"gahyeon\",\"subjectId\":\"user-a\",\"query\":\"새벽\",\"limit\":5}"))
                .andExpect(status().isOk()).andExpect(jsonPath("$.graphEnabled").value(true));
        verify(rag).search(request);
    }

    private static GahyeonAdminProperties properties(boolean enabled) {
        var properties = new GahyeonAdminProperties();
        properties.setEnabled(enabled);
        properties.setToken(TOKEN);
        return properties;
    }
}
