package com.gahyeonbot.services.assistant;

import com.gahyeonbot.core.audio.GuildMusicManager;
import com.gahyeonbot.services.music.MusicService;
import com.gahyeonbot.services.tts.TtsService;
import com.gahyeonbot.services.tts.TtsTrackMetadata;
import com.sedmelluq.discord.lavaplayer.player.AudioLoadResultHandler;
import com.sedmelluq.discord.lavaplayer.tools.FriendlyException;
import com.sedmelluq.discord.lavaplayer.track.AudioPlaylist;
import com.sedmelluq.discord.lavaplayer.track.AudioTrack;
import jakarta.annotation.PreDestroy;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import net.dv8tion.jda.api.audio.AudioReceiveHandler;
import net.dv8tion.jda.api.audio.UserAudio;
import net.dv8tion.jda.api.entities.Guild;
import net.dv8tion.jda.api.entities.Member;
import net.dv8tion.jda.api.entities.channel.middleman.MessageChannel;
import net.dv8tion.jda.api.entities.channel.middleman.AudioChannel;
import org.springframework.stereotype.Service;

import java.io.ByteArrayOutputStream;
import java.nio.file.Path;
import java.util.Map;
import java.util.concurrent.*;

@Slf4j
@Service
@RequiredArgsConstructor
public class VoiceAssistantService {
    private static final int MIN_UTTERANCE_BYTES = WavEncoder.SAMPLE_RATE * 4 / 2; // ~0.5 second

    private final AssistantProperties properties;
    private final SpeechToTextProvider speechToTextProvider;
    private final AssistantChatProvider chatProvider;
    private final TtsService ttsService;
    private final MusicService musicService;
    private final com.gahyeonbot.core.audio.AudioManager audioManager;

    private final Map<Long, Session> sessions = new ConcurrentHashMap<>();
    private final ScheduledExecutorService silenceDetector =
            Executors.newSingleThreadScheduledExecutor(Thread.ofPlatform().name("assistant-silence-", 0).factory());
    private final ExecutorService workers = Executors.newVirtualThreadPerTaskExecutor();

    public boolean isConfigured() {
        return properties.isEnabled() && speechToTextProvider.isReady() && chatProvider.isReady();
    }

    public StartResult start(Guild guild, Member requester, MessageChannel textChannel) {
        if (!properties.isEnabled()) return new StartResult(false, "비서 기능이 비활성화되어 있습니다.");
        if (!speechToTextProvider.isReady()) return new StartResult(false, "STT 설정이 필요합니다.");
        if (!chatProvider.isReady()) return new StartResult(false, "OpenRouter 키와 모델 설정이 필요합니다.");
        if (requester == null || requester.getVoiceState() == null
                || requester.getVoiceState().getChannel() == null) {
            return new StartResult(false, "먼저 음성 채널에 입장해 주세요.");
        }
        if (sessions.containsKey(guild.getIdLong())) {
            return new StartResult(false, "이 서버에서는 이미 비서 세션이 실행 중입니다.");
        }

        AudioChannel channel = requester.getVoiceState().getChannel();
        GuildMusicManager musicManager = musicService.getOrCreateGuildMusicManager(guild);
        Session session = new Session(guild, channel, textChannel, musicManager);
        sessions.put(guild.getIdLong(), session);

        var manager = guild.getAudioManager();
        manager.setSelfDeafened(false);
        manager.setSendingHandler(musicManager.getSendHandler());
        manager.setReceivingHandler(session.receiver);
        manager.openAudioConnection(channel);
        return new StartResult(true,
                "음성 비서 세션을 시작했습니다. 종료 전까지 참여자의 음성이 외부 STT/AI로 전송되고 전사문이 이 채널에 표시됩니다.");
    }

    public boolean stop(Guild guild) {
        Session session = sessions.remove(guild.getIdLong());
        if (session == null) return false;
        session.close();
        guild.getAudioManager().setReceivingHandler(null);
        guild.getAudioManager().closeAudioConnection();
        return true;
    }

    public boolean isRunning(long guildId) {
        return sessions.containsKey(guildId);
    }

    @PreDestroy
    void shutdown() {
        sessions.values().forEach(Session::close);
        silenceDetector.shutdownNow();
        workers.shutdownNow();
    }

    public record StartResult(boolean started, String message) {}

    private final class Session {
        private final Guild guild;
        private final AudioChannel voiceChannel;
        private final MessageChannel textChannel;
        private final GuildMusicManager musicManager;
        private final Map<Long, Utterance> utterances = new ConcurrentHashMap<>();
        private final AudioReceiveHandler receiver = new Receiver();
        private final ScheduledFuture<?> silenceTask;
        private volatile boolean closed;

        private Session(Guild guild, AudioChannel voiceChannel, MessageChannel textChannel,
                        GuildMusicManager musicManager) {
            this.guild = guild;
            this.voiceChannel = voiceChannel;
            this.textChannel = textChannel;
            this.musicManager = musicManager;
            this.silenceTask = silenceDetector.scheduleWithFixedDelay(
                    this::flushSilent, 250, 250, TimeUnit.MILLISECONDS);
        }

        private void close() {
            closed = true;
            silenceTask.cancel(false);
            utterances.values().forEach(Utterance::close);
            utterances.clear();
        }

        private final class Receiver implements AudioReceiveHandler {
            @Override public boolean canReceiveUser() { return !closed; }

            @Override
            public void handleUserAudio(UserAudio userAudio) {
                if (closed || userAudio.getUser().isBot()) return;
                // JDA exposes decoded 16-bit PCM in big-endian byte order, while
                // WAV and TEN VAD expect little-endian samples.
                byte[] pcm = WavEncoder.bigEndianToLittleEndian(userAudio.getAudioData(1.0));
                Utterance utterance = utterances.computeIfAbsent(
                        userAudio.getUser().getIdLong(),
                        ignored -> new Utterance(userAudio.getUser().getName(), properties.getVad()));
                synchronized (utterance) {
                    int max = properties.getMaxUtteranceSeconds()
                            * WavEncoder.SAMPLE_RATE * WavEncoder.CHANNELS * WavEncoder.BITS_PER_SAMPLE / 8;
                    long now = System.currentTimeMillis();
                    if (utterance.vad == null) {
                        if (utterance.pcm.size() + pcm.length <= max) utterance.pcm.writeBytes(pcm);
                        utterance.lastVoiceAt = now;
                        return;
                    }

                    TenVadDetector.Detection detection = utterance.vad.processDiscordPcm(pcm);
                    if (!utterance.speechStarted) {
                        if (detection.voice()) {
                            utterance.speechStarted = true;
                            utterance.pcm.writeBytes(utterance.preRoll.toByteArray());
                            utterance.preRoll.reset();
                        } else {
                            utterance.appendPreRoll(pcm, properties.getVad().getPreRollMillis());
                            return;
                        }
                    }
                    if (utterance.pcm.size() + pcm.length <= max) utterance.pcm.writeBytes(pcm);
                    if (detection.voice()) {
                        utterance.lastVoiceAt = now;
                        utterance.voiceSamples += (long) detection.voiceFrames() * properties.getVad().getHopSize();
                    }
                }
            }
        }

        private void flushSilent() {
            if (closed) return;
            long now = System.currentTimeMillis();
            utterances.forEach((userId, utterance) -> {
                byte[] pcm = null;
                synchronized (utterance) {
                    long requiredSilence = utterance.vad == null
                            ? properties.getSilenceMillis()
                            : properties.getVad().getEndSilenceMillis();
                    long speechMillis = utterance.vad == null
                            ? Long.MAX_VALUE
                            : utterance.voiceSamples * 1_000 / 16_000;
                    boolean maxLength = utterance.pcm.size() >= properties.getMaxUtteranceSeconds()
                            * WavEncoder.SAMPLE_RATE * WavEncoder.CHANNELS * WavEncoder.BITS_PER_SAMPLE / 8;
                    if (utterance.speechStarted
                            && utterance.pcm.size() >= MIN_UTTERANCE_BYTES
                            && speechMillis >= properties.getVad().getMinSpeechMillis()
                            && (now - utterance.lastVoiceAt >= requiredSilence || maxLength)) {
                        pcm = utterance.pcm.toByteArray();
                        utterance.reset();
                    }
                }
                if (pcm != null) {
                    byte[] captured = pcm;
                    workers.submit(() -> process(userId, utterance.username, captured));
                }
            });
        }

        private void process(long userId, String username, byte[] pcm) {
            if (closed) return;
            try {
                String transcript = speechToTextProvider.transcribe(WavEncoder.pcmToWav(pcm));
                if (transcript.isBlank()) return;
                textChannel.sendMessage("**" + username + "**: " + limit(transcript, 1500)).queue();
                String answer = chatProvider.chat(guild.getIdLong(), userId, username, transcript);
                textChannel.sendMessage("**가현**: " + limit(answer, 1800)).queue();
                if (properties.isSpeakResponses() && ttsService.isEnabled() && !closed) speak(answer);
            } catch (Exception e) {
                log.error("음성 비서 처리 실패 guild={} user={}", guild.getIdLong(), userId, e);
                textChannel.sendMessage("음성 비서 처리에 실패했습니다. 잠시 후 다시 말해 주세요.").queue();
            }
        }

        private void speak(String answer) throws Exception {
            for (String segment : ttsService.prepareSegments(answer)) {
                Path audio = ttsService.synthesizeSegmentToAudio(
                        segment, properties.getTtsProvider());
                audioManager.getPlayerManager().loadItem(audio.toString(), new AudioLoadResultHandler() {
                    @Override public void trackLoaded(AudioTrack track) {
                        track.setUserData(new TtsTrackMetadata(audio, true, true));
                        musicManager.playOrQueueTrack(track);
                    }
                    @Override public void playlistLoaded(AudioPlaylist playlist) {
                        if (!playlist.getTracks().isEmpty()) trackLoaded(playlist.getTracks().getFirst());
                    }
                    @Override public void noMatches() { log.warn("비서 TTS 파일을 로드하지 못함: {}", audio); }
                    @Override public void loadFailed(FriendlyException exception) {
                        log.warn("비서 TTS 로딩 실패: {}", exception.getMessage());
                    }
                });
            }
        }
    }

    private static final class Utterance {
        private final String username;
        private final ByteArrayOutputStream pcm = new ByteArrayOutputStream();
        private final ByteArrayOutputStream preRoll = new ByteArrayOutputStream();
        private final TenVadDetector vad;
        private long lastVoiceAt = System.currentTimeMillis();
        private long voiceSamples;
        private boolean speechStarted;

        private Utterance(String username, AssistantProperties.Vad settings) {
            this.username = username;
            this.vad = settings.isEnabled()
                    ? new TenVadDetector(settings.getHopSize(), settings.getThreshold())
                    : null;
            this.speechStarted = vad == null;
        }

        private void appendPreRoll(byte[] packet, long preRollMillis) {
            int maxBytes = (int) (WavEncoder.SAMPLE_RATE * WavEncoder.CHANNELS
                    * WavEncoder.BITS_PER_SAMPLE / 8 * preRollMillis / 1_000);
            preRoll.writeBytes(packet);
            if (preRoll.size() <= maxBytes) return;
            byte[] bytes = preRoll.toByteArray();
            preRoll.reset();
            preRoll.write(bytes, bytes.length - maxBytes, maxBytes);
        }

        private void reset() {
            pcm.reset();
            preRoll.reset();
            voiceSamples = 0;
            speechStarted = vad == null;
            lastVoiceAt = System.currentTimeMillis();
        }

        private void close() {
            if (vad != null) vad.close();
        }
    }

    private static String limit(String text, int max) {
        return text.length() <= max ? text : text.substring(0, max - 3) + "...";
    }
}
