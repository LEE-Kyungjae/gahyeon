package com.gahyeonbot.adapters.discord.voice;

import java.util.HashSet;
import java.util.Locale;
import java.util.Set;

final class VoiceBargeInPolicy {
    private static final long ECHO_WINDOW_MILLIS = 30_000;
    private String recentSpeech = "";
    private long recentSpeechAt = Long.MIN_VALUE;

    synchronized void rememberBotSpeech(String text, long now) {
        String normalized = normalize(text);
        if (normalized.length() < 4) return;
        recentSpeech = normalized;
        recentSpeechAt = now;
    }

    synchronized boolean isLikelySelfEcho(String transcript, long now) {
        String candidate = normalize(transcript);
        if (candidate.length() < 4 || recentSpeech.isBlank() || recentSpeechAt == Long.MIN_VALUE
                || now - recentSpeechAt < 0 || now - recentSpeechAt > ECHO_WINDOW_MILLIS) return false;
        if (recentSpeech.contains(candidate) || candidate.contains(recentSpeech)) return true;
        Set<String> left = bigrams(candidate);
        Set<String> right = bigrams(recentSpeech);
        long shared = left.stream().filter(right::contains).count();
        return !left.isEmpty() && !right.isEmpty() && shared * 2.0 / (left.size() + right.size()) >= 0.72;
    }

    private static Set<String> bigrams(String value) {
        var result = new HashSet<String>();
        for (int index = 0; index + 1 < value.length(); index++) result.add(value.substring(index, index + 2));
        return result;
    }

    private static String normalize(String value) {
        return value == null ? "" : value.toLowerCase(Locale.ROOT).replaceAll("[^\\p{L}\\p{N}]", "").trim();
    }
}
