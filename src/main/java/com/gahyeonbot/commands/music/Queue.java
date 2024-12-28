package com.gahyeonbot.commands.music;

import com.gahyeonbot.commands.util.*;
import com.gahyeonbot.manager.music.GuildMusicManager;
import net.dv8tion.jda.api.events.interaction.command.SlashCommandInteractionEvent;
import net.dv8tion.jda.api.interactions.commands.build.OptionData;

import java.util.List;
import java.util.Map;

public class Queue extends AbstractCommand {

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
        logger.info("명령어 실행 시작: {}", getName());

        var guild = event.getGuild();

        if (guild == null) {
            ResponseUtil.replyError(event, "길드를 찾을 수 없습니다.");
            return;
        }

        var musicManager = musicManagers.get(guild.getIdLong());

        if (musicManager == null || musicManager.getQueue().isEmpty()) { // 변경된 부분
            ResponseUtil.replyError(event, "현재 대기열에 곡이 없습니다.");
            return;
        }

        var embed = EmbedUtil.createQueueEmbed(musicManager.getQueue()); // 변경된 부분
        ResponseUtil.replyEmbed(event, embed);
    }
}
