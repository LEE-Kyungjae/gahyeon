package com.gahyeonbot.models;

/**
 * 음악 검색 결과를 담는 데이터 클래스.
 * 스트리밍 URL과 앨범 커버 URL을 포함합니다.
 * 
 * @author GahyeonBot Team
 * @version 1.0
 */
public class SearchResult {
    private final String streamUrl;
    private final String albumCoverUrl;

    /**
     * SearchResult 생성자.
     * 
     * @param streamUrl 음악 스트리밍 URL
     * @param albumCoverUrl 앨범 커버 이미지 URL
     */
    public SearchResult(String streamUrl, String albumCoverUrl) {
        this.streamUrl = streamUrl;
        this.albumCoverUrl = albumCoverUrl;
    }

    /**
     * 음악 스트리밍 URL을 반환합니다.
     * 
     * @return 스트리밍 URL
     */
    public String getStreamUrl() {
        return streamUrl;
    }

    /**
     * 앨범 커버 이미지 URL을 반환합니다.
     * 
     * @return 앨범 커버 URL
     */
    public String getAlbumCoverUrl() {
        return albumCoverUrl;
    }
}
