package com.gahyeonbot.manager.music;

import com.sedmelluq.discord.lavaplayer.track.AudioTrack;
import java.util.concurrent.BlockingQueue;
import java.util.concurrent.LinkedBlockingQueue;
import java.util.List;

public class TrackQueue {
    private final BlockingQueue<AudioTrack> queue = new LinkedBlockingQueue<>();

    public void addTrack(AudioTrack track) {
        queue.offer(track);
    }

    public AudioTrack pollTrack() {
        return queue.poll();
    }

    public List<AudioTrack> getTracks() {
        return List.copyOf(queue);
    }

    public boolean isEmpty() {
        return queue.isEmpty();
    }

    public void clear() {
        queue.clear();
    }
}
