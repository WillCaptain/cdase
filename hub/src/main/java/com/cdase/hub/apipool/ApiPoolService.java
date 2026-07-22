package com.cdase.hub.apipool;

import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

public final class ApiPoolService implements AutoCloseable {

    private final KnowledgeBaseProvider provider;
    private final EmbeddingProvider embeddings;

    public ApiPoolService(KnowledgeBaseProvider provider, EmbeddingProvider embeddings) {
        this.provider = provider;
        this.embeddings = embeddings;
    }

    public Map<String, Object> publish(Map<String, Object> body) throws Exception {
        ApiDefinition definition = ApiDefinition.fromMap(body);
        Map<String, Object> current = provider.get(definition.apiId(), definition.version());
        if (current.isEmpty() && definition.status() != ApiStatus.DEVELOPING) {
            throw new IllegalStateException(
                    "new API versions must be published as DEVELOPING"
            );
        }
        if (!current.isEmpty()
                && !definition.status().name().equals(current.get("status"))) {
            throw new IllegalStateException(
                    "lifecycle changes require the transition endpoint"
            );
        }
        if (definition.status() == ApiStatus.RELEASED
                && definition.source().commit().endsWith("+dirty")) {
            throw new IllegalStateException(
                    "RELEASED APIs must reference a committed source revision"
            );
        }
        String contentHash = definition.contentHash();
        String targetModel = embeddings.model();
        int targetDimensions = embeddings.available() ? embeddings.dimensions() : 0;
        boolean replaceEmbedding = current.isEmpty()
                || !contentHash.equals(current.get("content_hash"))
                || !targetModel.equals(current.get("embedding_model"))
                || integer(current.get("embedding_dimensions"), 0) != targetDimensions;
        float[] vector = null;
        String warning = null;
        if (replaceEmbedding && embeddings.available()) {
            try {
                vector = embeddings.embedDocument(definition.canonicalEmbeddingText());
            } catch (Exception e) {
                warning = "API stored without embedding; rerun api-sync after embedding service recovers";
            }
        }
        Map<String, Object> stored = provider.upsert(
                definition,
                vector,
                targetModel,
                contentHash,
                replaceEmbedding
        );
        Map<String, Object> response = new LinkedHashMap<>();
        response.put("ok", true);
        response.put("api", stored);
        response.put("embedding_updated", replaceEmbedding);
        if (warning != null) {
            response.put("warning", warning);
        }
        return response;
    }

    public Map<String, Object> search(Map<String, Object> body) throws Exception {
        String query = text(body.get("query"));
        if (query == null) {
            throw new IllegalArgumentException("missing field: query");
        }
        int limit = integer(body.get("limit"), 20);
        Map<String, String> filters = filters(body.get("filters"));
        float[] vector = null;
        String warning = null;
        if (embeddings.available()) {
            try {
                vector = embeddings.embedQuery(query);
            } catch (Exception e) {
                warning = "semantic embedding unavailable; lexical search used";
            }
        }
        List<Map<String, Object>> results = provider.search(query, vector, filters, limit);
        Map<String, Object> response = new LinkedHashMap<>();
        response.put("ok", true);
        response.put("query", query);
        response.put("results", results);
        response.put("count", results.size());
        response.put("embedding_model", embeddings.model());
        response.put("semantic_search", vector != null);
        if (warning != null) {
            response.put("warning", warning);
        }
        return response;
    }

    public Map<String, Object> get(String apiId, String version) throws Exception {
        Map<String, Object> api = provider.get(apiId, version);
        if (api.isEmpty()) {
            return Map.of("ok", false, "error", "API not found");
        }
        return Map.of("ok", true, "api", api);
    }

    public Map<String, Object> transition(
            String apiId,
            Map<String, Object> body
    ) throws Exception {
        String version = text(body.get("version"));
        if (version == null) {
            throw new IllegalArgumentException("missing field: version");
        }
        ApiStatus status = ApiStatus.parse(body.get("status"));
        Map<String, Object> current = provider.get(apiId, version);
        if (current.isEmpty()) {
            throw new IllegalArgumentException("API version not found");
        }
        if (status == ApiStatus.RELEASED) {
            Object sourceValue = current.get("source");
            if (sourceValue instanceof Map<?, ?> source
                    && String.valueOf(source.get("commit")).endsWith("+dirty")) {
                throw new IllegalStateException(
                        "RELEASED APIs must reference a committed source revision"
                );
            }
        }
        String supersededBy = text(body.get("superseded_by_version"));
        if (status == ApiStatus.SUPERSEDED) {
            if (supersededBy == null) {
                throw new IllegalArgumentException(
                        "superseded_by_version is required for SUPERSEDED"
                );
            }
            Map<String, Object> successor = provider.get(apiId, supersededBy);
            if (successor.isEmpty()
                    || !ApiStatus.RELEASED.name().equals(successor.get("status"))) {
                throw new IllegalStateException(
                        "superseding version must exist and be RELEASED"
                );
            }
        }
        Map<String, Object> api = provider.transition(
                apiId,
                version,
                status,
                text(body.get("actor")),
                text(body.get("note")),
                supersededBy
        );
        return Map.of("ok", true, "api", api);
    }

    public Map<String, Object> graph(String system) throws Exception {
        return Map.of("ok", true, "graph", provider.graph(system));
    }

    @SuppressWarnings("unchecked")
    public Map<String, Object> verify(Map<String, Object> body) throws Exception {
        Object raw = body.get("apis");
        if (!(raw instanceof List<?> list) || list.isEmpty()) {
            throw new IllegalArgumentException("apis must be a non-empty list");
        }
        List<Map<String, Object>> states = new java.util.ArrayList<>();
        int synced = 0;
        int stale = 0;
        int missing = 0;
        int conflict = 0;
        for (Object item : list) {
            if (!(item instanceof Map<?, ?> map)) {
                throw new IllegalArgumentException("each api entry must be an object");
            }
            Map<String, Object> entry = (Map<String, Object>) map;
            String apiId = text(entry.get("api_id"));
            String version = text(entry.get("version"));
            if (apiId == null || version == null) {
                throw new IllegalArgumentException("each api requires api_id and version");
            }
            Map<String, Object> remote = provider.get(apiId, version);
            Map<String, Object> state = new LinkedHashMap<>();
            state.put("api_id", apiId);
            state.put("version", version);
            if (remote.isEmpty()) {
                state.put("state", "MISSING");
                missing++;
                states.add(state);
                continue;
            }
            Map<String, Object> localSource = asMap(entry.get("source"));
            Map<String, Object> remoteSource = asMap(remote.get("source"));
            java.util.List<String> reasons = new java.util.ArrayList<>();
            String localRepo = text(localSource.get("repo"));
            String remoteRepo = text(remoteSource.get("repo"));
            if (localRepo != null && remoteRepo != null && !localRepo.equals(remoteRepo)) {
                state.put("state", "CONFLICT");
                reasons.add("source repository ownership differs");
                conflict++;
            } else {
                String localHash = text(entry.get("content_hash"));
                if (localHash == null && entry.containsKey("capability")) {
                    localHash = ApiDefinition.fromMap(entry).contentHash();
                }
                String remoteHash = text(remote.get("content_hash"));
                if (localHash != null && remoteHash != null && !localHash.equals(remoteHash)) {
                    reasons.add("semantic content hash differs");
                }
                String localCommit = text(localSource.get("commit"));
                String remoteCommit = text(remoteSource.get("commit"));
                if (localCommit != null && remoteCommit != null
                        && !localCommit.equals(remoteCommit)) {
                    reasons.add("source commit differs");
                }
                String localPath = text(localSource.get("path"));
                String remotePath = text(remoteSource.get("path"));
                if (localPath != null && remotePath != null && !localPath.equals(remotePath)) {
                    reasons.add("source path differs");
                }
                if (reasons.isEmpty()) {
                    state.put("state", "SYNCED");
                    synced++;
                } else {
                    state.put("state", "STALE");
                    stale++;
                }
            }
            state.put("reasons", reasons);
            state.put("local_content_hash", entry.get("content_hash"));
            state.put("remote_content_hash", remote.get("content_hash"));
            states.add(state);
        }
        Map<String, Object> counts = new LinkedHashMap<>();
        counts.put("SYNCED", synced);
        counts.put("STALE", stale);
        counts.put("MISSING", missing);
        counts.put("CONFLICT", conflict);
        Map<String, Object> response = new LinkedHashMap<>();
        response.put("ok", missing == 0 && stale == 0 && conflict == 0);
        response.put("states", states);
        response.put("counts", counts);
        return response;
    }

    public Map<String, Object> health() throws Exception {
        Map<String, Object> response = new LinkedHashMap<>(provider.health());
        response.put("embedding_available", embeddings.available());
        response.put("embedding_model", embeddings.model());
        response.put("embedding_dimensions", embeddings.dimensions());
        return response;
    }

    @Override
    public void close() throws Exception {
        provider.close();
    }

    private static String text(Object value) {
        if (value == null) {
            return null;
        }
        String text = String.valueOf(value).trim();
        return text.isEmpty() ? null : text;
    }

    private static int integer(Object value, int fallback) {
        if (value == null) {
            return fallback;
        }
        try {
            return Integer.parseInt(String.valueOf(value));
        } catch (NumberFormatException e) {
            return fallback;
        }
    }

    private static Map<String, String> filters(Object value) {
        if (!(value instanceof Map<?, ?> map)) {
            return Map.of();
        }
        Map<String, String> out = new LinkedHashMap<>();
        for (String key : List.of(
                "system",
                "module",
                "status",
                "kind",
                "context_system",
                "context_module"
        )) {
            String filter = text(map.get(key));
            if (filter != null) {
                out.put(key, "status".equals(key) ? filter.toUpperCase() : filter);
            }
        }
        return out;
    }

    @SuppressWarnings("unchecked")
    private static Map<String, Object> asMap(Object value) {
        if (value instanceof Map<?, ?> map) {
            return (Map<String, Object>) map;
        }
        return Map.of();
    }
}
