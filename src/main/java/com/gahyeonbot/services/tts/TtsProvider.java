package com.gahyeonbot.services.tts;

import java.nio.file.Path;

public interface TtsProvider {
    String name();
    boolean isReady();
    Path synthesize(String text) throws Exception;
}
