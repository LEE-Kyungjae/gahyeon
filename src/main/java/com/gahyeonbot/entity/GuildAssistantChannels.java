package com.gahyeonbot.entity;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.Setter;

import java.time.LocalDateTime;

@Entity
@Table(name = "guild_assistant_channels")
@Getter
@Setter
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class GuildAssistantChannels {
    @Id
    @Column(name = "guild_id")
    private Long guildId;

    @Column(name = "category_id", nullable = false)
    private Long categoryId;

    @Column(name = "text_channel_id", nullable = false)
    private Long textChannelId;

    @Column(name = "voice_channel_id", nullable = false)
    private Long voiceChannelId;

    @Column(name = "created_by", nullable = false)
    private Long createdBy;

    @Column(name = "created_at", nullable = false)
    private LocalDateTime createdAt;

    @Column(name = "updated_at", nullable = false)
    private LocalDateTime updatedAt;
}

