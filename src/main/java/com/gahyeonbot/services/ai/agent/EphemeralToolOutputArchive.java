package com.gahyeonbot.services.ai.agent;

import java.time.Clock;
import java.time.Duration;
import java.time.Instant;
import java.util.Iterator;
import java.util.LinkedHashMap;
import java.util.Map;
import java.util.Optional;

/**
 * Bounded, process-local recovery storage. Raw tool output is deliberately never written to logs
 * or durable storage; entries disappear on expiry, eviction, or restart.
 */
final class EphemeralToolOutputArchive implements ToolOutputArchive {
    private static final int DEFAULT_MAX_ENTRIES = 128;
    private static final int DEFAULT_MAX_CHARACTERS = 2_000_000;
    private static final Duration DEFAULT_RETENTION = Duration.ofMinutes(5);

    private final int maxEntries;
    private final int maxCharacters;
    private final Duration retention;
    private final Clock clock;
    private final LinkedHashMap<String, Entry> entries = new LinkedHashMap<>(16, 0.75f, true);
    private int storedCharacters;

    EphemeralToolOutputArchive() {
        this(DEFAULT_MAX_ENTRIES, DEFAULT_MAX_CHARACTERS, DEFAULT_RETENTION, Clock.systemUTC());
    }

    EphemeralToolOutputArchive(int maxEntries, int maxCharacters, Duration retention, Clock clock) {
        if (maxEntries < 1 || maxCharacters < 1 || retention.isNegative() || retention.isZero()) {
            throw new IllegalArgumentException("archive bounds and retention must be positive");
        }
        this.maxEntries = maxEntries;
        this.maxCharacters = maxCharacters;
        this.retention = retention;
        this.clock = clock;
    }

    @Override
    public synchronized void store(String digest, String toolName, String originalOutput) {
        purgeExpired();
        String original = originalOutput == null ? "" : originalOutput;
        if (original.length() > maxCharacters) {
            throw new IllegalArgumentException("tool output exceeds ephemeral archive capacity");
        }
        Entry replaced = entries.remove(digest);
        if (replaced != null) storedCharacters -= replaced.originalOutput().length();
        entries.put(digest, new Entry(original, clock.instant().plus(retention)));
        storedCharacters += original.length();
        evictToBounds();
        if (!entries.containsKey(digest)) {
            throw new IllegalStateException("tool output could not be retained for recovery");
        }
    }

    @Override
    public synchronized Optional<String> retrieve(String digest) {
        purgeExpired();
        Entry entry = entries.get(digest);
        return entry == null ? Optional.empty() : Optional.of(entry.originalOutput());
    }

    private void purgeExpired() {
        Instant now = clock.instant();
        Iterator<Map.Entry<String, Entry>> iterator = entries.entrySet().iterator();
        while (iterator.hasNext()) {
            Entry entry = iterator.next().getValue();
            if (!entry.expiresAt().isAfter(now)) {
                storedCharacters -= entry.originalOutput().length();
                iterator.remove();
            }
        }
    }

    private void evictToBounds() {
        Iterator<Map.Entry<String, Entry>> iterator = entries.entrySet().iterator();
        while ((entries.size() > maxEntries || storedCharacters > maxCharacters)
                && iterator.hasNext()) {
            Entry entry = iterator.next().getValue();
            storedCharacters -= entry.originalOutput().length();
            iterator.remove();
        }
    }

    private record Entry(String originalOutput, Instant expiresAt) {}
}
