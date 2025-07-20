package com.gahyeonbot;

import com.gahyeonbot.config.AppCredentialsConfig;
import com.gahyeonbot.config.ConfigLoader;
import com.gahyeonbot.core.BotInitializer;
import com.gahyeonbot.core.audio.AudioManager;
import com.gahyeonbot.core.audio.GuildMusicManager;
import com.gahyeonbot.core.command.CommandRegistry;
import com.gahyeonbot.core.scheduler.LeaveSchedulerManagerImpl;
import com.gahyeonbot.listeners.CommandManager;
import com.gahyeonbot.listeners.ListenerManager;
import lombok.AllArgsConstructor;
import net.dv8tion.jda.api.sharding.ShardManager;
import org.springframework.boot.CommandLineRunner;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.ComponentScan;
import java.util.HashMap;

/**
 * Discord 봇의 메인 스프링부트 애플리케이션 클래스.
 * 스프링부트 애플리케이션을 시작하고 Discord 봇을 초기화합니다.
 * 
 * @author GahyeonBot Team
 * @version 1.0
 */
@SpringBootApplication
public class Main {
    public static void main(String[] args) {
        SpringApplication.run(Main.class, args);
    }
}