package com.gahyeonbot.services.tts;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.sun.net.httpserver.HttpExchange;
import com.sun.net.httpserver.HttpServer;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.Test;

import java.io.IOException;
import java.net.InetSocketAddress;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.concurrent.atomic.AtomicInteger;

import static org.assertj.core.api.Assertions.assertThat;

class VoiceboxTtsProviderTest {
    private HttpServer server;

    @AfterEach
    void stopServer() {
        if (server != null) {
            server.stop(0);
        }
    }

    @Test
    void generatesPollsAndDownloadsAudio() throws Exception {
        byte[] expectedAudio = new byte[512];
        expectedAudio[0] = 'R';
        expectedAudio[1] = 'I';
        expectedAudio[2] = 'F';
        expectedAudio[3] = 'F';
        AtomicInteger historyCalls = new AtomicInteger();

        server = HttpServer.create(new InetSocketAddress(0), 0);
        server.createContext("/generate", exchange -> {
            assertThat(exchange.getRequestMethod()).isEqualTo("POST");
            String body = new String(exchange.getRequestBody().readAllBytes(), StandardCharsets.UTF_8);
            assertThat(body).contains("\"profile_id\":\"recording-6-profile\"");
            assertThat(body).contains("\"text\":\"테스트 문장\"");
            respondJson(exchange, 200, "{\"id\":\"generation-1\"}");
        });
        server.createContext("/history/generation-1", exchange -> {
            String status = historyCalls.incrementAndGet() < 2 ? "generating" : "completed";
            respondJson(exchange, 200, "{\"status\":\"" + status + "\"}");
        });
        server.createContext("/audio/generation-1", exchange -> {
            exchange.getResponseHeaders().set("Content-Type", "audio/wav");
            exchange.sendResponseHeaders(200, expectedAudio.length);
            exchange.getResponseBody().write(expectedAudio);
            exchange.close();
        });
        server.start();

        TtsProperties properties = new TtsProperties();
        properties.getVoicebox().setBaseUrl("http://127.0.0.1:" + server.getAddress().getPort());
        properties.getVoicebox().setProfileId("recording-6-profile");
        properties.getVoicebox().setPollMillis(100);
        properties.getVoicebox().setTimeoutSeconds(3);

        VoiceboxTtsProvider provider = new VoiceboxTtsProvider(properties, new ObjectMapper());
        Path result = provider.synthesize("테스트 문장");

        try {
            assertThat(Files.readAllBytes(result)).isEqualTo(expectedAudio);
            assertThat(historyCalls).hasValue(2);
        } finally {
            Files.deleteIfExists(result);
        }
    }

    private static void respondJson(HttpExchange exchange, int status, String body) throws IOException {
        byte[] bytes = body.getBytes(StandardCharsets.UTF_8);
        exchange.getResponseHeaders().set("Content-Type", "application/json");
        exchange.sendResponseHeaders(status, bytes.length);
        exchange.getResponseBody().write(bytes);
        exchange.close();
    }
}
