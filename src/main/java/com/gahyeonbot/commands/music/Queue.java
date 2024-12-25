package com.gahyeonbot.commands.music;

import com.gahyeonbot.commands.base.ICommand;
import com.gahyeonbot.commands.base.Description;
import com.gahyeonbot.manager.music.GuildMusicManager;
import com.sedmelluq.discord.lavaplayer.track.AudioTrack;
import net.dv8tion.jda.api.events.interaction.command.SlashCommandInteractionEvent;
import net.dv8tion.jda.api.interactions.commands.build.OptionData;

import java.util.List;
import java.util.Map;
import java.util.StringJoiner;

public class Queue implements ICommand {

    private final Map<Long, GuildMusicManager> musicManagers;

    public Queue(Map<Long, GuildMusicManager> musicManagers) {
        this.musicManagers = musicManagers;
    }

    @Override
    public String getName() {
        return Description.QUEUE_NAME;
    }

    @Override
    public String getDescription() {
        return Description.QUEUE_DESC;
    }

    @Override
    public String getDetailedDescription() {
        return Description.QUEUE_DETAIL;
    }

    @Override
    public List<OptionData> getOptions() {
        return List.of();
    }

    @Override
    public void execute(SlashCommandInteractionEvent event) {
        var guild = event.getGuild();

        if (guild == null) {
            event.reply("길드를 찾을 수 없습니다.").setEphemeral(true).queue();
            return;
        }

        var musicManager = musicManagers.get(guild.getIdLong());

        if (musicManager == null || musicManager.scheduler.getQueue().isEmpty()) {
            event.reply("현재 대기열에 곡이 없습니다.").setEphemeral(true).queue();
            return;
        }

        StringJoiner queueMessage = new StringJoiner("\n");
        List<AudioTrack> tracks = musicManager.scheduler.getQueue();

        for (int i = 0; i < tracks.size(); i++) {
            AudioTrack track = tracks.get(i);
            queueMessage.add((i + 1) + ". " + track.getInfo().title + " - " + formatDuration(track.getDuration()));
        }

        event.reply("🎶 **현재 대기열:**\n" + queueMessage).queue();
    }

    private String formatDuration(long durationMillis) {
        long minutes = (durationMillis / 1000) / 60;
        long seconds = (durationMillis / 1000) % 60;
        return String.format("%02d:%02d", minutes, seconds);
    }
}