package com.gahyeonbot.listeners;

import com.gahyeonbot.config.AppCredentialsConfig;
import net.dv8tion.jda.api.sharding.ShardManager;

/**
 * Discord 이벤트 리스너들을 관리하는 클래스.
 * 다양한 이벤트 리스너들을 ShardManager에 등록합니다.
 * 
 * @author GahyeonBot Team
 * @version 1.0
 */
public class ListenerManager {
    private final ShardManager shardManager;
    private final AppCredentialsConfig appCredentialsConfig;
    private final CommandManager commandManager;
    private final MessageListener messageListener;
    private final AssistantVoiceChannelListener assistantVoiceChannelListener;

    /**
     * ListenerManager 생성자.
     * 
     * @param shardManager Discord ShardManager 인스턴스
     * @param appCredentialsConfig 설정 로더
     * @param commandManager 명령어 매니저
     */
    public ListenerManager(
            ShardManager shardManager,
            AppCredentialsConfig appCredentialsConfig,
            CommandManager commandManager,
            MessageListener messageListener,
            AssistantVoiceChannelListener assistantVoiceChannelListener) {
        this.shardManager = shardManager;
        this.appCredentialsConfig = appCredentialsConfig;
        this.commandManager = commandManager;
        this.messageListener = messageListener;
        this.assistantVoiceChannelListener = assistantVoiceChannelListener;
    }

    /**
     * 모든 이벤트 리스너를 ShardManager에 등록합니다.
     */
    public void registerListeners() {
        shardManager.addEventListener(messageListener);
        shardManager.addEventListener(assistantVoiceChannelListener);
        shardManager.addEventListener(new MemberJoinListener());
        shardManager.addEventListener(new UserStatusUpdateListener(appCredentialsConfig));
        shardManager.addEventListener(commandManager);
    }
}
