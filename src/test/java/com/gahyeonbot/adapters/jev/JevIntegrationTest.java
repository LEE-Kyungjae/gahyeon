package com.gahyeonbot.adapters.jev;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.gahyeonbot.adapters.speech.SmallConversationExpressionModelConfiguration;
import com.gahyeonbot.application.speech.*;
import com.gahyeonbot.core.life.*;
import com.gahyeonbot.core.world.WorldId;
import com.sun.net.httpserver.HttpServer;
import io.micrometer.core.instrument.simple.SimpleMeterRegistry;
import org.junit.jupiter.api.*;
import org.springframework.boot.test.context.runner.ApplicationContextRunner;
import java.net.*;
import java.net.http.HttpClient;
import java.time.Instant;
import java.util.*;
import java.util.concurrent.atomic.AtomicInteger;
import java.util.concurrent.atomic.AtomicReference;
import static org.assertj.core.api.Assertions.assertThat;

class JevIntegrationTest {
    private final ObjectMapper mapper = new ObjectMapper();
    private final JevProperties properties = new JevProperties();
    private final SimpleMeterRegistry metrics = new SimpleMeterRegistry();
    private final AtomicReference<String> response = new AtomicReference<>();
    private final AtomicReference<String> received = new AtomicReference<>();
    private final AtomicInteger calls = new AtomicInteger();
    private HttpServer server;
    private JevDecisionClient client;
    private int status = 200;
    private long delay;

    @BeforeEach void setup() throws Exception {
        properties.setEnabled(true);
        properties.setApiKey("synthetic-test-key");
        properties.setExpressionTimeoutMillis(1000);
        properties.setMemoryTimeoutMillis(1000);
        server = HttpServer.create(new InetSocketAddress("127.0.0.1", 0), 0);
        server.createContext("/", exchange -> {
            calls.incrementAndGet();
            received.set(new String(exchange.getRequestBody().readAllBytes(), java.nio.charset.StandardCharsets.UTF_8));
            try { Thread.sleep(delay); } catch (InterruptedException e) { Thread.currentThread().interrupt(); }
            byte[] bytes = response.get().getBytes(java.nio.charset.StandardCharsets.UTF_8);
            exchange.sendResponseHeaders(status, bytes.length);
            try (var out = exchange.getResponseBody()) { out.write(bytes); }
        });
        server.start();
        client = new JevDecisionClient(properties, mapper, metrics, HttpClient.newHttpClient(),
                URI.create("http://127.0.0.1:" + server.getAddress().getPort() + "/"));
    }

    @AfterEach void cleanup() { server.stop(0); metrics.close(); }

    @Test void selectsCompassionateExpressionWithoutSendingIdentityOrHistory() throws Exception {
        response.set(choice("gentle", 0.95));
        var result = new JevExpressionModel(client, properties).plan(request());
        assertThat(result).isPresent();
        assertThat(result.get().style()).isEqualTo("gentle");
        assertThat(received.get()).doesNotContain("private-character", "private-profile", "fallback");
        assertThat(mapper.readTree(received.get()).path("state").path("utterance").asText()).contains("잘렸어");
    }

    @Test void lowConfidenceKeepsDeterministicExpression() throws Exception {
        response.set(choice("gentle", 0.2));
        assertThat(new JevExpressionModel(client, properties).plan(request())).isEmpty();
    }

    @Test void reranksOnlySuppliedMemoriesWithNoPersistentIdentifiers() throws Exception {
        response.set(scores(0, 2));
        var candidates = List.of(memory(11, "커피를 좋아함", "private-user"), memory(12, "금요일에 발표 예정", "private-user"));
        assertThat(new JevMemoryReranker(client, properties).rerank("내 발표 언제지?", candidates))
                .containsExactly(candidates.get(1), candidates.get(0));
        assertThat(received.get()).doesNotContain("private-user", "private-character", "private-world");
    }

    @Test void refusesToSendMixedSubjectScope() {
        var candidates = List.of(memory(1, "a", "one"), memory(2, "b", "two"));
        assertThat(new JevMemoryReranker(client, properties).rerank("query", candidates)).isSameAs(candidates);
        assertThat(calls).hasValue(0);
    }

    @Test void incompleteResponseAndProviderFailurePreserveOriginalOrderAndCooldown() {
        response.set("{\"model\":\"jev-1.13.0\",\"answers\":{}}");
        var candidates = List.of(memory(1, "a", "one"), memory(2, "b", "one"));
        var ranker = new JevMemoryReranker(client, properties);
        assertThat(ranker.rerank("query", candidates)).isSameAs(candidates);
        assertThat(ranker.rerank("query", candidates)).isSameAs(candidates);
        assertThat(calls).hasValue(1);
    }

    @Test void timeoutIsBoundedAndFallsBackWithoutRetry() throws Exception {
        response.set(choice("gentle", 1));
        delay = 700;
        properties.setExpressionTimeoutMillis(120);
        long start = System.nanoTime();
        assertThat(new JevExpressionModel(client, properties).plan(request())).isEmpty();
        assertThat((System.nanoTime() - start) / 1_000_000).isLessThan(600);
        assertThat(new JevExpressionModel(client, properties).plan(request())).isEmpty();
        assertThat(calls.get()).isLessThanOrEqualTo(1);
    }

    @Test void oversizedResponseFailsClosed() {
        response.set("x".repeat(70_000));
        assertThat(new JevExpressionModel(client, properties).plan(request())).isEmpty();
    }

    @Test void wrongModelIdentityFailsClosed() throws Exception {
        response.set(choice("gentle", 1).replace("jev-1.13.0", "jev-9.0.0"));
        assertThat(new JevExpressionModel(client, properties).plan(request())).isEmpty();
    }

    @Test void invalidProbabilityAndUnknownChoiceFailClosed() throws Exception {
        response.set(choice("unknown", 1));
        assertThat(new JevExpressionModel(client, properties).plan(request())).isEmpty();
    }

    @Test void disabledAndMissingKeyNeverCallProvider() {
        properties.setApiKey("");
        assertThat(new JevExpressionModel(client, properties).plan(request())).isEmpty();
        properties.setApiKey("synthetic"); properties.setEnabled(false);
        assertThat(new JevExpressionModel(client, properties).plan(request())).isEmpty();
        assertThat(calls).hasValue(0);
    }

    @Test void providerErrorDoesNotExposeResponseAndTripsCooldown() {
        status = 401; response.set("sensitive provider error");
        assertThat(new JevExpressionModel(client, properties).plan(request())).isEmpty();
        assertThat(new JevExpressionModel(client, properties).plan(request())).isEmpty();
        assertThat(calls).hasValue(1);
    }

    @Test void jevAndSmallModelFlagsProduceExactlyOneExpressionBean() {
        new ApplicationContextRunner().withUserConfiguration(JevConfiguration.class, SmallConversationExpressionModelConfiguration.class)
                .withBean(ObjectMapper.class, ObjectMapper::new)
                .withBean(io.micrometer.core.instrument.MeterRegistry.class, SimpleMeterRegistry::new)
                .withPropertyValues("gahyeon.jev.enabled=true", "gahyeon.speech.expression-planner.small-model.enabled=true")
                .run(context -> {
                    assertThat(context).hasSingleBean(ConversationExpressionModel.class);
                    assertThat(context.getBean(ConversationExpressionModel.class)).isInstanceOf(JevExpressionModel.class);
                });
    }

    @Test void disablingJevRestoresExistingSmallModel() {
        new ApplicationContextRunner().withUserConfiguration(JevConfiguration.class, SmallConversationExpressionModelConfiguration.class)
                .withBean(ObjectMapper.class, ObjectMapper::new)
                .withPropertyValues("gahyeon.jev.enabled=false", "gahyeon.speech.expression-planner.small-model.enabled=true")
                .run(context -> {
                    assertThat(context).hasSingleBean(ConversationExpressionModel.class);
                    assertThat(context.getBean(ConversationExpressionModel.class))
                            .isInstanceOf(com.gahyeonbot.adapters.speech.HttpSmallConversationExpressionModel.class);
                });
    }

    private String choice(String selected, double confidence) throws Exception {
        Map<String, Double> probabilities = new LinkedHashMap<>();
        JevExpressionModel.STYLES.keySet().forEach(style -> probabilities.put(style, style.equals(selected) ? 1d : 0d));
        return mapper.writeValueAsString(Map.of("model", properties.getModel(), "answers", Map.of("style", Map.of(
                "type", "choice", "choice", selected, "confidence", confidence, "probabilities", probabilities))));
    }

    private String scores(int first, int second) throws Exception {
        Map<String, Object> answers = new LinkedHashMap<>();
        for (int i = 0; i < 2; i++) {
            int score = i == 0 ? first : second;
            answers.put("m" + i, Map.of("type", "score", "score", score, "confidence", 1,
                    "probabilities", Map.of("0", score == 0 ? 1 : 0, "1", score == 1 ? 1 : 0, "2", score == 2 ? 1 : 0)));
        }
        return mapper.writeValueAsString(Map.of("model", properties.getModel(), "answers", answers));
    }

    static ConversationExpressionModelRequest request() {
        return new ConversationExpressionModelRequest("private-character", "private-profile", true,
                "ㅋㅋ 나 오늘 잘렸어", "idle", 0, 0.2, 0.3, 0.3, 0.3, 0, "bright", 0.5, "conversation");
    }

    static CharacterMemory memory(long id, String text, String subject) {
        return new CharacterMemory(id, new CharacterId("private-character"), new WorldId("private-world"), subject,
                CharacterMemoryKind.SEMANTIC, text, 0.5, 1, 0, null, Instant.EPOCH, Instant.EPOCH);
    }
}
