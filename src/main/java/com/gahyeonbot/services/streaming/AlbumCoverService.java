package com.gahyeonbot.services.streaming;

import com.gahyeonbot.services.streaming.SpotifySearchService;

/**
 * 앨범 커버 이미지를 처리하는 서비스 클래스.
 * 음악의 앨범 커버 URL을 관리하고 제공합니다.
 * 
 * @author GahyeonBot Team
 * @version 1.0
 */
public class AlbumCoverService {
    private final SpotifySearchService spotifySearchService;

    public AlbumCoverService(SpotifySearchService spotifySearchService) {
        this.spotifySearchService = spotifySearchService;
    }

    /**
     * 앨범 커버 URL을 가져옵니다.
     * 
     * @param query 검색 쿼리
     * @return 앨범 커버 URL
     */
    public String getAlbumCover(String query) {
        var track = spotifySearchService.searchTrack(query);
        return (track != null && track.getAlbum() != null && track.getAlbum().getImages().length > 0)
                ? track.getAlbum().getImages()[0].getUrl()
                : null; // 기본 URL은 EmbedUtil에서 처리
    }
}
