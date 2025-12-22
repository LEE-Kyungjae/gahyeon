package com.gahyeonbot.core;

import com.gahyeonbot.config.AppCredentialsConfig;
import com.gahyeonbot.core.command.CommandRegistry;
import com.gahyeonbot.listeners.CommandManager;
import com.gahyeonbot.listeners.ListenerManager;
import lombok.RequiredArgsConstructor;
import net.dv8tion.jda.api.sharding.ShardManager;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.boot.CommandLineRunner;
import org.springframework.stereotype.Component;

/**
 * Discord 봇의 초기화를 담당하는 Spring CommandLineRunner.
 * Spring Boot 애플리케이션이 시작될 때 자동으로 실행되어 봇을 초기화합니다.
 *
 * @author GahyeonBot Team
 * @version 1.0
 */
@Component
@RequiredArgsConstructor
public class BotInitializerRunner implements CommandLineRunner {

    private static final Logger logger = LoggerFactory.getLogger(BotInitializerRunner.class);
    private final AppCredentialsConfig config;
    private final CommandRegistry commandRegistry;
    @Value("${bot.enabled:true}")
    private boolean botEnabled;
    private ShardManager shardManager;

    /**
     * Discord 봇을 초기화하고 리스너를 등록합니다.
     *
     * @param args 명령줄 인수
     * @throws Exception 초기화 중 발생할 수 있는 예외
     */
    @Override
    public void run(String... args) throws Exception {
        if (!botEnabled) {
            logger.info("bot.enabled=false 설정으로 Discord 봇 초기화를 건너뜁니다.");
            return;
        }
        try {
            // Discord ShardManager 초기화
            BotInitializer botInitializer = new BotInitializer(config);
            shardManager = botInitializer.initialize();

            // CommandManager 설정 및 명령어 등록
            CommandManager commandManager = new CommandManager();
            commandRegistry.registerCommands().forEach(commandManager::addCommand);
            commandManager.setShardManager(shardManager);
            commandManager.synchronizeCommands();

            // 이벤트 리스너 등록
            ListenerManager listenerManager = new ListenerManager(shardManager, config, commandManager);
            listenerManager.registerListeners();

            logger.info("Discord 봇이 성공적으로 초기화되었습니다.");
        } catch (IllegalArgumentException e) {
            logger.warn("Discord 봇 초기화 실패: {}. 애플리케이션은 계속 실행됩니다.", e.getMessage());
        } catch (Exception e) {
            logger.error("Discord 봇 초기화 중 예기치 않은 오류 발생", e);
            throw e;
        }
    }

    @jakarta.annotation.PreDestroy
    public void shutdown() {
        if (shardManager != null) {
            logger.info("ShardManager 종료 중...");
            shardManager.shutdown();
        }
    }
}
