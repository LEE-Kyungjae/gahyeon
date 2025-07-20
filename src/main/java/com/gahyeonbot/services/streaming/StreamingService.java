package com.gahyeonbot.services.streaming;

import com.gahyeonbot.core.audio.StreamingSource;
import com.gahyeonbot.models.SearchResult;
import net.dv8tion.jda.api.events.interaction.command.SlashCommandInteractionEvent;

import java.util.List;

/**
 * 음악 스트리밍 서비스를 관리하는 클래스.
 * 다양한 음악 플랫폼에서 음악을 검색하고 스트리밍 URL을 제공합니다.
 * 
 * @author GahyeonBot Team
 * @version 1.0
 */
public class StreamingService {
    private final SpotifySearchService spotifySearchService;
    private final StreamingSource streamingSource;

    /**
     * StreamingService 생성자.
     * 
     * @param spotifySearchService Spotify 검색 서비스
     * @param streamingSource 스트리밍 소스
     */
    public StreamingService(SpotifySearchService spotifySearchService, StreamingSource streamingSource) {
        this.spotifySearchService = spotifySearchService;
        this.streamingSource = streamingSource;
    }

    /**
     * Spotify와 SoundCloud 데이터를 조합하여 검색 결과를 반환합니다.
     *
     * @param query 사용자 입력 쿼리
     * @return SearchResult 객체
     */
    public SearchResult search(String query) {
        // Step 1: Spotify 검색
        var track = spotifySearchService.searchTrack(query);

        String albumCoverUrl = null;
        String streamUrl;

        if (track != null) {
            // Spotify에서 데이터 가져오기
            albumCoverUrl = spotifySearchService.getAlbumCoverUrl(track);

            // SoundCloud에서 스트림 URL 생성
            String fullQuery = track.getName() + " " + track.getArtists()[0].getName();
            streamUrl = streamingSource.getStreamUrl(fullQuery);
        } else {
            // Spotify 결과가 없으면 사용자가 입력한 쿼리로 SoundCloud 검색
            streamUrl = streamingSource.getStreamUrl(query);
        }

        return new SearchResult(streamUrl, albumCoverUrl);
    }
}
