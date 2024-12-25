package com.gahyeonbot;

import com.gahyeonbot.commands.*;
import com.gahyeonbot.commands.base.ICommand;
import com.gahyeonbot.commands.music.*;
import com.gahyeonbot.commands.out.*;
import com.gahyeonbot.config.ConfigLoader;
import com.gahyeonbot.listeners.CommandManager;
import com.gahyeonbot.listeners.EventListeners;
import com.gahyeonbot.manager.music.AudioManager;
import com.gahyeonbot.manager.music.GuildMusicManager;
import com.gahyeonbot.manager.scheduler.LeaveSchedulerManager;
import com.gahyeonbot.manager.scheduler.LeaveSchedulerManagerImpl;
import com.gahyeonbot.service.SpotifySearchService;
import net.dv8tion.jda.api.OnlineStatus;
import net.dv8tion.jda.api.entities.Activity;
import net.dv8tion.jda.api.requests.GatewayIntent;
import net.dv8tion.jda.api.sharding.DefaultShardManagerBuilder;
import net.dv8tion.jda.api.sharding.ShardManager;
import net.dv8tion.jda.api.utils.ChunkingFilter;
import net.dv8tion.jda.api.utils.MemberCachePolicy;
import net.dv8tion.jda.api.utils.cache.CacheFlag;

import javax.security.auth.login.LoginException;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

/**
 * 봇의 메인 클래스.
 * 토큰을 환경 변수에서 로드하고 ShardManager를 초기화하며 주요 이벤트 리스너와 명령어를 등록합니다.
 */
public class Main {
    private final ConfigLoader config;
    private final ShardManager shardManager;
    private final LeaveSchedulerManager schedulerManager;


    public Main() {
        // ConfigLoader를 통해 토큰 가져오기
        config = new ConfigLoader();
        String token = config.getToken();

        if (token == null || token.isEmpty()) {
            throw new IllegalArgumentException("TOKEN이 설정되지 않았습니다!");
        }

        // ShardManager 빌드
        DefaultShardManagerBuilder builder = DefaultShardManagerBuilder
                .createDefault(token)
                .setStatus(OnlineStatus.ONLINE)
                .setActivity(Activity.playing("데이트")) // 봇 상태 메시지 설정
                .enableIntents(
                        GatewayIntent.GUILD_MEMBERS,
                        GatewayIntent.GUILD_MESSAGES,
                        GatewayIntent.MESSAGE_CONTENT,
                        GatewayIntent.GUILD_PRESENCES
                )
                .setMemberCachePolicy(MemberCachePolicy.ALL) // 멤버 캐싱 정책
                .setChunkingFilter(ChunkingFilter.ALL)       // 전체 서버 정보 로드
                .enableCache(CacheFlag.ONLINE_STATUS);       // 온라인 상태 캐싱

        shardManager = builder.build();

        // LeaveSchedulerManager 초기화
        schedulerManager = new LeaveSchedulerManagerImpl();

        // CommandManager 초기화 및 명령어 등록
        CommandManager commandManager = new CommandManager();
        commandManager.setShardManager(shardManager);
        registerCommands(commandManager);

        // 이벤트 리스너 등록
        shardManager.addEventListener(commandManager);
        shardManager.addEventListener(new EventListeners(config));
    }

    /**
     * 봇 명령어 등록 메서드.
     */
    private void registerCommands(CommandManager manager) {

        List<ICommand> commandList = new ArrayList<>();

        // GuildMusicManager 초기화
        Map<Long, GuildMusicManager> musicManagers = new HashMap<>();

        // Spotify API 키 로드
        String spotifyClientId = config.getSpotifyClientId();
        String spotifyClientSecret = config.getSpotifyClientSecret();
        // 필요한 매니저 생성
        AudioManager audioManager = new AudioManager(spotifyClientId, spotifyClientSecret);
        SpotifySearchService spotifySearchService = new SpotifySearchService();


        // 음악 관련 명령어 추가
        commandList.add(new Add(audioManager, musicManagers, spotifySearchService));
        commandList.add(new Clear(musicManagers));
        commandList.add(new Pause(musicManagers));
        commandList.add(new Queue(musicManagers));
        commandList.add(new Resume(musicManagers));

        // 예약 관련 명령어 추가
        commandList.add(new BotOut());
        commandList.add(new CancelOut(schedulerManager));
        commandList.add(new Out(schedulerManager));
        commandList.add(new SearchOut(schedulerManager));
        commandList.add(new WithOut(schedulerManager));

        // 기타 명령어 추가
        commandList.add(new Allhere());
        commandList.add(new Clean());
        // Info 명령어 등록 (명령어 목록 제공)
        manager.add(new Info(commandList));

        // 명령어 추가
        for (ICommand cmd : commandList) {
            manager.add(cmd);
        }
    }

    /**
     * ShardManager를 가져오는 메서드.
     */
    public ShardManager getShardManager() {
        return shardManager;
    }

    /**
     * ConfigLoader를 가져오는 메서드.
     */
    public ConfigLoader getConfig() {
        return config;
    }

    /**
     * 메인 메서드 - 봇 실행 시작.
     */
    public static void main(String[] args) throws LoginException {
        new Main();
    }
}
