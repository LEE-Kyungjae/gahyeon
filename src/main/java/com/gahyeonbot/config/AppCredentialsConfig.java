package com.gahyeonbot.config;

import lombok.Getter;
import lombok.Setter;
import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.stereotype.Component;

// AppCredentialsConfig.java
@Component
@ConfigurationProperties(prefix = "app.credentials")
@Getter
@Setter
public class AppCredentialsConfig {
    private String applicationId;
    private String token;
    private String spotifyClientId;
    private String spotifyClientSecret;
}
