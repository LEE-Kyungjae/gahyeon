package com.gahyeonbot.listeners;

import com.gahyeonbot.commands.base.ICommand;
import net.dv8tion.jda.api.entities.Guild;
import net.dv8tion.jda.api.events.guild.GuildReadyEvent;
import net.dv8tion.jda.api.events.interaction.command.SlashCommandInteractionEvent;
import net.dv8tion.jda.api.hooks.ListenerAdapter;
import net.dv8tion.jda.api.sharding.ShardManager;
import org.jetbrains.annotations.NotNull;

import java.util.ArrayList;
import java.util.List;

public class CommandManager extends ListenerAdapter {
    private final List<ICommand> commands = new ArrayList<>();
    private ShardManager shardManager;

    public void setShardManager(ShardManager shardManager) {
        this.shardManager = shardManager;
    }

    //전역 커멘드 : 한계없음. 업데이트까지 시간이걸림
//    @Override
//    public void onReady(@NotNull ReadyEvent event) {
//        //  커멘드를 삭제하고 재등록할떄만 한번 작동시키면 됨
//        shardManager.getGuilds().forEach(guild -> {
//            // 모든 길드에 대해 커맨드 조회 후 삭제
//            guild.retrieveCommands().queue(commands -> {
//                commands.forEach(command -> {
//                    // 커맨드를 하나씩 삭제
//                    guild.deleteCommandById(command.getId()).queue(
//                            success -> {
//                                System.out.println("Command deleted: " + command.getName());
//                            },
//                            error -> System.err.println("Failed to delete command: " + command.getName())
//                    );
//                });
//            });
//        });
//        for (Guild guild : event.getJDA().getGuilds()) {
//            for (ICommand command : commands) {
//                guild.upsertCommand(command.getName(), command.getDescription()).addOptions(command.getOptions()).queue();
//            }
//        }
//    }

    //길드 커멘드 : 최대 100개까지 제한
    @Override
    public void onGuildReady(@NotNull GuildReadyEvent event) {
        for (Guild guild : event.getJDA().getGuilds()) {
            for (ICommand command : commands) {
                //guild.upsertCommand(command.getName(), command.getDescription()).addOptions(command.getOptions()).queue();
            }
        }
    }


    @Override
    public void onSlashCommandInteraction(@NotNull SlashCommandInteractionEvent event) {
        for (ICommand command : commands) {
            if (command.getName().equals(event.getName())) {
                command.execute(event);
                return;
            }
        }
    }

    public void add(ICommand command) {
        commands.add(command);
    }
}