// 예약 관리 시스템 구현
package com.gahyeonbot.manager.scheduler;

import com.gahyeonbot.models.Reservation;

import java.util.*;
import java.util.concurrent.*;

public class LeaveSchedulerManagerImpl implements LeaveSchedulerManager {

    private final Map<Long, List<Reservation>> reservations = new ConcurrentHashMap<>();
    private final ScheduledExecutorService scheduler = Executors.newScheduledThreadPool(2);
    private long nextId = 1;

    @Override
    public synchronized long addReservation(Reservation reservation) {
        reservations.computeIfAbsent(reservation.getMemberId(), k -> new ArrayList<>()).add(reservation);
        return reservation.getId();
    }

    @Override
    public boolean cancelReservation(long reservationId) {
        for (List<Reservation> memberReservations : reservations.values()) {
            for (Iterator<Reservation> iterator = memberReservations.iterator(); iterator.hasNext(); ) {
                Reservation reservation = iterator.next();
                if (reservation.getId() == reservationId) {
                    reservation.getTask().cancel(false);
                    iterator.remove();
                    return true;
                }
            }
        }
        return false;
    }

    @Override
    public List<Reservation> getReservations(long memberId) {
        return reservations.getOrDefault(memberId, Collections.emptyList());
    }

    @Override
    public ScheduledFuture<?> scheduleTask(Runnable task, long delay, TimeUnit unit) {
        return scheduler.schedule(task, delay, unit);
    }

    @Override
    public synchronized long generateId() {
        return nextId++;
    }
}
