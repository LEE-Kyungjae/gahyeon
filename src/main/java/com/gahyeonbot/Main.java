package com.gahyeonbot;

import com.gahyeonbot.config.ConfigLoader;
import com.gahyeonbot.listeners.CommandManager;
import com.gahyeonbot.listeners.ListenerManager;
import com.gahyeonbot.listeners.UserStatusUpdateListener;
import com.gahyeonbot.manager.BotInitializer;
import com.gahyeonbot.manager.command.CommandRegistrar;
import com.gahyeonbot.manager.music.AudioManager;
import com.gahyeonbot.manager.music.GuildMusicManager;
import com.gahyeonbot.manager.scheduler.LeaveSchedulerManagerImpl;
import net.dv8tion.jda.api.sharding.ShardManager;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import javax.security.auth.login.LoginException;
import java.util.HashMap;

/**
 * 봇의 메인 클래스.
 * 토큰을 환경 변수에서 로드하고 ShardManager를 초기화하며 주요 이벤트 리스너와 명령어를 등록합니다.
 */
public class Main {
    private static final Logger logger = LoggerFactory.getLogger(UserStatusUpdateListener.class);

    public Main() {

        ConfigLoader config = new ConfigLoader();
        // 봇 초기화
        BotInitializer botInitializer = new BotInitializer(config);
        ShardManager shardManager = botInitializer.initialize();
        // 스케줄러 매니저
        LeaveSchedulerManagerImpl schedulerManager = new LeaveSchedulerManagerImpl();
        HashMap<Long, GuildMusicManager> musicManagers = new HashMap<>();
        AudioManager audioManager = new AudioManager(
                config.getSpotifyClientId(),
                config.getSpotifyClientSecret()
        );
        // 명령어 등록
        CommandRegistrar commandRegistrar = new CommandRegistrar(audioManager, schedulerManager, musicManagers);
        CommandManager commandManager = new CommandManager();
        commandRegistrar.registerCommands().forEach(commandManager::addCommand);
        // ShardManager 설정
        commandManager.setShardManager(shardManager);
        // 명령어 동기화
        commandManager.synchronizeCommands();

        // 이벤트 리스너 등록
        ListenerManager listenerManager = new ListenerManager(shardManager, config, commandManager);
        listenerManager.registerListeners();
        logger.info("GahyeonBot started successfully!");
    }
    /**
     * 메인 메서드 - 봇 실행 시작.
     */
    public static void main(String[] args) throws LoginException {
        new Main();
    }
}
