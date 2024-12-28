package com.gahyeonbot.service;

import com.gahyeonbot.manager.music.StreamingSource;

public class StreamingService {
    private final SpotifySearchService spotifySearchService;
    private final StreamingSource streamingSource;

    public StreamingService(SpotifySearchService spotifySearchService, StreamingSource streamingSource) {
        this.spotifySearchService = spotifySearchService;
        this.streamingSource = streamingSource;
    }

    public String getStreamUrl(String query) {
        var track = spotifySearchService.searchTrack(query);
        if (track != null) {
            String fullQuery = track.getName() + " " + track.getArtists()[0].getName();
            return streamingSource.getStreamUrl(fullQuery);
        }
        return streamingSource.getStreamUrl(query);
    }
}
