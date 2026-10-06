package com.gahyeonbot.application.knowledge;

import java.util.List;

public interface KnowledgeEmbeddingPort {
    boolean isReady();
    List<Double> embed(String text);
    String modelId();
}
