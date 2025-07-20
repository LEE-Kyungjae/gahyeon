package com.gahyeonbot.core;

import com.gahyeonbot.config.AppCredentialsConfig;
import com.gahyeonbot.core.audio.AudioManager;
import com.gahyeonbot.core.audio.GuildMusicManager;
import com.gahyeonbot.core.command.CommandRegistry;
import com.gahyeonbot.core.scheduler.LeaveSchedulerManagerImpl;
import com.gahyeonbot.listeners.CommandManager;
import com.gahyeonbot.listeners.ListenerManager;
import lombok.RequiredArgsConstructor;
import net.dv8tion.jda.api.sharding.ShardManager;
import org.springframework.boot.CommandLineRunner;
import org.springframework.stereotype.Component;

import java.util.HashMap;

@Component
@RequiredArgsConstructor
public class BotInitializerRunner implements CommandLineRunner {

    private final AppCredentialsConfig config;

    @Override
    public void run(String... args) throws Exception {
        BotInitializer botInitializer = new BotInitializer(config);
        ShardManager shardManager = botInitializer.initialize();

        LeaveSchedulerManagerImpl schedulerManager = new LeaveSchedulerManagerImpl();
        HashMap<Long, GuildMusicManager> musicManagers = new HashMap<>();
        AudioManager audioManager = new AudioManager(
                config.getSpotifyClientId(),
                config.getSpotifyClientSecret()
        );

        CommandRegistry commandRegistry = new CommandRegistry(audioManager, schedulerManager, musicManagers);
        CommandManager commandManager = new CommandManager();
        commandRegistry.registerCommands().forEach(commandManager::addCommand);
        commandManager.setShardManager(shardManager);
        commandManager.synchronizeCommands();

        ListenerManager listenerManager = new ListenerManager(shardManager, config, commandManager);
        listenerManager.registerListeners();
    }
}
