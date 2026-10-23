package com.gahyeonbot.adapters.discord.voice;

/** Only explicit trailing connectives; complete questions and short acknowledgements remain responsive. */
final class VoiceContinuationPolicy {
    static boolean unfinished(String transcript) {
        if (transcript == null || transcript.endsWith("?")) return false;
        String text = transcript.strip().replaceAll("[.。…]+$", "").strip();
        return text.matches("(?s).*(?:어떻게 해야 되냐면|어떻게 하냐면|예를 들면|그러니까|해가지고|말씀드리면|한다면|하는데 그중에|그런 거일 수도 있고)$");
    }
}
