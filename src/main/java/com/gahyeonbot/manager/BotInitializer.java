package com.gahyeonbot.manager;

import com.gahyeonbot.config.ConfigLoader;
import net.dv8tion.jda.api.OnlineStatus;
import net.dv8tion.jda.api.entities.Activity;
import net.dv8tion.jda.api.requests.GatewayIntent;
import net.dv8tion.jda.api.sharding.DefaultShardManagerBuilder;
import net.dv8tion.jda.api.sharding.ShardManager;
import net.dv8tion.jda.api.utils.ChunkingFilter;
import net.dv8tion.jda.api.utils.MemberCachePolicy;
import net.dv8tion.jda.api.utils.cache.CacheFlag;

public class BotInitializer {
    private final ConfigLoader config;
    public BotInitializer(ConfigLoader config) {
        this.config = config;
    }
    public ShardManager initialize() throws IllegalArgumentException {
        String token = config.getToken();
        if (token == null || token.isEmpty()) {
            throw new IllegalArgumentException("TOKEN이 설정되지 않았습니다!");
        }

        try {
            return DefaultShardManagerBuilder.createDefault(token)
                    .setStatus(OnlineStatus.ONLINE)
                    .setActivity(Activity.playing("데이트"))
                    .enableIntents(
                            GatewayIntent.GUILD_MEMBERS,
                            GatewayIntent.GUILD_MESSAGES,
                            GatewayIntent.MESSAGE_CONTENT,
                            GatewayIntent.GUILD_PRESENCES
                    )
                    .setMemberCachePolicy(MemberCachePolicy.ALL)
                    .setChunkingFilter(ChunkingFilter.ALL)
                    .enableCache(CacheFlag.ONLINE_STATUS)
                    .build();
        } catch (Exception e) {
            throw new RuntimeException("ShardManager 초기화 실패", e);
        }
    }

}
