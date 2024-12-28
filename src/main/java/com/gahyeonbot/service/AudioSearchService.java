package com.gahyeonbot.service;

import com.wrapper.spotify.model_objects.specification.Track;
/*

음악 검색 관련 서비스 제공.
특정 음악 소스에 대한 검색 작업 수행.
*/
public class AudioSearchService {
    private final SpotifySearchService spotifySearchService;

    public AudioSearchService(SpotifySearchService spotifySearchService) {
        this.spotifySearchService = spotifySearchService;
    }

    public Track searchTrack(String query) {
        return spotifySearchService.searchTrack(query); // Spotify 검색
    }
}
