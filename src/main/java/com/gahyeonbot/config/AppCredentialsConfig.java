package com.gahyeonbot.config;

import jakarta.validation.constraints.NotBlank;
import lombok.Getter;
import lombok.Setter;
import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.stereotype.Component;
import org.springframework.validation.annotation.Validated;

// AppCredentialsConfig.java
@Component
@ConfigurationProperties(prefix = "app.credentials")
@Validated
@Getter
@Setter
public class AppCredentialsConfig {

    @NotBlank(message = "APPLICATION_ID 환경변수가 설정되지 않았습니다")
    private String applicationId;

    @NotBlank(message = "TOKEN 환경변수가 설정되지 않았습니다")
    private String token;

    @NotBlank(message = "SPOTIFY_CLIENT_ID 환경변수가 설정되지 않았습니다")
    private String spotifyClientId;

    @NotBlank(message = "SPOTIFY_CLIENT_SECRET 환경변수가 설정되지 않았습니다")
    private String spotifyClientSecret;

    /**
     * OpenAI API Key (선택적)
     * 설정되지 않으면 OpenAI 기능이 비활성화됩니다.
     */
    private String openaiApiKey;
}
