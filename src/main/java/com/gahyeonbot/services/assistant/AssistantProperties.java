package com.gahyeonbot.services.assistant;

import lombok.Getter;
import lombok.Setter;
import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.stereotype.Component;

@Getter
@Setter
@Component
@ConfigurationProperties(prefix = "assistant")
public class AssistantProperties {
    private boolean enabled;
    private int maxUtteranceSeconds = 20;
    private long silenceMillis = 900;
    private boolean speakResponses = true;
    private final Stt stt = new Stt();
    private final OpenRouter openrouter = new OpenRouter();

    @Getter
    @Setter
    public static class Stt {
        private boolean enabled;
        private String baseUrl = "https://api.openai.com/v1";
        private String apiKey;
        private String model = "gpt-4o-mini-transcribe";
        private String language = "ko";
        private int timeoutSeconds = 30;
    }

    @Getter
    @Setter
    public static class OpenRouter {
        private boolean enabled;
        private String apiKey;
        private String baseUrl = "https://openrouter.ai/api/v1";
        private String model;
        private int timeoutSeconds = 60;
    }
}
