package com.gahyeonbot.services.ai.agent.skills;

import com.fasterxml.jackson.databind.ObjectMapper;
import org.springframework.core.io.ClassPathResource;
import org.springframework.stereotype.Component;

import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.util.*;

@Component
public final class AgentSkillCatalog {
    private final Map<String, AgentSkill> skills;

    public AgentSkillCatalog() {
        this(loadReleased());
    }

    public AgentSkillCatalog(Collection<AgentSkill> definitions) {
        Map<String, AgentSkill> indexed = new LinkedHashMap<>();
        for (AgentSkill skill : definitions) {
            if (indexed.putIfAbsent(skill.identity(), skill) != null)
                throw new IllegalArgumentException("Duplicate skill version: " + skill.identity());
        }
        skills = Collections.unmodifiableMap(indexed);
    }

    public Collection<AgentSkill> all() { return skills.values(); }

    public AgentSkill require(String id, String version) {
        AgentSkill skill = skills.get(id + "@" + version);
        if (skill == null) throw new IllegalArgumentException("Unknown released skill version");
        return skill;
    }

    private static List<AgentSkill> loadReleased() {
        ObjectMapper json = new ObjectMapper();
        try {
            String[] packages = json.readValue(read("agent-skills/index.json"), String[].class);
            if (packages.length > 64) throw new IllegalArgumentException("Skill catalog too large");
            List<AgentSkill> result = new ArrayList<>();
            for (String path : packages) {
                if (!path.matches("[a-z][a-z0-9-]{0,63}/[0-9]+\\.[0-9]+\\.[0-9]+"))
                    throw new IllegalArgumentException("Invalid skill package path");
                String manifest = read("agent-skills/" + path + "/manifest.json");
                Manifest metadata = json.readValue(manifest, Manifest.class);
                if (metadata.schemaVersion != 1 || !"released".equals(metadata.status)
                        || !path.equals(metadata.id + "/" + metadata.version))
                    throw new IllegalArgumentException("Only reviewed released packages may be indexed");
                String instructions = read("agent-skills/" + path + "/SKILL.md");
                result.add(new AgentSkill(metadata.id, metadata.version, metadata.problem,
                        metadata.whenToUse, metadata.allowedTools, metadata.requiredEvidenceTools,
                        metadata.maxToolCalls, metadata.completionCriteria, instructions,
                        AgentSkill.sha256(manifest + "\n" + instructions)));
            }
            return result;
        } catch (IOException failure) {
            throw new IllegalStateException("Cannot load released skill catalog", failure);
        }
    }

    private static String read(String path) throws IOException {
        try (var input = new ClassPathResource(path).getInputStream()) {
            byte[] bytes = input.readNBytes(32769);
            if (bytes.length > 32768) throw new IOException("Skill resource too large");
            return new String(bytes, StandardCharsets.UTF_8);
        }
    }

    private record Manifest(int schemaVersion, String status, String id, String version,
            String problem, String whenToUse, Set<String> allowedTools,
            Set<String> requiredEvidenceTools, int maxToolCalls, List<String> completionCriteria) {}
}
