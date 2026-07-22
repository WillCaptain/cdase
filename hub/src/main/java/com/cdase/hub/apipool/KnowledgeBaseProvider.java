package com.cdase.hub.apipool;

import java.util.List;
import java.util.Map;

public interface KnowledgeBaseProvider extends AutoCloseable {

    Map<String, Object> upsert(
            ApiDefinition definition,
            float[] embedding,
            String embeddingModel,
            String contentHash,
            boolean replaceEmbedding
    ) throws Exception;

    Map<String, Object> get(String apiId, String version) throws Exception;

    List<Map<String, Object>> search(
            String query,
            float[] queryEmbedding,
            Map<String, String> filters,
            int limit
    ) throws Exception;

    Map<String, Object> transition(
            String apiId,
            String version,
            ApiStatus status,
            String actor,
            String note,
            String supersededByVersion
    ) throws Exception;

    Map<String, Object> graph(String system) throws Exception;

    Map<String, Object> health() throws Exception;

    @Override
    default void close() throws Exception {
    }
}
