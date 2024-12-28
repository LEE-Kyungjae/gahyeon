package com.gahyeonbot.listeners;

import com.gahyeonbot.config.ConfigLoader;
import net.dv8tion.jda.api.OnlineStatus;
import net.dv8tion.jda.api.events.user.update.UserUpdateOnlineStatusEvent;
import net.dv8tion.jda.api.hooks.ListenerAdapter;
import org.jetbrains.annotations.NotNull;

import java.util.Map;

public class UserStatusUpdateListener extends ListenerAdapter {
    private final ConfigLoader configLoader;
    private static final Map<String, String> STATE_MAP = Map.of(
            "offline", "오프라인",
            "online", "온라인",
            "idle", "자리비움",
            "dnd", "방해금지"
    );

    public UserStatusUpdateListener(ConfigLoader configLoader) {
        this.configLoader = configLoader;
    }

    @Override
    public void onUserUpdateOnlineStatus(@NotNull UserUpdateOnlineStatusEvent event) {
        String userId = getConfigValue("USER_ID");
        if (userId == null) return;

        var user = event.getJDA().getUserById(userId);
        if (user == null) return;

        long onlineCount = event.getGuild().getMembers().stream()
                .filter(member -> member.getOnlineStatus() == OnlineStatus.ONLINE)
                .count();

        String userState = STATE_MAP.getOrDefault(event.getNewOnlineStatus().getKey(), "알 수 없음");
        String message = "**" + user.getName() + "** 님이 " + userState + " 상태로 변경되었습니다. 현재 온라인 유저 수: " + onlineCount;

        event.getGuild().getDefaultChannel()
                .asTextChannel()
                .sendMessage(message)
                .queue();
    }

    private String getConfigValue(String key) {
        try {
            return configLoader.getValue(key);
        } catch (IllegalArgumentException e) {
            System.err.println("환경 변수 '" + key + "'가 설정되지 않았습니다.");
            return null;
        }
    }
}
