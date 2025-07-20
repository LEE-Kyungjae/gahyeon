package com.gahyeonbot.models;

import java.util.concurrent.ScheduledFuture;

/**
 * 예약된 작업을 나타내는 데이터 클래스.
 * 사용자가 예약한 작업의 정보와 실행될 스케줄된 작업을 포함합니다.
 * 
 * @author GahyeonBot Team
 * @version 1.0
 */
public class Reservation {
    private final long id;
    private final long memberId;
    private final String memberName;
    private final long guildId;
    private final ScheduledFuture<?> task;
    private final String description;

    /**
     * Reservation 생성자.
     * 
     * @param id 예약 고유 ID
     * @param memberId 예약한 멤버의 Discord ID
     * @param memberName 예약한 멤버의 이름
     * @param guildId 서버 ID
     * @param task 스케줄된 작업
     * @param description 예약 작업 설명
     */
    public Reservation(long id, long memberId, String memberName, long guildId, ScheduledFuture<?> task, String description) {
        this.id = id;
        this.memberId = memberId;
        this.memberName = memberName;
        this.guildId = guildId;
        this.task = task;
        this.description = description;
    }

    /**
     * 예약 고유 ID를 반환합니다.
     * 
     * @return 예약 ID
     */
    public long getId() {
        return id;
    }

    /**
     * 예약한 멤버의 Discord ID를 반환합니다.
     * 
     * @return 멤버 ID
     */
    public long getMemberId() {
        return memberId;
    }

    /**
     * 예약한 멤버의 이름을 반환합니다.
     * 
     * @return 멤버 이름
     */
    public String getMemberName() {
        return memberName;
    }

    /**
     * 서버 ID를 반환합니다.
     * 
     * @return 서버 ID
     */
    public long getGuildId() {
        return guildId;
    }

    /**
     * 스케줄된 작업을 반환합니다.
     * 
     * @return 스케줄된 작업
     */
    public ScheduledFuture<?> getTask() {
        return task;
    }

    /**
     * 예약 작업의 설명을 반환합니다.
     * 
     * @return 작업 설명
     */
    public String getDescription() {
        return description;
    }
}