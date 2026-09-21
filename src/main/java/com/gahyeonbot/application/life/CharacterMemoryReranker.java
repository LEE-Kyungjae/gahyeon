package com.gahyeonbot.application.life;

import com.gahyeonbot.core.life.CharacterMemory;
import java.util.List;

/** Reorders already authorized, unexpired candidates; never retrieves or creates memory. */
public interface CharacterMemoryReranker {
    List<CharacterMemory> rerank(String query, List<CharacterMemory> candidates);
}
