package com.gahyeonbot.services.ai.agent.skills;

import java.util.List;

/** Contains procedure identities and hashes only, never raw user data or tool output. */
public interface AgentSkillJournal {
    List<Entry> read(String runId);
    void append(String runId, Entry entry);

    record Entry(String kind, String skillId, String version, String digest,
            String tool, String resultDigest) {}
}
