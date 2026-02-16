package com.gahyeonbot.services.tts;

import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;

import java.io.ByteArrayOutputStream;
import java.io.InputStream;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.Optional;
import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.TimeUnit;

@Slf4j
@Service
@RequiredArgsConstructor
public class TtsService {
    private final TtsProperties props;
    private final ObjectMapper objectMapper = new ObjectMapper();

    public boolean isEnabled() {
        return props.isEnabled();
    }

    public int getMaxChars() {
        return props.getMaxChars();
    }

    public List<Path> synthesizeSegmentsToWav(String text) throws Exception {
        List<String> segments = splitAndChunk(text);
        List<Path> out = new ArrayList<>(segments.size());
        for (String s : segments) {
            out.add(synthesizeToAudio(s));
        }
        return out;
    }

    private List<String> splitAndChunk(String text) throws Exception {
        List<String> sentences = splitSentences(text);
        List<String> out = new ArrayList<>();
        int max = Math.max(20, props.getSegmentMaxChars());
        for (String s : sentences) {
            String trimmed = (s == null) ? "" : s.trim();
            if (trimmed.isEmpty()) continue;
            if (trimmed.length() <= max) {
                out.add(trimmed);
                continue;
            }
            // Chunk long sentence into fixed windows to avoid synthesis failures.
            for (int i = 0; i < trimmed.length(); i += max) {
                int end = Math.min(trimmed.length(), i + max);
                String part = trimmed.substring(i, end).trim();
                if (!part.isEmpty()) out.add(part);
            }
        }
        return out;
    }

    private List<String> splitSentences(String text) throws Exception {
        String script = props.getKss().getScript();
        // If running outside Docker (dev), allow local path.
        if (!Files.exists(Path.of(script))) {
            script = "scripts/tts_split.py";
        }

        ProcessBuilder pb = new ProcessBuilder(
                props.getKss().getPython(),
                script
        );
        pb.redirectErrorStream(false);
        Process p = pb.start();
        StreamGobbler outGobbler = StreamGobbler.start(p.getInputStream());
        StreamGobbler errGobbler = StreamGobbler.start(p.getErrorStream());
        try (var os = p.getOutputStream()) {
            os.write(text.getBytes(StandardCharsets.UTF_8));
        }

        boolean ok = p.waitFor(props.getTimeoutSeconds(), TimeUnit.SECONDS);
        if (!ok) {
            p.destroyForcibly();
            throw new IllegalStateException("KSS splitter timeout");
        }
        String stdout = outGobbler.getOutput();
        String stderr = errGobbler.getOutput();
        if (p.exitValue() != 0) {
            throw new IllegalStateException("KSS splitter failed: " + stderr);
        }

        String json = extractJsonPayload(stdout).orElse(stdout);
        try {
            return objectMapper.readValue(json, new TypeReference<>() {});
        } catch (Exception e) {
            // Include both streams for diagnosis but keep it compact.
            String msg = "KSS splitter returned non-JSON output. stdout=" + abbreviate(stdout) + " stderr=" + abbreviate(stderr);
            throw new IllegalStateException(msg, e);
        }
    }

    private Path synthesizeToAudio(String text) throws Exception {
        Path dir = Path.of(System.getProperty("java.io.tmpdir"), "gahyeonbot-tts");
        Files.createDirectories(dir);
        Path audio = Files.createTempFile(dir, "tts_", ".mp3");

        ExecResult result = runEdgeSynthesis(text, audio);
        if (!result.ok()) {
            safeDelete(audio);
            throw new IllegalStateException("Edge TTS failed: " + result.output());
        }

        // Basic sanity check.
        if (!Files.exists(audio) || Files.size(audio) < 256) {
            safeDelete(audio);
            throw new IllegalStateException("Edge TTS produced empty audio");
        }
        return audio;
    }

    private ExecResult runEdgeSynthesis(String text, Path outputFile) throws Exception {
        List<String> cmd = new ArrayList<>();
        cmd.add(props.getEdge().getBin());
        cmd.add("--voice");
        cmd.add(props.getEdge().getVoice());
        cmd.add("--rate");
        cmd.add(props.getEdge().getRate());
        cmd.add("--pitch");
        cmd.add(props.getEdge().getPitch());
        cmd.add("--text");
        cmd.add(text);
        cmd.add("--write-media");
        cmd.add(outputFile.toString());

        ProcessBuilder pb = new ProcessBuilder(cmd);
        pb.redirectErrorStream(true);
        Process p = pb.start();
        StreamGobbler gobbler = StreamGobbler.start(p.getInputStream());
        try (var os = p.getOutputStream()) {
            os.write(text.getBytes(StandardCharsets.UTF_8));
        }

        boolean ok = p.waitFor(props.getTimeoutSeconds(), TimeUnit.SECONDS);
        if (!ok) {
            p.destroyForcibly();
            return new ExecResult(false, "Edge TTS timeout");
        }
        return new ExecResult(p.exitValue() == 0, gobbler.getOutput());
    }
    private record ExecResult(boolean ok, String output) {}

    private static Optional<String> extractJsonPayload(String s) {
        if (s == null) return Optional.empty();
        int startArr = s.indexOf('[');
        int endArr = s.lastIndexOf(']');
        if (startArr >= 0 && endArr > startArr) {
            return Optional.of(s.substring(startArr, endArr + 1).trim());
        }
        int startObj = s.indexOf('{');
        int endObj = s.lastIndexOf('}');
        if (startObj >= 0 && endObj > startObj) {
            return Optional.of(s.substring(startObj, endObj + 1).trim());
        }
        return Optional.empty();
    }

    private static String abbreviate(String s) {
        if (s == null) return "";
        String t = s.replace("\n", "\\n").replace("\r", "\\r");
        int max = 400;
        if (t.length() <= max) return t;
        return t.substring(0, max) + "...";
    }

    private static final class StreamGobbler implements Runnable {
        private final InputStream is;
        private final ByteArrayOutputStream baos = new ByteArrayOutputStream();
        private final Thread thread;

        private StreamGobbler(InputStream is) {
            this.is = is;
            this.thread = new Thread(this, "tts-proc-gobbler");
            this.thread.setDaemon(true);
        }

        static StreamGobbler start(InputStream is) {
            StreamGobbler g = new StreamGobbler(is);
            g.thread.start();
            return g;
        }

        @Override
        public void run() {
            try {
                is.transferTo(baos);
            } catch (Exception ignored) {
            }
        }

        String getOutput() {
            try {
                thread.join(200); // best-effort; stream should be closed after process exit
            } catch (InterruptedException ignored) {
                Thread.currentThread().interrupt();
            }
            return baos.toString(StandardCharsets.UTF_8);
        }
    }

    private static void safeDelete(Path p) {
        try {
            Files.deleteIfExists(p);
        } catch (Exception ignored) {
        }
    }
}
