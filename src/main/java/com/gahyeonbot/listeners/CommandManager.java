package com.gahyeonbot.listeners;

import com.gahyeonbot.commands.util.ICommand;
import net.dv8tion.jda.api.events.interaction.command.SlashCommandInteractionEvent;
import net.dv8tion.jda.api.hooks.ListenerAdapter;
import net.dv8tion.jda.api.sharding.ShardManager;
import org.jetbrains.annotations.NotNull;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.*;
import java.util.stream.Collectors;

public class CommandManager extends ListenerAdapter {
    private static final Logger logger = LoggerFactory.getLogger(CommandManager.class);
    private final Map<String, ICommand> commandMap = new HashMap<>();
    private ShardManager shardManager;

    public void setShardManager(ShardManager shardManager) {
        this.shardManager = shardManager;
    }

    public void synchronizeCommands() {
        if (shardManager == null) {
            throw new IllegalStateException("ShardManager가 설정되지 않았습니다!");
        }

        shardManager.getGuilds().forEach(guild -> {
            guild.retrieveCommands().queue(existingCommands -> {
                synchronizeGuildCommands(guild.getId(), existingCommands);
            });
        });
    }

    private void synchronizeGuildCommands(String guildId, List<net.dv8tion.jda.api.interactions.commands.Command> existingCommands) {
        List<String> existingCommandNames = existingCommands.stream()
                .map(net.dv8tion.jda.api.interactions.commands.Command::getName)
                .collect(Collectors.toList());

        List<String> addedCommands = new ArrayList<>();
        List<String> failedCommands = new ArrayList<>();

        // 등록 로직
        commandMap.values().stream()
                .filter(command -> !existingCommandNames.contains(command.getName()))
                .forEach(command -> Optional.ofNullable(shardManager.getGuildById(guildId))
                        .ifPresent(guild -> guild.upsertCommand(command.getName(), command.getDescription())
                                .addOptions(command.getOptions())
                                .queue(
                                        success -> {
                                            addedCommands.add(command.getName());
                                            logger.info("Command 추가 성공: {}", command.getName());
                                        },
                                        error -> {
                                            failedCommands.add(command.getName());
                                            logger.error("Command 추가 실패: {}", command.getName(), error);

                                            // 실패한 명령어 복구 시도
                                            guild.upsertCommand(command.getName(), command.getDescription())
                                                    .addOptions(command.getOptions())
                                                    .queue(
                                                            retrySuccess -> logger.info("Command 복구 성공: {}", command.getName()),
                                                            retryError -> logger.error("Command 복구 실패: {}", command.getName(), retryError)
                                                    );
                                        }
                                )));

        // 삭제 로직
        existingCommands.stream()
                .filter(command -> !commandMap.containsKey(command.getName()))
                .forEach(command -> Optional.ofNullable(shardManager.getGuildById(guildId))
                        .ifPresent(guild -> guild.deleteCommandById(command.getId())
                                .queue(
                                        success -> logger.info("Command 삭제 성공: {}", command.getName()),
                                        error -> logger.error("Command 삭제 실패: {}", command.getName(), error)
                                )));

        logger.info("등록된 명령어: {}", String.join(", ", addedCommands));
        if (!failedCommands.isEmpty()) {
            logger.warn("등록 실패 명령어: {}", String.join(", ", failedCommands));
        }
    }

    @Override
    public void onSlashCommandInteraction(@NotNull SlashCommandInteractionEvent event) {
        ICommand command = commandMap.get(event.getName());
        logger.info("명령어 '{}' 실행 요청 - 사용자: {} - 옵션: {}",
                event.getName(),
                event.getUser().getAsTag(),
                event.getOptions().stream()
                        .map(option -> option.getName() + "=" + option.getAsString())
                        .collect(Collectors.joining(", "))
        );

        if (command != null) {
            long startTime = System.currentTimeMillis();
            try {
                command.execute(event);
            } catch (Exception e) {
                logger.error("명령어 실행 중 오류 발생: {}", event.getName(), e);
                event.reply("명령어 실행 중 오류가 발생했습니다. 문제가 지속되면 관리자에게 문의하세요.").setEphemeral(true).queue();
            } finally {
                long endTime = System.currentTimeMillis();
                logger.info("명령어 '{}' 실행 시간: {}ms", event.getName(), (endTime - startTime));
            }
        } else {
            event.reply("알 수 없는 명령어입니다.").setEphemeral(true).queue();
        }
    }


    public void addCommand(ICommand command) {
        if (commandMap.containsKey(command.getName())) {
            logger.warn("명령어 '{}'가 이미 등록되어 있습니다.", command.getName());
            return;
        }
        commandMap.put(command.getName(), command);
        logger.info("명령어 '{}' 등록 완료.", command.getName());
    }

    public void addCommands(List<ICommand> commands) {
        commands.forEach(this::addCommand);
    }
}