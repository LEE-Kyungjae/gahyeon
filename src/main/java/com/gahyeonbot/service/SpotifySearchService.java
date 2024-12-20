package com.gahyeonbot.service;

import com.gahyeonbot.config.ConfigLoader;
import com.wrapper.spotify.SpotifyApi;
import com.wrapper.spotify.model_objects.specification.Track;
import com.wrapper.spotify.requests.data.search.simplified.SearchTracksRequest;

public class SpotifySearchService {
    private final SpotifyApi spotifyApi;



    public SpotifySearchService() {
        // 환경 변수에서 CLIENT_ID와 CLIENT_SECRET 로드
        String clientId = System.getenv("SPOTIFY_CLIENT_ID");
        String clientSecret = System.getenv("SPOTIFY_CLIENT_SECRET");

        // 환경 변수가 없는 경우 ConfigLoader 사용
        if (clientId == null || clientId.isEmpty() || clientSecret == null || clientSecret.isEmpty()) {
            ConfigLoader configLoader = new ConfigLoader();
            clientId = configLoader.getSpotifyClientId();
            clientSecret = configLoader.getSpotifyClientSecret();
        }

        if (clientId == null || clientId.isEmpty() || clientSecret == null || clientSecret.isEmpty()) {
            throw new IllegalArgumentException("Spotify CLIENT_ID 또는 CLIENT_SECRET이 설정되지 않았습니다!");
        }
        // Spotify API 초기화
        spotifyApi = new SpotifyApi.Builder()
                .setClientId(clientId)
                .setClientSecret(clientSecret)
                .build();

        // 토큰 획득
        requestAccessToken();
    }

    /**
     * Spotify API 액세스 토큰 요청
     */
    private void requestAccessToken() {
        try {
            String accessToken = spotifyApi.clientCredentials().build().execute().getAccessToken();
            spotifyApi.setAccessToken(accessToken);
            System.out.println("Spotify API Access Token 요청 성공");
        } catch (Exception e) {
            System.err.println("액세스 토큰 요청 실패: " + e.getMessage());
        }
    }

    /**
     * Spotify 트랙 검색
     */
    public Track searchTrack(String query) {
        try {
            // Spotify에서 트랙 검색
            SearchTracksRequest searchTracksRequest = spotifyApi.searchTracks(query).build();
            Track[] tracks = searchTracksRequest.execute().getItems();

            if (tracks.length == 0) {
                return null; // 검색 결과 없음
            }

            return tracks[0]; // 첫 번째 검색 결과 반환
        } catch (Exception e) {
            System.err.println("Spotify 검색 실패: " + e.getMessage());
            return null;
        }
    }
}
