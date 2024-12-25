package com.gahyeonbot.service;

import com.wrapper.spotify.model_objects.specification.Track;

/**
 * Spotify 검색 관련 서비스 인터페이스
 */
public interface SpotifyService {

    /**
     * Spotify 트랙 검색 메서드
     *
     * @param query 검색할 트랙 이름 또는 키워드
     * @return 첫 번째 검색 결과로 반환된 Track 객체, 검색 결과가 없으면 null
     */
    Track searchTrack(String query);
}
