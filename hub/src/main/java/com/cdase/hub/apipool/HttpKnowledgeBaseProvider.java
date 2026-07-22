package com.cdase.hub.apipool;

import com.cdase.hub.http.JsonUtil;

import java.net.URI;
import java.net.URLEncoder;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.nio.charset.StandardCharsets;
import java.time.Duration;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/**
 * Server-side adapter for relocating the API pool to an existing HTTP knowledge
 * service. Clients still communicate only with CDASE Hub.
 */
public final class HttpKnowledgeBaseProvider implements KnowledgeBaseProvider {

    private final HttpClient client;
    private final String baseUrl;
    private final String token;

    public HttpKnowledgeBaseProvider(String baseUrl, String token) {
        if (baseUrl == null || baseUrl.isBlank()) {
            throw new IllegalArgumentException("legacy knowledge-base URL is required");
        }
        this.baseUrl = baseUrl.replaceAll("/+$", "");
        this.token = token;
        this.client = HttpClient.newBuilder()
                .connectTimeout(Duration.ofSeconds(5))
                .build();
    }

    @Override
    public Map<String, Object> upsert(
            ApiDefinition definition,
            float[] embedding,
            String embeddingModel,
            String contentHash,
            boolean replaceEmbedding
    ) throws Exception {
        Map<String, Object> body = new LinkedHashMap<>(definition.toMap());
        body.put("embedding", floats(embedding));
        body.put("embedding_model", embeddingModel);
        body.put("content_hash", contentHash);
        body.put("replace_embedding", replaceEmbedding);
        return object(post("/api-pool/apis", body), "api");
    }

    @Override
    public Map<String, Object> get(String apiId, String version) throws Exception {
        String path = "/api-pool/apis?api_id=" + encode(apiId);
        if (version != null && !version.isBlank()) {
            path += "&version=" + encode(version);
        }
        Map<String, Object> response = get(path);
        if (Boolean.FALSE.equals(response.get("ok"))) {
            return Map.of();
        }
        return object(response, "api");
    }

    @Override
    public List<Map<String, Object>> search(
            String query,
            float[] queryEmbedding,
            Map<String, String> filters,
            int limit
    ) throws Exception {
        Map<String, Object> body = new LinkedHashMap<>();
        body.put("query", query);
        body.put("embedding", floats(queryEmbedding));
        body.put("filters", filters == null ? Map.of() : filters);
        body.put("limit", limit);
        Map<String, Object> response = post("/api-pool/search", body);
        Object value = response.get("results");
        if (!(value instanceof List<?> list)) {
            return List.of();
        }
        @SuppressWarnings("unchecked")
        List<Map<String, Object>> results = (List<Map<String, Object>>) (List<?>) list;
        return results;
    }

    @Override
    public Map<String, Object> transition(
            String apiId,
            String version,
            ApiStatus status,
            String actor,
            String note,
            String supersededByVersion
    ) throws Exception {
        Map<String, Object> body = new LinkedHashMap<>();
        body.put("version", version);
        body.put("status", status.name());
        body.put("actor", actor);
        body.put("note", note);
        body.put("superseded_by_version", supersededByVersion);
        body.put("api_id", apiId);
        return object(post("/api-pool/transition", body), "api");
    }

    @Override
    public Map<String, Object> graph(String system) throws Exception {
        String path = "/api-pool/graph";
        if (system != null && !system.isBlank()) {
            path += "?system=" + encode(system);
        }
        return object(get(path), "graph");
    }

    @Override
    public Map<String, Object> health() throws Exception {
        return get("/api-pool/health");
    }

    private Map<String, Object> get(String path) throws Exception {
        HttpRequest.Builder builder = HttpRequest.newBuilder(URI.create(baseUrl + path))
                .timeout(Duration.ofSeconds(20))
                .GET();
        authorize(builder);
        return send(builder.build());
    }

    private Map<String, Object> post(String path, Map<String, Object> body) throws Exception {
        HttpRequest.Builder builder = HttpRequest.newBuilder(URI.create(baseUrl + path))
                .timeout(Duration.ofSeconds(30))
                .header("Content-Type", "application/json")
                .POST(HttpRequest.BodyPublishers.ofByteArray(JsonUtil.toBytes(body)));
        authorize(builder);
        return send(builder.build());
    }

    private Map<String, Object> send(HttpRequest request) throws Exception {
        HttpResponse<String> response = client.send(
                request,
                HttpResponse.BodyHandlers.ofString()
        );
        Map<String, Object> body = JsonUtil.parseMap(response.body());
        if (response.statusCode() < 200 || response.statusCode() >= 300) {
            throw new IllegalStateException(
                    "legacy knowledge base returned HTTP " + response.statusCode()
                            + ": " + body.getOrDefault("error", "unknown error")
            );
        }
        return body;
    }

    private void authorize(HttpRequest.Builder builder) {
        if (token != null && !token.isBlank()) {
            builder.header("Authorization", "Bearer " + token);
        }
    }

    private static List<Float> floats(float[] vector) {
        if (vector == null) {
            return List.of();
        }
        java.util.ArrayList<Float> out = new java.util.ArrayList<>(vector.length);
        for (float value : vector) {
            out.add(value);
        }
        return out;
    }

    private static String encode(String value) {
        return URLEncoder.encode(value, StandardCharsets.UTF_8);
    }

    @SuppressWarnings("unchecked")
    private static Map<String, Object> object(Map<String, Object> response, String field) {
        Object value = response.get(field);
        if (!(value instanceof Map<?, ?> map)) {
            throw new IllegalStateException("legacy knowledge base response missing '" + field + "'");
        }
        return (Map<String, Object>) map;
    }
}
