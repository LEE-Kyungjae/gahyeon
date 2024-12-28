package com.gahyeonbot.manager.music;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import com.wrapper.spotify.SpotifyApi;
import com.wrapper.spotify.model_objects.specification.Track;
import com.wrapper.spotify.requests.data.search.simplified.SearchTracksRequest;
import com.sedmelluq.discord.lavaplayer.player.AudioPlayerManager;
import com.sedmelluq.discord.lavaplayer.player.DefaultAudioPlayerManager;
import com.sedmelluq.discord.lavaplayer.source.AudioSourceManagers;

public class AudioManager {
    private static final Logger logger = LoggerFactory.getLogger(AudioManager.class);
    private final AudioPlayerManager playerManager;
    private final SpotifyApi spotifyApi;

    public AudioManager(String spotifyClientId, String spotifyClientSecret) {
        this.playerManager = new DefaultAudioPlayerManager();
        AudioSourceManagers.registerRemoteSources(playerManager);
        AudioSourceManagers.registerLocalSource(playerManager);

        spotifyApi = new SpotifyApi.Builder()
                .setClientId(spotifyClientId)
                .setClientSecret(spotifyClientSecret)
                .build();

        authenticateSpotify();
    }

    private void authenticateSpotify() {
        try {
            var credentials = spotifyApi.clientCredentials().build().execute();
            spotifyApi.setAccessToken(credentials.getAccessToken());
            logger.info("Spotify 인증 성공");
        } catch (Exception e) {
            logger.error("Spotify 인증 실패: LavaPlayer만 활성화됩니다.", e);
        }
    }

    public AudioPlayerManager getPlayerManager() {
        return playerManager;
    }

    public String getSoundCloudTrackFromSpotify(String spotifyQuery) {
        if (spotifyQuery == null || spotifyQuery.trim().isEmpty()) {
            logger.warn("유효하지 않은 Spotify 쿼리");
            return null;
        }

        try {
            SearchTracksRequest request = spotifyApi.searchTracks(spotifyQuery).build();
            Track[] tracks = request.execute().getItems();
            if (tracks.length == 0) {
                logger.info("Spotify에서 결과를 찾을 수 없습니다. 쿼리: {}", spotifyQuery);
                return null;
            }
            return buildSoundCloudQuery(tracks[0]);
        } catch (Exception e) {
            logger.error("Spotify API 오류", e);
            return null;
        }
    }

    private String buildSoundCloudQuery(Track track) {
        String artist = track.getArtists()[0].getName();
        String title = track.getName();
        String soundCloudQuery = "scsearch:" + artist + " " + title;
        logger.info("SoundCloud 쿼리 생성: {}", soundCloudQuery);
        return soundCloudQuery;
    }
}
