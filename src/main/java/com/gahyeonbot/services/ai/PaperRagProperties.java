package com.gahyeonbot.services.ai;

import lombok.Getter;
import lombok.Setter;
import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.stereotype.Component;

@Getter
@Setter
@Component
@ConfigurationProperties(prefix = "paper-rag")
public class PaperRagProperties {

    private boolean enabled;
    private String baseUrl = "http://127.0.0.1:8765";
    private String apiKey = "";
    private int topK = 5;
    private double minScore = 0.35;
    private int connectTimeoutMs = 3_000;
    private int readTimeoutMs = 20_000;
}
