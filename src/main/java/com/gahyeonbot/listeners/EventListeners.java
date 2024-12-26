package com.gahyeonbot.listeners;

import com.gahyeonbot.config.ConfigLoader;
import net.dv8tion.jda.api.OnlineStatus;
import net.dv8tion.jda.api.entities.User;

import net.dv8tion.jda.api.events.guild.member.GuildMemberJoinEvent;
import net.dv8tion.jda.api.events.message.MessageReceivedEvent;
import net.dv8tion.jda.api.events.user.update.UserUpdateOnlineStatusEvent;
import net.dv8tion.jda.api.hooks.ListenerAdapter;
import org.jetbrains.annotations.NotNull;
import java.util.HashMap;
import java.util.Map;
import java.util.Objects;

public class EventListeners extends ListenerAdapter {
    private final ConfigLoader configLoader;
    public EventListeners(ConfigLoader config) {
        this.configLoader = config;  // 중복 초기화 방지
    }
    private final Map<String, String> emojiResponses = new HashMap<>();
    private static final Map<String, String> STATE_MAP = Map.of(
            "offline", "오프라인",
            "online", "온라인",
            "idle", "자리비움",
            "dnd", "방해금지"
    );



    /**
     * 텍스트채널 메시지 수신리스너
     * 봇의 메시지일 경우 무시한다.
     * 이벤트가 발생한 채널에 메시지를 회신한다.
     */
    @Override
    public void onMessageReceived(@NotNull MessageReceivedEvent event) {
        if (event.getAuthor().isBot()) return;
        String message = event.getMessage().getContentRaw();
        if (message.contains("ping")) {
            event.getChannel().sendMessage("pong2").queue();
        }
    }
    /**
     * 서버 입장 리스너
     */
    //
    @Override
    public void onGuildMemberJoin(@NotNull GuildMemberJoinEvent event) {
        User user = event.getUser();
        String message = "hi " + user;
        Objects.requireNonNull(event.getGuild().getDefaultChannel()).asTextChannel().sendMessage(message).queue();
    }

    /**
     * 온라인으로 전환한 유저 리스너
     */
    @Override
    public void onUserUpdateOnlineStatus(@NotNull UserUpdateOnlineStatusEvent event) {
        String USER_ID;
        try {
            USER_ID = configLoader.getValue("USER_ID");
        } catch (IllegalArgumentException e) {
            System.err.println("환경 변수 'USER_ID'가 설정되지 않았습니다.");
            return;
        }

        User user = event.getJDA().getUserById(USER_ID);
        if (user == null) return;
        long onlineCount = event.getGuild().getMembers().stream()
                .filter(member -> member.getOnlineStatus() == OnlineStatus.ONLINE)
                .count();

        String userState = changeStateKr(event.getNewOnlineStatus().getKey());
        String message = "**" + user.getName() + "** 님이 " + userState + " 상태로 변경되었습니다. 현재 온라인 유저 수: " + onlineCount;

        Objects.requireNonNull(event.getGuild().getDefaultChannel())
                .asTextChannel()
                .sendMessage(message).queue();
    }



    private String changeStateKr(String key) {
        return STATE_MAP.getOrDefault(key, "알 수 없음");
    }




    //봇 강제종류 알림
//    @Override
//    public void onShutdown(ShutdownEvent event) {
//        notifyAllServers(event);
//    }

    /**
     * 메시지 반응이모지 리스너
     */
//    @Override
//    public void onMessageReactionAdd(@NotNull MessageReactionAddEvent event) {
//        User user = event.getUser();
//        if (user == null || user.isBot()) return;
//
//        String emoji = event.getReaction().getEmoji().getAsReactionCode();
//        String message = String.format("%s 님이 %s 메시지에 %s 반응을 추가했습니다!",
//                user.getAsMention(),
//                event.getChannel().getAsMention(),
//                emoji
//        );
//
//        Objects.requireNonNull(event.getGuild().getDefaultChannel())
//                .asTextChannel()
//                .sendMessage(message).queue();
//    }
}
