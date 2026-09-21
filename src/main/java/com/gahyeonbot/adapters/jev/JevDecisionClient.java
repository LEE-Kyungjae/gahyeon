package com.gahyeonbot.adapters.jev;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import io.micrometer.core.instrument.MeterRegistry;
import java.io.ByteArrayOutputStream;
import java.net.URI;
import java.net.http.*;
import java.nio.ByteBuffer;
import java.time.Duration;
import java.util.*;
import java.util.concurrent.*;
import java.util.concurrent.atomic.AtomicLong;

/** One bounded call, no retries, no raw input/output logging, and no redirects with credentials. */
public class JevDecisionClient {
    private static final URI ENDPOINT = URI.create("https://api.typesafe.ai/v1/systemone");
    private static final int MAX_BYTES = 65_536;
    private final JevProperties properties;
    private final ObjectMapper mapper;
    private final MeterRegistry metrics;
    private final HttpClient http;
    private final URI endpoint;
    private final Semaphore slots = new Semaphore(2);
    private final AtomicLong cooldownUntil = new AtomicLong();

    public JevDecisionClient(JevProperties properties, ObjectMapper mapper, MeterRegistry metrics) {
        this(properties, mapper, metrics, HttpClient.newBuilder()
                .connectTimeout(Duration.ofMillis(800)).followRedirects(HttpClient.Redirect.NEVER).build(), ENDPOINT);
    }

    // Package-private endpoint injection is only for loopback transport tests.
    JevDecisionClient(JevProperties properties, ObjectMapper mapper, MeterRegistry metrics, HttpClient http, URI endpoint) {
        this.properties = properties;
        this.mapper = mapper;
        this.metrics = metrics;
        this.http = http;
        this.endpoint = endpoint;
    }

    public Optional<JsonNode> decide(String purpose, Object state, Map<String, Object> questions, int timeoutMillis) {
        if (!properties.isEnabled() || properties.getApiKey().isBlank()) return outcome(purpose, "disabled");
        if (System.nanoTime() < cooldownUntil.get()) return outcome(purpose, "cooldown");
        if (!slots.tryAcquire()) return outcome(purpose, "busy");
        long started = System.nanoTime();
        CompletableFuture<HttpResponse<byte[]>> pending = null;
        try {
            byte[] body = mapper.writeValueAsBytes(Map.of("model", properties.getModel(), "state", state, "questions", questions));
            if (body.length > MAX_BYTES || questions.isEmpty() || questions.size() > 24) return outcome(purpose, "input_limit");
            var request = HttpRequest.newBuilder(endpoint).timeout(Duration.ofMillis(timeoutMillis))
                    .header("Authorization", "Bearer " + properties.getApiKey())
                    .header("Content-Type", "application/json")
                    .POST(HttpRequest.BodyPublishers.ofByteArray(body)).build();
            pending = http.sendAsync(request, ignored -> new BoundedBody());
            var response = pending.get(timeoutMillis, TimeUnit.MILLISECONDS);
            if (response.statusCode() != 200) throw new IllegalStateException("provider_status");
            JsonNode root = mapper.readTree(response.body());
            if (root == null || !properties.getModel().equals(root.path("model").asText())) {
                throw new IllegalStateException("model_identity");
            }
            JsonNode answers = root.path("answers");
            if (!answers.isObject() || answers.size() != questions.size()) throw new IllegalStateException("answer_schema");
            for (var entry : questions.entrySet()) {
                validate(answers.path(entry.getKey()), mapper.valueToTree(entry.getValue()));
            }
            metrics.counter("gahyeonbot.jev.decisions", "purpose", purpose, "outcome", "success").increment();
            return Optional.of(answers);
        } catch (InterruptedException interrupted) {
            Thread.currentThread().interrupt();
            return outcome(purpose, "interrupted");
        } catch (Exception unavailable) {
            cooldownUntil.set(System.nanoTime() + TimeUnit.SECONDS.toNanos(5));
            return outcome(purpose, "unavailable");
        } finally {
            if (pending != null && !pending.isDone()) pending.cancel(true);
            slots.release();
            metrics.timer("gahyeonbot.jev.latency", "purpose", purpose)
                    .record(System.nanoTime() - started, TimeUnit.NANOSECONDS);
        }
    }

    public void fallback(String purpose, String reason) {
        metrics.counter("gahyeonbot.jev.fallback", "purpose", purpose, "reason", reason).increment();
    }

    private Optional<JsonNode> outcome(String purpose, String result) {
        metrics.counter("gahyeonbot.jev.decisions", "purpose", purpose, "outcome", result).increment();
        return Optional.empty();
    }

    private static void validate(JsonNode answer, JsonNode question) {
        String type = question.path("type").asText();
        if (!type.equals(answer.path("type").asText())) throw new IllegalStateException("answer_type");
        unit(answer.path("confidence"));
        JsonNode criteria = question.path("criteria");
        Set<String> expected = new HashSet<>();
        if ("choice".equals(type)) {
            criteria.fieldNames().forEachRemaining(expected::add);
            if (!answer.path("choice").isTextual() || !expected.contains(answer.path("choice").asText())) {
                throw new IllegalStateException("unknown_choice");
            }
        } else if ("score".equals(type)) {
            for (int i = 0; i < criteria.size(); i++) expected.add(Integer.toString(i));
            JsonNode score = answer.path("score");
            if (!score.isNumber() || !Double.isFinite(score.asDouble()) || score.asDouble() < 0
                    || score.asDouble() > criteria.size() - 1) throw new IllegalStateException("invalid_score");
        } else throw new IllegalStateException("unsupported_type");
        JsonNode probabilities = answer.path("probabilities");
        if (!probabilities.isObject() || probabilities.size() != expected.size()) throw new IllegalStateException("distribution");
        double sum = 0;
        for (String key : expected) sum += unit(probabilities.path(key));
        if (Math.abs(sum - 1) > 0.02) throw new IllegalStateException("distribution_sum");
    }

    private static double unit(JsonNode value) {
        if (!value.isNumber() || !Double.isFinite(value.asDouble()) || value.asDouble() < 0 || value.asDouble() > 1) {
            throw new IllegalStateException("invalid_probability");
        }
        return value.asDouble();
    }

    private static final class BoundedBody implements HttpResponse.BodySubscriber<byte[]> {
        private final CompletableFuture<byte[]> result = new CompletableFuture<>();
        private final ByteArrayOutputStream bytes = new ByteArrayOutputStream();
        private Flow.Subscription subscription;
        @Override public CompletionStage<byte[]> getBody() { return result; }
        @Override public void onSubscribe(Flow.Subscription value) { subscription = value; value.request(1); }
        @Override public void onNext(List<ByteBuffer> buffers) {
            for (ByteBuffer buffer : buffers) {
                if (buffer.remaining() > MAX_BYTES - bytes.size()) {
                    subscription.cancel();
                    result.completeExceptionally(new IllegalStateException("response_limit"));
                    return;
                }
                byte[] chunk = new byte[buffer.remaining()];
                buffer.get(chunk);
                bytes.writeBytes(chunk);
            }
            subscription.request(1);
        }
        @Override public void onError(Throwable error) { result.completeExceptionally(error); }
        @Override public void onComplete() { result.complete(bytes.toByteArray()); }
    }
}
