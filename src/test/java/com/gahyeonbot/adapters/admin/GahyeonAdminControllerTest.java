package com.gahyeonbot.adapters.admin;

import com.gahyeonbot.application.knowledge.KnowledgeBaseService;
import com.gahyeonbot.application.life.CharacterAutonomyWorkspaceService;
import com.gahyeonbot.application.privacy.MemoryGovernanceService;
import jakarta.servlet.http.HttpServletRequest;
import org.junit.jupiter.api.Test;
import org.springframework.jdbc.core.JdbcTemplate;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.*;

class GahyeonAdminControllerTest {
    @Test
    void authorizedKnowledgeIngestionDelegatesToTheScopedService() {
        var properties = new GahyeonAdminProperties();
        properties.setEnabled(true);
        properties.setToken("0123456789abcdef0123456789abcdef");
        var request = mock(HttpServletRequest.class);
        when(request.getHeader(GahyeonAdminAuthorization.TOKEN_HEADER)).thenReturn(properties.getToken());
        var knowledge = mock(KnowledgeBaseService.class);
        when(knowledge.ingest(any())).thenReturn(new KnowledgeBaseService.IngestionResult("document", 2, false));
        var controller = new GahyeonAdminController(new GahyeonAdminAuthorization(properties), knowledge,
                mock(MemoryGovernanceService.class), mock(CharacterAutonomyWorkspaceService.class),
                mock(JdbcTemplate.class));

        var result = controller.ingest(new GahyeonAdminController.KnowledgeIngestBody(
                "gahyeon", "zezestudio:user", "manual", "운영자", null,
                KnowledgeBaseService.AccessScope.PRIVATE, "제목", "ko", "본문", "{}"), request);

        assertThat(result.documentId()).isEqualTo("document");
        verify(knowledge).ingest(argThat(body -> body.serviceId().equals("gahyeon")
                && body.ownerSubjectId().equals("zezestudio:user")
                && body.accessScope() == KnowledgeBaseService.AccessScope.PRIVATE));
    }
}
