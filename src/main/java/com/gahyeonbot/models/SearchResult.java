package com.gahyeonbot.models;

import lombok.Getter;
import lombok.AllArgsConstructor;

/**
 * 음악 검색 결과를 담는 데이터 클래스.
 * 스트리밍 URL과 앨범 커버 URL을 포함합니다.
 *
 * @author GahyeonBot Team
 * @version 1.0
 */
@Getter
@AllArgsConstructor
public class SearchResult {
    private final String streamUrl;
    private final String albumCoverUrl;
}
