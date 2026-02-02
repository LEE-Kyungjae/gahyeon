package com.gahyeonbot.models;

import lombok.Getter;
import lombok.AllArgsConstructor;

import java.time.Duration;
import java.time.LocalDateTime;
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
    private final LocalDateTime createdAt;
    private final LocalDateTime executeAt;
    private final int delayMinutes;

    public Reservation(
            long id,
            long memberId,
            String memberName,
            long guildId,
            ScheduledFuture<?> task,
            String description,
            int delayMinutes
    ) {
        this(id, memberId, memberName, guildId, task, description,
                LocalDateTime.now(), LocalDateTime.now().plusMinutes(delayMinutes), delayMinutes);
    }

    public long getRemainingMinutes() {
        return Math.max(0, Duration.between(LocalDateTime.now(), executeAt).toMinutes());
    }
}
