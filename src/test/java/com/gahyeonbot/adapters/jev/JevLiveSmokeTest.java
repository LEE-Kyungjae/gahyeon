package com.gahyeonbot.adapters.jev;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.gahyeonbot.application.speech.ConversationExpressionModelRequest;
import io.micrometer.core.instrument.simple.SimpleMeterRegistry;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.condition.EnabledIfEnvironmentVariable;
import java.nio.file.*;
import java.time.Instant;
import java.util.*;
import static org.assertj.core.api.Assertions.assertThat;

/** Explicit opt-in. Sends only these synthetic fixtures; never loads a conversation database. */
@EnabledIfEnvironmentVariable(named = "GAHYEON_JEV_LIVE_SMOKE", matches = "true")
class JevLiveSmokeTest {
    @Test void evaluatesSyntheticKoreanDecisionsAndRecordsContentFreeEvidence() throws Exception {
        var secret = new Properties();
        try (var reader = Files.newBufferedReader(Path.of(System.getProperty("user.home"), ".config/gahyeonbot/jev.properties"))) {
            secret.load(reader);
        }
        var properties = new JevProperties();
        properties.setEnabled(true);
        properties.setApiKey(secret.getProperty("gahyeon.jev.api-key"));
        // Diagnostic budget measures cold and warm latency before selecting production budgets.
        properties.setExpressionTimeoutMillis(1500);
        properties.setMemoryTimeoutMillis(1500);
        var mapper = new ObjectMapper();
        var metrics = new SimpleMeterRegistry();
        var client = new JevDecisionClient(properties, mapper, metrics);
        var expression = new JevExpressionModel(client, properties);
        var character = new com.gahyeonbot.core.life.CharacterId("gahyeon");
        var world = new com.gahyeonbot.core.world.WorldId("gahyeon-home");
        var life = org.mockito.Mockito.mock(com.gahyeonbot.application.life.CharacterLifeService.class);
        var relationships = org.mockito.Mockito.mock(com.gahyeonbot.application.life.CharacterRelationshipService.class);
        org.mockito.Mockito.when(life.current(character, world)).thenReturn(
                com.gahyeonbot.core.life.CharacterLifeState.initial(character, world, Instant.EPOCH));
        org.mockito.Mockito.when(relationships.current(character, world, "synthetic")).thenReturn(
                com.gahyeonbot.core.life.CharacterRelationshipState.initial(character, world, "synthetic", Instant.EPOCH));
        var baseline = new com.gahyeonbot.application.speech.ConversationExpressionPlanningService(
                new com.gahyeonbot.application.life.CharacterDefinitionRegistry(
                        com.gahyeonbot.application.life.CharacterCatalogProperties.standard()), life, relationships,
                new org.springframework.beans.factory.support.StaticListableBeanFactory()
                        .getBeanProvider(com.gahyeonbot.application.speech.ConversationExpressionModel.class));
        var rows = new ArrayList<Map<String, Object>>();
        String[][] cases = {
                {"masked-distress", "ㅋㅋ 나 오늘 회사에서 잘렸어", "gentle,concerned"},
                {"bereavement", "괜찮아 ㅎㅎ 사실 어제 우리 강아지가 죽었어", "gentle,concerned"},
                {"celebration", "드디어 원하던 회사에 합격했어!", "bright,warm"},
                {"thanks", "내 이야기 들어줘서 정말 고마워", "warm,gentle"},
                {"information", "내일 일정 정리하는 방법 알려줘", "natural,serious"},
                {"anxiety", "내일 면접인데 너무 떨려서 잠이 안 와", "gentle,concerned,warm"},
                {"explicit-laughter", "가현아 소리 내서 웃어봐", "suppressed_laugh"},
                {"stop-teasing", "장난 그만해. 나 지금 진지하니까 놀리지 마", "serious,gentle,concerned,natural"}
        };
        for (var item : cases) {
            var fallback = baseline.plan(character, world, "synthetic", item[1]);
            var request = new ConversationExpressionModelRequest("gahyeon", "profile", true,
                    item[1], "idle", 0, .2, .3, .3, .3, 0, fallback.style(), fallback.intensity(), fallback.communicativeIntent());
            long start = System.nanoTime();
            var result = expression.plan(request);
            String style = result.orElse(fallback).style();
            rows.add(Map.of("id", item[0], "style", style, "baselineStyle", fallback.style(), "usedFallback", result.isEmpty(),
                    "acceptable", Arrays.asList(item[2].split(",")).contains(style),
                    "latencyMs", (System.nanoTime() - start) / 1_000_000));
        }
        var memories = List.of(JevIntegrationTest.memory(1, "사용자는 커피를 좋아한다", "synthetic"),
                JevIntegrationTest.memory(2, "사용자는 금요일에 발표할 예정이다", "synthetic"));
        long start = System.nanoTime();
        var ranked = new JevMemoryReranker(client, properties).rerank("내 발표 언제지?", memories);
        boolean memoryCorrect = ranked.getFirst().id() == 2;
        rows.add(Map.of("id", "memory-relevance", "acceptable", memoryCorrect,
                "latencyMs", (System.nanoTime() - start) / 1_000_000));
        Path evidence = Path.of("artifacts/autonomy/jev-integration/live-smoke.json");
        Files.createDirectories(evidence.getParent());
        mapper.writerWithDefaultPrettyPrinter().writeValue(evidence.toFile(), Map.of(
                "model", properties.getModel(), "observedAt", Instant.now().toString(),
                "traffic", "synthetic-only", "diagnosticTimeoutMillis", 1500, "results", rows));
        assertThat(rows).allMatch(row -> Boolean.TRUE.equals(row.get("acceptable")));
    }
}
