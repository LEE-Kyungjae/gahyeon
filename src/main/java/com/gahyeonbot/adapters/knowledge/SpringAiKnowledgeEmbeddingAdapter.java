package com.gahyeonbot.adapters.knowledge;

import com.gahyeonbot.application.knowledge.KnowledgeEmbeddingPort;
import org.springframework.ai.embedding.EmbeddingModel;
import org.springframework.beans.factory.ObjectProvider;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;

import java.util.ArrayList;
import java.util.List;

@Component
public class SpringAiKnowledgeEmbeddingAdapter implements KnowledgeEmbeddingPort {
    private final ObjectProvider<EmbeddingModel> models;
    private final String modelId;

    public SpringAiKnowledgeEmbeddingAdapter(ObjectProvider<EmbeddingModel> models,
            @Value("${gahyeon.knowledge.embedding-model:configured-spring-ai-embedding}") String modelId) {
        this.models = models;
        this.modelId = modelId;
    }

    @Override public boolean isReady() { return models.orderedStream().findFirst().isPresent(); }

    @Override
    public List<Double> embed(String text) {
        EmbeddingModel model = models.orderedStream().findFirst().orElse(null);
        if (model == null) return List.of();
        float[] raw = model.embed(text);
        List<Double> vector = new ArrayList<>(raw.length);
        for (float value : raw) vector.add((double) value);
        return List.copyOf(vector);
    }

    @Override public String modelId() { return modelId; }
}
