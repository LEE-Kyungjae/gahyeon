package com.gahyeonbot.services.ai.agent.work;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.gahyeonbot.core.tool.ToolDecision;
import com.gahyeonbot.services.ai.agent.AgentRequest;
import com.gahyeonbot.services.ai.agent.skills.*;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;
import java.nio.charset.StandardCharsets;
import java.util.*;
import java.util.concurrent.TimeUnit;

/** Identity and destinations come from server configuration, never model arguments. */
@Component
public final class OwnerWorkTools implements RequestScopedTools {
    interface Transport { JsonNode call(String target, String envelope); }
    private final long owner, scope;
    private final boolean enabled;
    private final Transport transport;
    @org.springframework.beans.factory.annotation.Autowired
    public OwnerWorkTools(@Value("${gahyeon.agent.owner-work.enabled:false}") boolean enabled,
            @Value("${gahyeon.agent.owner-work.actor-id:0}") long owner,
            @Value("${gahyeon.agent.owner-work.scope-id:0}") long scope) {
        this(enabled, owner, scope, OwnerWorkTools::ssh);
    }
    OwnerWorkTools(boolean enabled, long owner, long scope, Transport transport) {
        this.enabled = enabled; this.owner = owner; this.scope = scope; this.transport = transport;
    }
    public List<AgentToolRegistry.Binding> bindings(AgentRequest request) {
        if (!enabled || owner <= 0 || scope <= 0 || request.actorId().value() != owner
                || !Objects.equals(request.toolScopeId(), scope)) return List.of();
        var callback = new WorkToolCallback("owner_workspace_task",
                "본인 전용 Mac/land 작업 폴더 조회·파일 수정·격리 테스트. 실제 인자에 대한 승인이 필요하다.", """
                {"type":"object","properties":{
                "target":{"type":"string","enum":["mac","land"]},
                "action":{"type":"string","enum":["status","list","read","write","test"]},
                "path":{"type":"string"},"content":{"type":"string"},"expectedSha256":{"type":"string"}},
                "required":["target","action"],"additionalProperties":false}
                """, args -> execute(request, args));
        return List.of(new AgentToolRegistry.Binding("mcp:owner-work", callback,
                ToolDecision.REQUIRE_APPROVAL, Set.of(owner), scope));
    }
    private Object execute(AgentRequest request, JsonNode args) {
        WorkToolCallback.keys(args, "target", "action", "path", "content", "expectedSha256");
        String target = WorkToolCallback.text(args, "target", 8);
        if (!Set.of("mac", "land").contains(target)) throw new IllegalArgumentException("Unknown target");
        String original = request.message().toLowerCase(Locale.ROOT);
        if (!(target.equals("mac") ? original.contains("mac") || original.contains("맥") : original.contains("land")))
            throw new SecurityException("Target must be named in the original user request");
        String action = WorkToolCallback.text(args, "action", 12);
        if (!Set.of("status", "list", "read", "write", "test").contains(action)) throw new IllegalArgumentException("Unknown action");
        try {
            var json = new ObjectMapper();
            var envelope = json.createObjectNode();
            envelope.put("actor", Long.toString(owner)); envelope.put("scope", Long.toString(scope));
            envelope.put("jobId", AgentSkill.sha256(request.requestId() + "\n" + args));
            envelope.set("task", args);
            JsonNode result = transport.call(target, json.writeValueAsString(envelope));
            if (result == null || !result.path("jobId").asText().equals(envelope.path("jobId").asText())
                    || !result.path("ok").asBoolean(false)) throw new IllegalStateException("Worker did not complete task successfully");
            return Map.of("untrusted", true, "result", result);
        } catch (java.io.IOException e) { throw new IllegalStateException("Worker protocol failed"); }
    }
    private static JsonNode ssh(String target, String envelope) {
        Process process = null;
        try {
            process = new ProcessBuilder("/usr/bin/ssh", "-F", "/app/owner-work/ssh_config",
                    "-o", "BatchMode=yes", "-o", "StrictHostKeyChecking=yes", "-o", "ConnectTimeout=8",
                    "-T", "gahyeon-" + target + "-worker").redirectError(ProcessBuilder.Redirect.DISCARD).start();
            try (var input = process.getOutputStream()) { input.write((envelope + "\n").getBytes(StandardCharsets.UTF_8)); }
            final Process child = process;
            var bytes = java.util.concurrent.CompletableFuture.supplyAsync(() -> {
                try (var output = child.getInputStream()) { return output.readNBytes(131073); }
                catch (java.io.IOException e) { throw new IllegalStateException("Worker read failed"); }
            });
            byte[] output = bytes.get(100, TimeUnit.SECONDS);
            if (output.length > 131072 || !process.waitFor(3, TimeUnit.SECONDS) || process.exitValue() != 0)
                throw new IllegalStateException("Worker transport failed");
            return new ObjectMapper().readTree(output);
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt(); throw new IllegalStateException("Worker request interrupted");
        } catch (Exception e) { throw new IllegalStateException("Worker unavailable; no completion claimed"); }
        finally { if (process != null && process.isAlive()) process.destroyForcibly(); }
    }
}
