package com.gahyeonbot.models;

public class SearchResult {
    private final String streamUrl;
    private final String albumCoverUrl;

    public SearchResult(String streamUrl, String albumCoverUrl) {
        this.streamUrl = streamUrl;
        this.albumCoverUrl = albumCoverUrl;
    }

    public String getStreamUrl() {
        return streamUrl;
    }

    public String getAlbumCoverUrl() {
        return albumCoverUrl;
    }
}
