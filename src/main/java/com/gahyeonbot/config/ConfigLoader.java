package com.gahyeonbot.config;

import org.yaml.snakeyaml.Yaml;

import java.io.InputStream;
import java.util.Map;

public class ConfigLoader {

    private final Map<String, String> config;

    public ConfigLoader() {
        Yaml yaml = new Yaml();
        InputStream inputStream = getClass().getResourceAsStream("/application.yml");

        if (inputStream != null) {
            config = yaml.load(inputStream);
        } else {
            config = System.getenv();
        }

    }
    // 설정 로드 메서드
    public String getApplicationId() {
        return getValue("APPLICATION_ID");
    }
    public String getToken() {
        return getValue("TOKEN");
    }
    public String getSpotifyClientId() {
        return getValue("SPOTIFY_CLIENT_ID");
    }

    public String getSpotifyClientSecret() {
        return getValue("SPOTIFY_CLIENT_SECRET");
    }

    public String getValue(String key) {
        String value = config.get(key);
        if (value == null || value.isEmpty()) {
            value = System.getenv(key);
            if (value == null || value.isEmpty()) {
                throw new IllegalArgumentException("환경 변수 '" + key + "'이(가) 설정되지 않았습니다.");
            }
        }
        return value;
    }
}
