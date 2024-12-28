package com.gahyeonbot.listeners;

import com.gahyeonbot.config.ConfigLoader;
import net.dv8tion.jda.api.JDA;
import net.dv8tion.jda.api.sharding.ShardManager;

public class ListenerManager {
    private final ShardManager shardManager;
    private final ConfigLoader configLoader;

    public ListenerManager(ShardManager shardManager, ConfigLoader configLoader) {
        this.shardManager = shardManager;
        this.configLoader = configLoader;
    }

    public void registerListeners() {
        shardManager.addEventListener(new MessageListener());
        shardManager.addEventListener(new MemberJoinListener());
        shardManager.addEventListener(new UserStatusUpdateListener(configLoader));
    }
}
