package com.gahyeonbot.commands.music;

import com.gahyeonbot.commands.util.Description;
import com.gahyeonbot.commands.util.ICommand;
import com.gahyeonbot.commands.util.ResponseUtil;
import com.gahyeonbot.commands.util.EmbedUtil;
import com.gahyeonbot.manager.music.GuildMusicManager;
import net.dv8tion.jda.api.events.interaction.command.SlashCommandInteractionEvent;
import net.dv8tion.jda.api.interactions.commands.build.OptionData;

import java.util.List;
import java.util.Map;

public class Skip implements ICommand {

    private final Map<Long, GuildMusicManager> musicManagers;

    public Skip(Map<Long, GuildMusicManager> musicManagers) {
        this.musicManagers = musicManagers;
    }

    @Override
    public String getName() {
        return Description.SKIP_NAME;
    }

    @Override
    public String getDescription() {
        return Description.SKIP_DESC;
    }

    @Override
    public String getDetailedDescription() {
        return Description.SKIP_DETAIL;
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
            ResponseUtil.replyError(event, "현재 재생 중인 트랙이 없습니다.");
            return;
        }

        var currentTrack = musicManager.getCurrentTrack();
        boolean trackSkipped = musicManager.skipCurrentTrack();

        if (trackSkipped) {
            var embed = EmbedUtil.createSkipEmbed(event, currentTrack.getInfo().title);
            ResponseUtil.replyEmbed(event, embed);
        } else {
            ResponseUtil.replyError(event, "트랙을 건너뛸 수 없습니다.");
        }
    }
}
