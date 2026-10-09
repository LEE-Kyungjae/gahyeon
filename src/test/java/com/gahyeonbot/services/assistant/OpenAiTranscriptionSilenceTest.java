package com.gahyeonbot.services.assistant;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.sun.net.httpserver.HttpServer;
import com.gahyeonbot.application.speech.DefaultTranscriptionService;
import com.gahyeonbot.core.speech.AudioInput;
import org.junit.jupiter.api.Test;
import javax.sound.sampled.*;
import java.io.*;
import java.net.InetSocketAddress;
import java.nio.charset.StandardCharsets;
import java.util.concurrent.atomic.AtomicInteger;
import static org.assertj.core.api.Assertions.*;

class OpenAiTranscriptionSilenceTest {
    @Test void coreServiceRejectsExactSilenceWithoutCallingPrimaryOrFallback() throws Exception {
        AtomicInteger calls = new AtomicInteger();
        var server = server(calls, false);
        try {
            var provider = new OpenAiTranscriptionProvider(settings(server), new ObjectMapper());
            var service = new DefaultTranscriptionService(provider);
            for (int length : new int[]{32000, 96000})
                assertThat(service.transcribe(new AudioInput(wav(new byte[length]), "audio/wav"))).isEmpty();
            assertThat(calls.get()).isZero();
        } finally { server.stop(0); }
    }
    @Test void veryQuietSpeechStillReachesPrimaryRecognition() throws Exception {
        AtomicInteger calls = new AtomicInteger();
        var server = server(calls, false);
        try {
            var provider = new OpenAiTranscriptionProvider(settings(server), new ObjectMapper());
            byte[] pcm = new byte[32000]; pcm[1000] = 1;
            assertThat(provider.transcribe(wav(pcm))).isEqualTo("네");
            assertThat(calls.get()).isEqualTo(1);
        } finally { server.stop(0); }
    }
    @Test void quietSpeechKeepsExistingProviderFailureFallback() throws Exception {
        AtomicInteger calls = new AtomicInteger();
        var server = server(calls, true);
        try {
            var provider = new OpenAiTranscriptionProvider(settings(server), new ObjectMapper());
            byte[] pcm = new byte[32000]; pcm[1000] = 1;
            assertThat(provider.transcribe(wav(pcm))).isEqualTo("네");
            assertThat(calls.get()).isEqualTo(2);
        } finally { server.stop(0); }
    }
    @Test void silenceDoesNotBypassDisabledProviderConfiguration() throws Exception {
        var provider = new OpenAiTranscriptionProvider(new AssistantProperties(), new ObjectMapper());
        assertThatThrownBy(() -> provider.transcribe(wav(new byte[32000])))
                .isInstanceOf(IllegalStateException.class);
    }
    private static AssistantProperties settings(HttpServer server) {
        var p = new AssistantProperties(); p.setEnabled(true);
        p.getStt().setEnabled(true); p.getStt().setApiKeyRequired(false);
        p.getStt().setBaseUrl("http://127.0.0.1:" + server.getAddress().getPort());
        p.getStt().setEndpoint("/primary");
        p.getStt().setFallbackBaseUrl(p.getStt().getBaseUrl()); p.getStt().setFallbackEndpoint("/fallback");
        return p;
    }
    private static HttpServer server(AtomicInteger calls, boolean failPrimary) throws IOException {
        var server = HttpServer.create(new InetSocketAddress("127.0.0.1", 0), 0);
        server.createContext("/", exchange -> {
            calls.incrementAndGet(); exchange.getRequestBody().readAllBytes();
            boolean failure = failPrimary && exchange.getRequestURI().getPath().equals("/primary");
            byte[] response = (failure ? "{}" : "{\"text\":\"네\"}").getBytes(StandardCharsets.UTF_8);
            exchange.getResponseHeaders().set("Content-Type", "application/json");
            exchange.sendResponseHeaders(failure ? 503 : 200, response.length);
            exchange.getResponseBody().write(response); exchange.close();
        }); server.start(); return server;
    }
    private static byte[] wav(byte[] pcm) throws Exception {
        var format = new AudioFormat(16000, 16, 1, true, false);
        var out = new ByteArrayOutputStream();
        try (var input = new AudioInputStream(new ByteArrayInputStream(pcm), format, pcm.length / 2)) {
            AudioSystem.write(input, AudioFileFormat.Type.WAVE, out);
        } return out.toByteArray();
    }
}
