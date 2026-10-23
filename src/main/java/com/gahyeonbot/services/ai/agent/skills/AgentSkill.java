package com.gahyeonbot.services.ai.agent.skills;

import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.util.HexFormat;
import java.util.List;
import java.util.Set;

/** A reviewed procedure, not an authority grant or a user memory. */
public record AgentSkill(String id, String version, String problem, String whenToUse,
        Set<String> allowedTools, Set<String> requiredEvidenceTools, int maxToolCalls,
        List<String> completionCriteria, String instructions, String digest) {
    public AgentSkill {
        if (id == null || !id.matches("[a-z][a-z0-9-]{0,63}")
                || version == null || !version.matches("[0-9]+\\.[0-9]+\\.[0-9]+"))
            throw new IllegalArgumentException("Invalid skill identity");
        if (problem == null || problem.isBlank() || whenToUse == null || whenToUse.isBlank()
                || instructions == null || instructions.isBlank() || instructions.length() > 16000)
            throw new IllegalArgumentException("Skill requires a bounded problem and procedure");
        allowedTools = Set.copyOf(allowedTools);
        requiredEvidenceTools = Set.copyOf(requiredEvidenceTools);
        completionCriteria = List.copyOf(completionCriteria);
        if (allowedTools.isEmpty() || allowedTools.size() > 32 || requiredEvidenceTools.isEmpty()
                || !allowedTools.containsAll(requiredEvidenceTools) || completionCriteria.isEmpty()
                || maxToolCalls < requiredEvidenceTools.size() || maxToolCalls > 32)
            throw new IllegalArgumentException("Invalid skill execution contract");
        if (allowedTools.stream().anyMatch(name -> !name.matches("[a-zA-Z][a-zA-Z0-9_]{0,63}")
                || name.startsWith("agent_skill_")))
            throw new IllegalArgumentException("Invalid or reserved skill tool name");
        if (digest == null || !digest.matches("[a-f0-9]{64}"))
            throw new IllegalArgumentException("Skill content digest required");
    }

    public String identity() { return id + "@" + version; }

    public static String sha256(String content) {
        try {
            return HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256")
                    .digest(content.getBytes(StandardCharsets.UTF_8)));
        } catch (java.security.NoSuchAlgorithmException impossible) {
            throw new IllegalStateException(impossible);
        }
    }
}
