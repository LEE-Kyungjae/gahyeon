package com.gahyeonbot.commands.util;

import net.dv8tion.jda.api.events.interaction.command.SlashCommandInteractionEvent;

import net.dv8tion.jda.api.interactions.commands.build.OptionData;

import java.util.List;

public interface ICommand {
    String getName();
    String getDescription();
    String getDetailedDescription();
    List<OptionData> getOptions();

    void execute(SlashCommandInteractionEvent event);
}
