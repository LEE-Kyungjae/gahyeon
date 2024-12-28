package com.gahyeonbot.service;

public class AlbumCoverService {
    private final SpotifySearchService spotifySearchService;

    public AlbumCoverService(SpotifySearchService spotifySearchService) {
        this.spotifySearchService = spotifySearchService;
    }

    public String getAlbumCover(String query) {
        var track = spotifySearchService.searchTrack(query);
        return (track != null && track.getAlbum() != null && track.getAlbum().getImages().length > 0)
                ? track.getAlbum().getImages()[0].getUrl()
                : null; // 기본 URL은 EmbedUtil에서 처리
    }
}
