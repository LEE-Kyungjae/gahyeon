package com.gahyeonbot.commands.music;

import com.gahyeonbot.commands.Description;
import com.gahyeonbot.commands.ICommand;
import com.gahyeonbot.manager.music.GuildMusicManager;
import net.dv8tion.jda.api.events.interaction.command.SlashCommandInteractionEvent;
import net.dv8tion.jda.api.interactions.commands.build.OptionData;

import java.util.List;
import java.util.Map;

public class Resume implements ICommand {
    private final Map<Long, GuildMusicManager> musicManagers;

    public Resume(Map<Long, GuildMusicManager> musicManagers) {
        this.musicManagers = musicManagers;
    }
    @Override
    public String getName() {
        return Description.RESUME_NAME;
    }

    @Override
    public String getDescription() {
        return Description.RESUME_DESC;
    }

    @Override
    public String getDetailedDescription() {
        return Description.RESUME_DETAIL;
    }

    @Override
    public List<OptionData> getOptions() {
        return List.of();
    }

    @Override
    public void execute(SlashCommandInteractionEvent event) {
        var guild = event.getGuild();
        if (guild == null) {
            event.reply("길드 정보를 가져올 수 없습니다.").setEphemeral(true).queue();
            return;
        }

        GuildMusicManager musicManager = musicManagers.get(guild.getIdLong());
        if (musicManager == null) {
            event.reply("현재 재생 중인 음악이 없습니다.").setEphemeral(true).queue();
            return;
        }

        if (musicManager.player.getPlayingTrack() == null) {
            event.reply("현재 재생 중인 트랙이 없습니다.").setEphemeral(true).queue();
            return;
        }

        if (!musicManager.player.isPaused()) {
            event.reply("음악이 이미 재생 중입니다.").setEphemeral(true).queue();
        } else {
            musicManager.player.setPaused(false); // 일시정지 해제
            event.reply("음악 재생이 다시 시작되었습니다.").queue();
        }
    }
}
