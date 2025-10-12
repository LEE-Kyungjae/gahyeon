package com.gahyeonbot.models;

import lombok.Getter;
import lombok.AllArgsConstructor;

import java.util.concurrent.ScheduledFuture;

/**
 * 예약된 작업을 나타내는 데이터 클래스.
 * 사용자가 예약한 작업의 정보와 실행될 스케줄된 작업을 포함합니다.
 *
 * @author GahyeonBot Team
 * @version 1.0
 */
@Getter
@AllArgsConstructor
public class Reservation {
    private final long id;
    private final long memberId;
    private final String memberName;
    private final long guildId;
    private final ScheduledFuture<?> task;
    private final String description;
}