package com.gahyeonbot.services.streaming;

import se.michaelthelin.spotify.SpotifyApi;
import se.michaelthelin.spotify.model_objects.specification.Track;

/**
 * Spotify 서비스 인터페이스.
 * Spotify API와의 상호작용을 위한 메서드들을 정의합니다.
 * 
 * @author GahyeonBot Team
 * @version 1.0
 */
public interface SpotifyService {
    
    /**
     * Spotify 트랙 검색.
     * 
     * @param query 검색할 트랙 이름 또는 키워드
     * @return 첫 번째 검색 결과로 반환된 Track 객체, 검색 결과가 없으면 null
     */
    Track searchTrack(String query);
    
    /**
     * 트랙의 앨범 커버 URL 반환.
     * 
     * @param track 앨범 커버를 추출할 트랙 객체
     * @return 앨범 커버 URL, 없으면 null
     */
    String getAlbumCoverUrl(Track track);
    
    /**
     * Spotify API 액세스 토큰 갱신.
     */
    void refreshAccessToken();
    
    /**
     * Spotify API 인스턴스 반환.
     * 
     * @return SpotifyApi 인스턴스
     */
    SpotifyApi getSpotifyApi();
    
    /**
     * Spotify API 인증.
     * 
     * @throws Exception 인증 실패 시 발생
     */
    void authenticate() throws Exception;
}
