package com.gahyeonbot.services.streaming;

import se.michaelthelin.spotify.model_objects.specification.Track;
import com.gahyeonbot.models.SearchResult;
import com.gahyeonbot.services.streaming.SpotifySearchService;

/**
 * 일반 오디오 검색 서비스 클래스.
 * YouTube 등의 플랫폼에서 음악을 검색합니다.
 * 
 * @author GahyeonBot Team
 * @version 1.0
 */
public class AudioSearchService {
    private final SpotifySearchService spotifySearchService;

    public AudioSearchService(SpotifySearchService spotifySearchService) {
        this.spotifySearchService = spotifySearchService;
    }

    /**
     * 음악을 검색하고 스트리밍 정보를 반환합니다.
     * 
     * @param query 검색 쿼리
     * @return 검색 결과 (스트리밍 URL, 앨범 커버 URL 포함)
     */
    public SearchResult search(String query) {
        // TODO: YouTube 검색 구현
        return null;
    }

    public Track searchTrack(String query) {
        return spotifySearchService.searchTrack(query); // Spotify 검색
    }
}
