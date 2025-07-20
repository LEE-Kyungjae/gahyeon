package com.gahyeonbot.services.streaming;

import com.gahyeonbot.config.ConfigLoader;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import se.michaelthelin.spotify.SpotifyApi;
import se.michaelthelin.spotify.model_objects.specification.Track;
import se.michaelthelin.spotify.requests.authorization.client_credentials.ClientCredentialsRequest;
import se.michaelthelin.spotify.requests.data.search.simplified.SearchTracksRequest;

import java.util.concurrent.Executors;
import java.util.concurrent.ScheduledExecutorService;
import java.util.concurrent.TimeUnit;

/**
 * Spotify 검색 및 토큰 관리 서비스 구현체
 */
public class SpotifySearchService {
    private static final Logger logger = LoggerFactory.getLogger(SpotifySearchService.class);
    private final SpotifyApi spotifyApi;
    private final ScheduledExecutorService scheduler;
    private static final long TOKEN_REFRESH_INTERVAL = 3600; // 초 단위

    /**
     * 기본 생성자
     * ConfigLoader를 사용하여 Spotify API 설정을 로드합니다.
     */
    public SpotifySearchService() {
        this(new ConfigLoader(), Executors.newScheduledThreadPool(1));
    }

    /**
     * 의존성 주입 가능한 생성자
     *
     * @param configLoader 설정 로더
     * @param scheduler    토큰 갱신용 스케줄러
     */
    public SpotifySearchService(ConfigLoader configLoader, ScheduledExecutorService scheduler) {
        this.scheduler = scheduler;

        String clientId = configLoader.getSpotifyClientId();
        String clientSecret = configLoader.getSpotifyClientSecret();

        if (clientId == null || clientId.isEmpty() || clientSecret == null || clientSecret.isEmpty()) {
            throw new IllegalArgumentException("Spotify CLIENT_ID 또는 CLIENT_SECRET이 설정되지 않았습니다!");
        }

        this.spotifyApi = new SpotifyApi.Builder()
                .setClientId(clientId)
                .setClientSecret(clientSecret)
                .build();

        refreshAccessToken();
        scheduleTokenRefresh();
    }

    /**
     * Spotify 트랙 검색
     *
     * @param query 검색할 트랙 이름 또는 키워드
     * @return 첫 번째 검색 결과로 반환된 Track 객체, 검색 결과가 없으면 null
     */
    public Track searchTrack(String query) {
        try {
            SearchTracksRequest searchTracksRequest = spotifyApi.searchTracks(query).build();
            var pagingTracks = searchTracksRequest.execute(); // 최신 API는 execute() 호출을 비동기로 제공 가능성 있음

            if (pagingTracks.getItems().length == 0) {
                logger.warn("Spotify 검색 결과가 없습니다. 쿼리: {}", query);
                return null;
            }

            logger.info("Spotify 검색 성공. 첫 번째 결과: {}", pagingTracks.getItems()[0].getName());
            return pagingTracks.getItems()[0];
        } catch (Exception e) {
            logger.error("Spotify 검색 실패. 쿼리: {}", query, e);
            return null;
        }
    }

    public String getAlbumCoverUrl(Track track) {
        if (track.getAlbum() != null && track.getAlbum().getImages().length > 0) {
            return track.getAlbum().getImages()[0].getUrl();
        }
        logger.warn("앨범 커버 이미지를 찾을 수 없습니다. 트랙: {}", track.getName());
        return null;
    }

    /**
     * Spotify API 액세스 토큰 갱신
     */
    public void refreshAccessToken() {
        try {
            ClientCredentialsRequest clientCredentialsRequest = spotifyApi.clientCredentials().build();
            var credentials = clientCredentialsRequest.execute();

            spotifyApi.setAccessToken(credentials.getAccessToken());
            logger.info("Spotify API Access Token 갱신 성공. 유효 기간: {}초", credentials.getExpiresIn());
        } catch (Exception e) {
            logger.error("Spotify Access Token 갱신 실패", e);
        }
    }

    public SpotifyApi getSpotifyApi() {
        return null;
    }

    public void authenticate() throws Exception {

    }

    /**
     * 액세스 토큰 갱신 작업 스케줄링
     */
    private void scheduleTokenRefresh() {
        scheduler.scheduleAtFixedRate(() -> {
            logger.info("액세스 토큰 갱신 작업 실행");
            refreshAccessToken();
        }, TOKEN_REFRESH_INTERVAL, TOKEN_REFRESH_INTERVAL, TimeUnit.SECONDS);
    }

    /**
     * 서비스 종료
     */
    public void shutdown() {
        logger.info("SpotifySearchService 종료. 스케줄러 종료");
        scheduler.shutdown();
        try {
            if (!scheduler.awaitTermination(60, TimeUnit.SECONDS)) {
                scheduler.shutdownNow();
            }
        } catch (InterruptedException e) {
            logger.error("스케줄러 종료 실패", e);
            scheduler.shutdownNow();
            Thread.currentThread().interrupt();
        }
    }
}
