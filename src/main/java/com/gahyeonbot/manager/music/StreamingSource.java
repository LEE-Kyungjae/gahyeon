package com.gahyeonbot.manager.music;

public interface StreamingSource {
    /**
     * 스트리밍 URL 가져오기
     * @param query 검색할 트랙 정보
     * @return 스트리밍 URL
     */
    String getStreamUrl(String query);

    /**
     * 트랙의 메타데이터 가져오기 (선택사항)
     * @param query 검색할 트랙 정보
     * @return 트랙 메타데이터
     */
    String getTrackMetadata(String query);
}
