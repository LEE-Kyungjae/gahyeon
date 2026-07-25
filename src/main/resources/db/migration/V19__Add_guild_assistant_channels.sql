CREATE TABLE guild_assistant_channels (
    guild_id BIGINT PRIMARY KEY,
    category_id BIGINT NOT NULL,
    text_channel_id BIGINT NOT NULL,
    voice_channel_id BIGINT NOT NULL,
    created_by BIGINT NOT NULL,
    created_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP NOT NULL
);

