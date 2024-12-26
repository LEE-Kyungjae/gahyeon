package com.gahyeonbot.listeners;

import com.gahyeonbot.commands.ICommand;
import net.dv8tion.jda.api.events.interaction.command.SlashCommandInteractionEvent;
import net.dv8tion.jda.api.hooks.ListenerAdapter;
import net.dv8tion.jda.api.sharding.ShardManager;
import org.jetbrains.annotations.NotNull;

import java.util.ArrayList;
import java.util.List;
/*
명령어를 처리하는 주요 역할을 담당하며, ICommand를 통해 구체적인 명령어를 구현합니다.
*/
public class CommandManager extends ListenerAdapter {
    private final List<ICommand> commands = new ArrayList<>();
    private ShardManager shardManager;

    public void setShardManager(ShardManager shardManager) {
        this.shardManager = shardManager;
    }


    public void synchronizeCommands() {
        if (shardManager == null) {
            System.err.println("ShardManager가 설정되지 않았습니다!");
            return;
        }

        shardManager.getGuilds().forEach(guild -> {
            guild.retrieveCommands().queue(existingCommands -> {
                // 기존 명령어와 새 명령어 리스트를 비교
                List<String> existingCommandNames = existingCommands.stream()
                        .map(command -> command.getName())
                        .toList();

                // 추가할 명령어
                commands.stream()
                        .filter(command -> !existingCommandNames.contains(command.getName()))
                        .forEach(command -> guild.upsertCommand(command.getName(), command.getDescription())
                                .addOptions(command.getOptions())
                                .queue(
                                        success -> System.out.println("Command 추가 성공: " + command.getName()),
                                        error -> System.err.println("Command 추가 실패: " + command.getName())
                                ));

                // 삭제할 명령어
                existingCommands.stream()
                        .filter(command -> commands.stream().noneMatch(cmd -> cmd.getName().equals(command.getName())))
                        .forEach(command -> guild.deleteCommandById(command.getId())
                                .queue(
                                        success -> System.out.println("Command 삭제 성공: " + command.getName()),
                                        error -> System.err.println("Command 삭제 실패: " + command.getName())
                                ));
            });
        });
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
// 명령어를 리스트에 추가
    public void add(ICommand command) {
        commands.add(command);
    }
}