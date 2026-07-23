package com.gahyeonbot.services.assistant;

public interface SpeechToTextProvider {
    boolean isReady();
    String transcribe(byte[] wavAudio);
}
