package com.gahyeonbot.services.ai.agent;

import org.junit.jupiter.api.Test;

import java.time.Clock;
import java.time.Duration;
import java.time.Instant;
import java.time.ZoneOffset;

import static org.assertj.core.api.Assertions.assertThat;

class EphemeralToolOutputArchiveTest {
    @Test
    void retainsExactOutputOnlyInsideTheBoundedRecoveryWindow() {
        Instant start = Instant.parse("2026-08-24T00:00:00Z");
        MutableClock clock = new MutableClock(start);
        var archive = new EphemeralToolOutputArchive(2, 100, Duration.ofMinutes(5), clock);

        archive.store("digest", "papers", "exact tool output");
        assertThat(archive.retrieve("digest")).contains("exact tool output");

        clock.instant = start.plus(Duration.ofMinutes(5));
        assertThat(archive.retrieve("digest")).isEmpty();
    }

    @Test
    void evictsLeastRecentlyUsedOutputAtCapacity() {
        var archive = new EphemeralToolOutputArchive(
                2, 100, Duration.ofMinutes(5), Clock.systemUTC());
        archive.store("one", "tool", "1");
        archive.store("two", "tool", "2");
        archive.retrieve("one");

        archive.store("three", "tool", "3");

        assertThat(archive.retrieve("one")).contains("1");
        assertThat(archive.retrieve("two")).isEmpty();
        assertThat(archive.retrieve("three")).contains("3");
    }

    private static final class MutableClock extends Clock {
        private Instant instant;

        private MutableClock(Instant instant) {
            this.instant = instant;
        }

        @Override public ZoneOffset getZone() { return ZoneOffset.UTC; }
        @Override public Clock withZone(java.time.ZoneId zone) { return this; }
        @Override public Instant instant() { return instant; }
    }
}
