package com.gahyeonbot.commands.music;

import com.gahyeonbot.commands.util.ICommand;
import com.gahyeonbot.commands.util.Description;
import com.gahyeonbot.commands.util.ResponseUtil;
import com.gahyeonbot.commands.util.EmbedUtil;
import com.gahyeonbot.manager.music.GuildMusicManager;
import net.dv8tion.jda.api.events.interaction.command.SlashCommandInteractionEvent;
import net.dv8tion.jda.api.interactions.commands.build.OptionData;

import java.util.List;
import java.util.Map;

public class Clear implements ICommand {

    private final Map<Long, GuildMusicManager> musicManagers;

    public Clear(Map<Long, GuildMusicManager> musicManagers) {
        this.musicManagers = musicManagers;
    }

    @Override
    public String getName() {
        return Description.CLEAR_NAME;
    }

    @Override
    public String getDescription() {
        return Description.CLEAR_DESC;
    }

    @Override
    public String getDetailedDescription() {
        return Description.CLEAR_DETAIL;
    }

    @Override
    public List<OptionData> getOptions() {
        return List.of();
    }

    @Override
    public void execute(SlashCommandInteractionEvent event) {
        var guild = event.getGuild();

        if (guild == null) {
            ResponseUtil.replyError(event, "길드를 찾을 수 없습니다.");
            return;
        }

        var musicManager = musicManagers.get(guild.getIdLong());

        if (musicManager == null || !musicManager.isPlaying()) {
            ResponseUtil.replyError(event, "현재 재생 중인 음악이 없습니다.");
            return;
        }

        // 음악 정지 및 대기열 초기화
        musicManager.stopPlayback(guild.getAudioManager());

        // 응답 전송
        var embed = EmbedUtil.createMusicStopEmbed(event);
        ResponseUtil.replyEmbed(event, embed);
    }
}
