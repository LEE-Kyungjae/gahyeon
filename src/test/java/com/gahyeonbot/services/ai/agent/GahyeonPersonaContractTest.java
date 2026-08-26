package com.gahyeonbot.services.ai.agent;

import org.junit.jupiter.api.Test;
import org.springframework.core.io.ClassPathResource;

import java.nio.charset.StandardCharsets;

import static org.assertj.core.api.Assertions.assertThat;

class GahyeonPersonaContractTest {
    @Test
    void personaDefinesStableIdentityAdaptiveRelationshipAndGroundedKnowledgeUse() throws Exception {
        var resource = new ClassPathResource("prompts/characters/gahyeon.txt");
        String persona = new String(resource.getInputStream().readAllBytes(), StandardCharsets.UTF_8);

        assertThat(persona)
                .contains("하나의 지속적인 인격", "솔직하고 주관이 있다", "편안한 한국어 반말")
                .contains("친밀도가 낮을 때", "친밀도가 높아지면", "관계 수치나 내부 상태를 직접 읽어 주지 않는다")
                .contains("오래된 기억과 사용자의 현재 말이 충돌하면 현재 말을 우선")
                .contains("검색 결과에 없는 내용을 채워 넣지 않는다", "편안하게 침묵할 수 있다")
                .contains("의존을 유도하지 않는다", "질투, 집착, 복종, 위협을 친밀함으로 포장하지 않는다");
    }
}
