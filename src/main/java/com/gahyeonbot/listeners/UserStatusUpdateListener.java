package com.gahyeonbot.listeners;

import com.gahyeonbot.config.AppCredentialsConfig;
import com.gahyeonbot.config.ConfigLoader;
import net.dv8tion.jda.api.OnlineStatus;
import net.dv8tion.jda.api.events.user.update.UserUpdateOnlineStatusEvent;
import net.dv8tion.jda.api.hooks.ListenerAdapter;
import org.jetbrains.annotations.NotNull;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.Map;

/**
 * 사용자의 온라인 상태 변경 이벤트를 처리하는 리스너 클래스.
 * 특정 사용자의 상태 변경을 감지하고 서버의 기본 채널에 알림을 전송합니다.
 * 
 * @author GahyeonBot Team
 * @version 1.0
 */
public class UserStatusUpdateListener extends ListenerAdapter {
    private static final Logger logger = LoggerFactory.getLogger(UserStatusUpdateListener.class);

    private final AppCredentialsConfig appCredentialsConfig;
    private static final Map<String, String> STATE_MAP = Map.of(
            "offline", "오프라인",
            "online", "온라인",
            "idle", "자리비움",
            "dnd", "방해금지"
    );

    /**
     * UserStatusUpdateListener 생성자.
     * 
     * @param appCredentialsConfig 설정 로더
     */
    public UserStatusUpdateListener(AppCredentialsConfig appCredentialsConfig) {
        this.appCredentialsConfig = appCredentialsConfig;
    }

    @Override
    public void onUserUpdateOnlineStatus(@NotNull UserUpdateOnlineStatusEvent event) {
        logger.info("onUserUpdateOnlineStatus");


//        String userId = getConfigValue("USER_ID");
//        if (userId == null) return;
//
//        var user = event.getJDA().getUserById(userId);
//        if (user == null) return;
//
//        long onlineCount = event.getGuild().getMembers().stream()
//                .filter(member -> member.getOnlineStatus() == OnlineStatus.ONLINE)
//                .count();
//
//        String userState = STATE_MAP.getOrDefault(event.getNewOnlineStatus().getKey(), "알 수 없음");
//        String message = "**" + user.getName() + "** 님이 " + userState + " 상태로 변경되었습니다. 현재 온라인 유저 수: " + onlineCount;
//
//        event.getGuild().getDefaultChannel()
//                .asTextChannel()
//                .sendMessage(message)
//                .queue();
    }

//    private String getConfigValue(String key) {
//        try {
//            return appCredentialsConfig.getValue(key);
//        } catch (IllegalArgumentException e) {
//            System.err.println("환경 변수 '" + key + "'가 설정되지 않았습니다.");
//            return null;
//        }
//    }
}
