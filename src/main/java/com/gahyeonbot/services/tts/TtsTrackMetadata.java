package com.gahyeonbot.services.tts;

import java.nio.file.Path;

/**
 * Stored as Lavaplayer track userData to allow cleanup on track end.
 */
public record TtsTrackMetadata(Path wavPath, boolean deleteOnEnd) {}

