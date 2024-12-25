package com.gahyeonbot.commands.music;

import com.gahyeonbot.commands.base.ICommand;
import com.gahyeonbot.commands.base.Description;
import com.gahyeonbot.manager.music.GuildMusicManager;
import net.dv8tion.jda.api.EmbedBuilder;
import net.dv8tion.jda.api.events.interaction.command.SlashCommandInteractionEvent;
import net.dv8tion.jda.api.interactions.commands.build.OptionData;

import java.awt.*;
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
            event.reply("길드를 찾을 수 없습니다.").setEphemeral(true).queue();
            return;
        }

        var musicManager = musicManagers.get(guild.getIdLong());

        if (musicManager == null || musicManager.player.getPlayingTrack() == null) {
            event.reply("현재 재생 중인 트랙이 없습니다.").setEphemeral(true).queue();
            return;
        }

        musicManager.player.stopTrack();
        musicManager.scheduler.clearQueue();
        guild.getAudioManager().closeAudioConnection();
        EmbedBuilder embed = new EmbedBuilder();
        embed.setTitle("🛑 재생 종료")
                .setDescription("음악 재생이 종료되었습니다.")
                .setColor(Color.RED)
                .setFooter("요청자: " + event.getUser().getName(), event.getUser().getAvatarUrl());

        event.replyEmbeds(embed.build()).queue();
    }
}
