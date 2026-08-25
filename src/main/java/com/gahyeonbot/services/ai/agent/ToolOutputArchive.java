package com.gahyeonbot.services.ai.agent;

import java.util.Optional;

/** Keeps the exact original output addressable by digest for the configured recovery window. */
interface ToolOutputArchive {
    void store(String digest, String toolName, String originalOutput);

    Optional<String> retrieve(String digest);
}
