package com.gahyeonbot.service;

import com.wrapper.spotify.model_objects.specification.Track;

/**
 * Spotify 검색 및 정보 제공 서비스 인터페이스
 */
public interface SpotifyService {

    /**
     * Spotify 트랙 검색 메서드
     *
     * @param query 검색할 트랙 이름 또는 키워드
     * @return 첫 번째 검색 결과로 반환된 Track 객체, 검색 결과가 없으면 null
     */
    Track searchTrack(String query);

    /**
     * 트랙의 앨범 커버 URL을 반환하는 메서드
     *
     * @param track 앨범 커버를 추출할 트랙 객체
     * @return 앨범 커버 URL, 없으면 null
     */
    String getAlbumCoverUrl(Track track);

    /**
     * Spotify API 초기화 및 토큰 갱신 메서드
     * (Optional: 필요 시 수동으로 토큰을 갱신)
     */
    void refreshAccessToken();
}
