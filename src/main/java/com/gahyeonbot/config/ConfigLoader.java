package com.gahyeonbot.config;

import org.yaml.snakeyaml.Yaml;

import java.io.InputStream;
import java.util.Map;

/**
 * 봇 설정을 로드하는 클래스.
 * YAML 파일과 환경 변수에서 설정값을 읽어오며, 
 * Discord 토큰, Spotify API 키 등의 설정을 관리합니다.
 * 
 * @author GahyeonBot Team
 * @version 1.0
 */

public class ConfigLoader {

    private final Map<String, String> config;

    /**
     * ConfigLoader 생성자.
     * application.yml 파일을 우선적으로 로드하고, 
     * 파일이 없는 경우 환경 변수에서 설정을 읽어옵니다.
     */
    public ConfigLoader() {
        Yaml yaml = new Yaml();
        InputStream inputStream = getClass().getResourceAsStream("/application.yml");

        if (inputStream != null) {
            config = yaml.load(inputStream);
        } else {
            config = System.getenv();
        }

    }
    
    /**
     * Discord 애플리케이션 ID를 반환합니다.
     * 
     * @return Discord 애플리케이션 ID
     * @throws IllegalArgumentException 설정이 없는 경우
     */
    public String getApplicationId() {
        return getValue("APPLICATION_ID");
    }
    
    /**
     * Discord 봇 토큰을 반환합니다.
     * 
     * @return Discord 봇 토큰
     * @throws IllegalArgumentException 설정이 없는 경우
     */
    public String getToken() {
        return getValue("TOKEN");
    }
    
    /**
     * Spotify 클라이언트 ID를 반환합니다.
     * 
     * @return Spotify 클라이언트 ID
     * @throws IllegalArgumentException 설정이 없는 경우
     */
    public String getSpotifyClientId() {
        return getValue("SPOTIFY_CLIENT_ID");
    }

    /**
     * Spotify 클라이언트 시크릿을 반환합니다.
     * 
     * @return Spotify 클라이언트 시크릿
     * @throws IllegalArgumentException 설정이 없는 경우
     */
    public String getSpotifyClientSecret() {
        return getValue("SPOTIFY_CLIENT_SECRET");
    }

    /**
     * 지정된 키에 해당하는 설정값을 반환합니다.
     * 먼저 YAML 설정에서 찾고, 없으면 환경 변수에서 찾습니다.
     * 
     * @param key 설정 키
     * @return 설정값
     * @throws IllegalArgumentException 설정이 없는 경우
     */
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
