package com.gahyeonbot.application.speech;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.sql.Timestamp;
import java.time.Clock;
import java.time.Duration;
import java.time.Instant;
import java.util.HexFormat;
import java.util.List;

/** Explicit labels only. This learns exact utterance corrections, never model weights. */
@Service
public class SttLearningService {
    private static final Duration RETENTION = Duration.ofDays(30);
    private final JdbcTemplate jdbc;
    private final Clock clock;

    @Autowired
    public SttLearningService(JdbcTemplate jdbc) { this(jdbc, Clock.systemUTC()); }
    SttLearningService(JdbcTemplate jdbc, Clock clock) { this.jdbc = jdbc; this.clock = clock; }

    public record Observation(String id, String raw, String effective, String expected, Instant captured) {}
    public record Decision(String observationId, String text, String state) {}
    private record Rule(String id, String raw, String target, String state, Instant validation, Instant expires) {}

    public static String hash(String... values) {
        try {
            var digest = MessageDigest.getInstance("SHA-256");
            for (String value : values) {
                byte[] bytes = String.valueOf(value).getBytes(StandardCharsets.UTF_8);
                digest.update((bytes.length + ":").getBytes(StandardCharsets.UTF_8));
                digest.update(bytes);
            }
            return HexFormat.of().formatHex(digest.digest());
        } catch (java.security.NoSuchAlgorithmException impossible) { throw new IllegalStateException(impossible); }
    }

    @Transactional(timeout = 3)
    public Decision observe(long actor, String scope, String pipeline, String requestId, String raw) {
        owner(actor, scope);
        if (raw == null || raw.isBlank() || raw.length() > 512) return new Decision(null, raw, "BYPASS");
        if (pipeline == null || pipeline.length() != 64 || requestId == null || requestId.isBlank())
            throw new IllegalArgumentException("invalid observation identity");
        Instant now = clock.instant();
        String id = hash(Long.toString(actor), scope, pipeline, raw);
        String observationId = hash(Long.toString(actor), scope, requestId);
        jdbc.update("""
                INSERT INTO stt_learning_rules(id, actor_id, scope, pipeline, raw_text, expires_at)
                VALUES (?, ?, ?, ?, ?, ?) ON CONFLICT DO NOTHING
                """, id, actor, scope, pipeline, raw, Timestamp.from(now.plus(RETENTION)));
        Rule rule = lock(id, actor, scope);
        String effective = rule.state().equals("ACTIVE") && rule.expires().isAfter(now) ? rule.target() : raw;
        jdbc.update("""
                INSERT INTO stt_learning_observations(id, rule_id, raw_text, effective_text, captured_at)
                VALUES (?, ?, ?, ?, ?) ON CONFLICT DO NOTHING
                """, observationId, id, raw, effective, Timestamp.from(now));
        Observation stored = observation(actor, scope, observationId);
        if (!stored.raw().equals(raw)) throw new IllegalArgumentException("request identity reused");
        return new Decision(observationId, stored.effective(), stored.effective().equals(raw) ? "UNCHANGED" : "APPLIED");
    }

    @Transactional(timeout = 3)
    public String correct(long actor, String scope, String observationId, String expected) {
        owner(actor, scope);
        if (expected == null || expected.isBlank() || expected.length() > 512)
            throw new IllegalArgumentException("정정 문장은 1~512자여야 합니다.");
        expected = expected.trim();
        Rule rule = lockForObservation(actor, scope, observationId);
        Observation turn = observation(actor, scope, observationId);
        Instant now = clock.instant();
        if (turn.captured().isBefore(now.minus(RETENTION)) || !rule.expires().isAfter(now))
            throw new IllegalArgumentException("정정 기간이 지났습니다.");
        if (turn.expected() != null) {
            if (!turn.expected().equals(expected)) throw new IllegalArgumentException("이미 검토한 기록입니다. 중지를 사용하세요.");
            return rule.state(); // retries cannot inflate evidence
        }
        jdbc.update("UPDATE stt_learning_observations SET expected_text=?, reviewed_at=? WHERE id=?",
                expected, Timestamp.from(now), observationId);
        if (rule.state().equals("BLOCKED")) return "BLOCKED";
        List<Observation> labels = jdbc.query("""
                SELECT * FROM stt_learning_observations WHERE rule_id=? AND expected_text IS NOT NULL
                AND captured_at>=? ORDER BY captured_at, id
                """, (rs, n) -> mapObservation(rs), rule.id(), Timestamp.from(now.minus(RETENTION)));
        // A correct original or any disagreement invalidates the whole mapping immediately.
        if (labels.stream().map(Observation::expected).distinct().count() != 1 || expected.equals(rule.raw())) {
            setState(rule.id(), "BLOCKED", null, null);
            return "BLOCKED";
        }
        if (rule.state().equals("COLLECTING") && labels.size() >= 3) {
            setState(rule.id(), "VALIDATING", expected, now);
            return "VALIDATING";
        }
        if (rule.state().equals("VALIDATING")) {
            long futureHoldouts = labels.stream().filter(o -> o.captured().isAfter(rule.validation())).count();
            if (futureHoldouts >= 2) {
                setState(rule.id(), "ACTIVE", expected, rule.validation());
                return "ACTIVE";
            }
        }
        return rule.state();
    }

    @Transactional(timeout = 3)
    public void disable(long actor, String scope, String observationId) {
        Rule rule = lockForObservation(actor, scope, observationId);
        setState(rule.id(), "BLOCKED", null, null);
    }

    public List<Observation> recent(long actor, String scope) {
        owner(actor, scope);
        return jdbc.query("""
                SELECT o.* FROM stt_learning_observations o JOIN stt_learning_rules r ON r.id=o.rule_id
                WHERE r.actor_id=? AND r.scope=? AND o.captured_at>=?
                ORDER BY o.captured_at DESC, o.id DESC LIMIT 5
                """, (rs, n) -> mapObservation(rs), actor, scope, Timestamp.from(clock.instant().minus(RETENTION)));
    }

    @Transactional(timeout = 3)
    public void clear(long actor, String scope) {
        owner(actor, scope);
        jdbc.update("DELETE FROM stt_learning_rules WHERE actor_id=? AND scope=?", actor, scope);
    }

    @Scheduled(fixedDelay = 3_600_000)
    @Transactional(timeout = 10)
    public void purgeExpired() {
        jdbc.update("DELETE FROM stt_learning_rules WHERE expires_at<=?", Timestamp.from(clock.instant()));
    }

    private Rule lockForObservation(long actor, String scope, String observationId) {
        owner(actor, scope);
        List<String> ids = jdbc.query("""
                SELECT r.id FROM stt_learning_rules r JOIN stt_learning_observations o ON o.rule_id=r.id
                WHERE o.id=? AND r.actor_id=? AND r.scope=?
                """, (rs, n) -> rs.getString(1), observationId, actor, scope);
        if (ids.isEmpty()) throw new IllegalArgumentException("본인의 전사 기록을 찾을 수 없습니다.");
        return lock(ids.getFirst(), actor, scope);
    }

    private Rule lock(String id, long actor, String scope) {
        var rows = jdbc.query("SELECT * FROM stt_learning_rules WHERE id=? AND actor_id=? AND scope=? FOR UPDATE",
                (rs, n) -> new Rule(rs.getString("id"), rs.getString("raw_text"), rs.getString("target_text"),
                        rs.getString("state"), rs.getTimestamp("validation_started") == null ? null :
                        rs.getTimestamp("validation_started").toInstant(), rs.getTimestamp("expires_at").toInstant()),
                id, actor, scope);
        if (rows.isEmpty()) throw new IllegalArgumentException("전사 규칙을 찾을 수 없습니다.");
        return rows.getFirst();
    }

    private Observation observation(long actor, String scope, String id) {
        var rows = jdbc.query("""
                SELECT o.* FROM stt_learning_observations o JOIN stt_learning_rules r ON r.id=o.rule_id
                WHERE o.id=? AND r.actor_id=? AND r.scope=?
                """, (rs, n) -> mapObservation(rs), id, actor, scope);
        if (rows.isEmpty()) throw new IllegalArgumentException("본인의 전사 기록을 찾을 수 없습니다.");
        return rows.getFirst();
    }

    private static Observation mapObservation(java.sql.ResultSet rs) throws java.sql.SQLException {
        return new Observation(rs.getString("id"), rs.getString("raw_text"), rs.getString("effective_text"),
                rs.getString("expected_text"), rs.getTimestamp("captured_at").toInstant());
    }

    private void setState(String id, String state, String target, Instant validation) {
        jdbc.update("UPDATE stt_learning_rules SET state=?, target_text=?, validation_started=? WHERE id=?",
                state, target, validation == null ? null : Timestamp.from(validation), id);
    }

    private static void owner(long actor, String scope) {
        if (actor <= 0 || scope == null || !scope.matches("discord:[0-9]{1,20}"))
            throw new IllegalArgumentException("invalid learning scope");
    }
}
