package com.gahyeonbot.manager;

import com.wrapper.spotify.SpotifyApi;
import com.wrapper.spotify.model_objects.specification.Track;
import com.wrapper.spotify.requests.data.search.simplified.SearchTracksRequest;
import com.sedmelluq.discord.lavaplayer.player.AudioPlayerManager;
import com.sedmelluq.discord.lavaplayer.player.DefaultAudioPlayerManager;
import com.sedmelluq.discord.lavaplayer.source.AudioSourceManagers;
/*

LavaPlayer 초기화 및 소스 등록
Spotify API 초기화
Spotify에서 음악 검색 및 SoundCloud 쿼리 생성

*/
public class AudioManager {
    public static final AudioPlayerManager playerManager = new DefaultAudioPlayerManager();
    private final SpotifyApi spotifyApi;

    static {
        // Register sources supported by LavaPlayer 2.2.2
        AudioSourceManagers.registerRemoteSources(playerManager);
        AudioSourceManagers.registerLocalSource(playerManager);
    }

    public AudioManager(String spotifyClientId, String spotifyClientSecret) {
        spotifyApi = new SpotifyApi.Builder()
                .setClientId(spotifyClientId)
                .setClientSecret(spotifyClientSecret)
                .build();
    }

    public String getSoundCloudTrackFromSpotify(String spotifyQuery) {
        try {
            SearchTracksRequest searchTracksRequest = spotifyApi.searchTracks(spotifyQuery).build();
            Track[] tracks = searchTracksRequest.execute().getItems();

            if (tracks.length == 0) {
                return null;
            }

            Track track = tracks[0];
            String artist = track.getArtists()[0].getName();
            String title = track.getName();

            // Construct SoundCloud search query
            String soundCloudQuery = "scsearch:" + artist + " " + title;
            return soundCloudQuery;
        } catch (Exception e) {
            System.err.println("Spotify API Error: " + e.getMessage());
            return null;
        }
    }
}
