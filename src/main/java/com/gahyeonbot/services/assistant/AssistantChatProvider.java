package com.gahyeonbot.services.assistant;

public interface AssistantChatProvider {
    boolean isReady();
    String chat(long guildId, long userId, String username, String message);
}
