package com.gahyeonbot.application.speech;

import org.junit.jupiter.api.*;
import org.springframework.context.annotation.*;
import org.springframework.core.io.ClassPathResource;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.jdbc.datasource.DataSourceTransactionManager;
import org.springframework.jdbc.datasource.DriverManagerDataSource;
import org.springframework.jdbc.datasource.init.ResourceDatabasePopulator;
import org.springframework.transaction.annotation.EnableTransactionManagement;

import javax.sql.DataSource;
import java.time.*;
import java.util.UUID;
import java.util.concurrent.Executors;
import static org.assertj.core.api.Assertions.*;

class SttLearningServiceTest {
    static final String PIPELINE = SttLearningService.hash("whisper-test");
    static final String RAW = "테스트 고유명사 오인식";
    static final String EXPECTED = "테스트 고유명사 정답";
    AnnotationConfigApplicationContext context;
    SttLearningService service;
    MutableClock clock;

    @BeforeEach void setup() {
        context = new AnnotationConfigApplicationContext(Config.class);
        service = context.getBean(SttLearningService.class);
        clock = context.getBean(MutableClock.class);
    }
    @AfterEach void close() { context.close(); }

    @Test void requiresThreeLabelsAndTwoFutureHoldoutsBeforeApplying() {
        train();
        var first = observe(RAW);
        assertThat(first.text()).isEqualTo(RAW);
        assertThat(label(first, EXPECTED)).isEqualTo("VALIDATING");
        var second = observe(RAW);
        assertThat(second.text()).isEqualTo(RAW);
        assertThat(label(second, EXPECTED)).isEqualTo("ACTIVE");
        assertThat(observe(RAW).text()).isEqualTo(EXPECTED);
        assertThat(observe("앞에 " + RAW).text()).isEqualTo("앞에 " + RAW);
    }

    @Test void historicalBackfillCannotMasqueradeAsFutureHoldout() {
        var past1 = observe(RAW);
        var past2 = observe(RAW);
        train();
        assertThat(label(past1, EXPECTED)).isEqualTo("VALIDATING");
        assertThat(label(past2, EXPECTED)).isEqualTo("VALIDATING");
        assertThat(observe(RAW).text()).isEqualTo(RAW);
    }

    @Test void duplicateRequestsAndDuplicateLabelsCannotInflateEvidence() {
        String id = UUID.randomUUID().toString();
        var turn = service.observe(1, "discord:10", PIPELINE, id, RAW);
        for (int i = 0; i < 6; i++) {
            assertThat(service.observe(1, "discord:10", PIPELINE, id, RAW).observationId()).isEqualTo(turn.observationId());
            assertThat(label(turn, EXPECTED)).isEqualTo("COLLECTING");
        }
        assertThat(service.recent(1, "discord:10")).hasSize(1);
        assertThatThrownBy(() -> service.observe(1, "discord:10", PIPELINE, id, "다른 문장"))
                .isInstanceOf(IllegalArgumentException.class);
    }

    @Test void conflictsBlockActiveRuleAndDoNotAutomaticallyReenableIt() {
        activate();
        var mistaken = observe(RAW);
        assertThat(mistaken.text()).isEqualTo(EXPECTED);
        assertThat(label(mistaken, RAW)).isEqualTo("BLOCKED");
        for (int i = 0; i < 6; i++) assertThat(label(observe(RAW), EXPECTED)).isEqualTo("BLOCKED");
        assertThat(observe(RAW).text()).isEqualTo(RAW);
    }

    @Test void usersServersAndPipelineRevisionsAreIsolated() {
        activate();
        var turn = observe(RAW);
        assertThat(service.observe(2, "discord:10", PIPELINE, "other-user", RAW).text()).isEqualTo(RAW);
        assertThat(service.observe(1, "discord:11", PIPELINE, "other-server", RAW).text()).isEqualTo(RAW);
        assertThat(service.observe(1, "discord:10", SttLearningService.hash("new-model"), "new-model", RAW).text()).isEqualTo(RAW);
        assertThatThrownBy(() -> service.correct(2, "discord:10", turn.observationId(), EXPECTED)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> service.disable(1, "discord:11", turn.observationId())).isInstanceOf(IllegalArgumentException.class);
    }

    @Test void disableAndRestartPreserveRevocationAndClearIsOwnerScoped() {
        activate();
        var turn = observe(RAW);
        service.disable(1, "discord:10", turn.observationId());
        var restarted = new SttLearningService(context.getBean(JdbcTemplate.class), clock);
        assertThat(restarted.observe(1, "discord:10", PIPELINE, "after-restart", RAW).text()).isEqualTo(RAW);
        service.observe(2, "discord:10", PIPELINE, "other", RAW);
        service.clear(1, "discord:10");
        assertThat(service.recent(1, "discord:10")).isEmpty();
        assertThat(service.recent(2, "discord:10")).hasSize(1);
    }

    @Test void expiredRulesStopApplyingBeforeCleanupAndOldRecordsAreDeleted() {
        activate();
        var old = observe(RAW);
        clock.now = clock.now.plus(Duration.ofDays(31));
        assertThat(observe(RAW).text()).isEqualTo(RAW);
        assertThatThrownBy(() -> label(old, EXPECTED)).isInstanceOf(IllegalArgumentException.class);
        service.purgeExpired();
        assertThat(service.recent(1, "discord:10")).isEmpty();
    }

    @Test void concurrentFeedbackOnOneObservationCountsOnlyOnce() throws Exception {
        var turn = observe(RAW);
        try (var executor = Executors.newVirtualThreadPerTaskExecutor()) {
            var tasks = java.util.stream.IntStream.range(0, 8)
                    .mapToObj(i -> executor.submit(() -> label(turn, EXPECTED))).toList();
            for (var task : tasks) assertThat(task.get()).isEqualTo("COLLECTING");
        }
    }

    @Test void neverLearnsFromUnreviewedRepetitionsOrLongInputs() {
        for (int i = 0; i < 12; i++) assertThat(observe(RAW).text()).isEqualTo(RAW);
        assertThat(service.observe(1, "discord:10", PIPELINE, "long", "가".repeat(513)).state()).isEqualTo("BYPASS");
    }

    private void train() { for (int i = 0; i < 3; i++) label(observe(RAW), EXPECTED); }
    private void activate() { train(); label(observe(RAW), EXPECTED); label(observe(RAW), EXPECTED); }
    private SttLearningService.Decision observe(String raw) {
        clock.now = clock.now.plusSeconds(1);
        return service.observe(1, "discord:10", PIPELINE, UUID.randomUUID().toString(), raw);
    }
    private String label(SttLearningService.Decision turn, String expected) {
        return service.correct(1, "discord:10", turn.observationId(), expected);
    }

    static class MutableClock extends Clock {
        Instant now = Instant.parse("2026-10-11T00:00:00Z");
        @Override public ZoneId getZone() { return ZoneOffset.UTC; }
        @Override public Clock withZone(ZoneId zone) { return this; }
        @Override public Instant instant() { return now; }
    }
    @Configuration
    @EnableTransactionManagement
    static class Config {
        @Bean DataSource dataSource() {
            var ds = new DriverManagerDataSource("jdbc:h2:mem:" + UUID.randomUUID() + ";MODE=PostgreSQL;DB_CLOSE_DELAY=-1", "sa", "");
            new ResourceDatabasePopulator(new ClassPathResource("db/migration/V43__Add_stt_learning.sql")).execute(ds);
            return ds;
        }
        @Bean JdbcTemplate jdbc(DataSource ds) { return new JdbcTemplate(ds); }
        @Bean DataSourceTransactionManager transactionManager(DataSource ds) { return new DataSourceTransactionManager(ds); }
        @Bean MutableClock clock() { return new MutableClock(); }
        @Bean SttLearningService learning(JdbcTemplate jdbc, MutableClock clock) { return new SttLearningService(jdbc, clock); }
    }
}
