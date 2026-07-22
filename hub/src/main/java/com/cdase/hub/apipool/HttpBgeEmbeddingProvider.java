package com.cdase.hub.apipool;

import com.cdase.hub.http.JsonUtil;

import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.time.Duration;
import java.util.List;
import java.util.Map;

/**
 * OpenAI-compatible HTTP embedding client. A lightweight local server can host
 * BAAI/bge-small-en-v1.5 while the Hub remains Java-only.
 */
public final class HttpBgeEmbeddingProvider implements EmbeddingProvider {

    public static final String DEFAULT_MODEL = "BAAI/bge-small-en-v1.5";
    public static final int DEFAULT_DIMENSIONS = 384;

    private final HttpClient client;
    private final URI endpoint;
    private final String model;
    private final String token;

    public HttpBgeEmbeddingProvider(String endpoint, String model, String token) {
        if (endpoint == null || endpoint.isBlank()) {
            throw new IllegalArgumentException("embedding endpoint is required");
        }
        this.endpoint = URI.create(endpoint);
        this.model = model == null || model.isBlank() ? DEFAULT_MODEL : model;
        this.token = token;
        this.client = HttpClient.newBuilder()
                .connectTimeout(Duration.ofSeconds(5))
                .build();
    }

    @Override
    public float[] embed(String text) throws Exception {
        Map<String, Object> payload = Map.of("model", model, "input", text);
        HttpRequest.Builder builder = HttpRequest.newBuilder(endpoint)
                .timeout(Duration.ofSeconds(30))
                .header("Content-Type", "application/json")
                .POST(HttpRequest.BodyPublishers.ofByteArray(JsonUtil.toBytes(payload)));
        if (token != null && !token.isBlank()) {
            builder.header("Authorization", "Bearer " + token);
        }
        HttpResponse<String> response = client.send(
                builder.build(),
                HttpResponse.BodyHandlers.ofString()
        );
        if (response.statusCode() < 200 || response.statusCode() >= 300) {
            throw new IllegalStateException(
                    "embedding service returned HTTP " + response.statusCode()
            );
        }
        Map<String, Object> decoded = JsonUtil.parseMap(response.body());
        Object dataValue = decoded.get("data");
        if (!(dataValue instanceof List<?> data) || data.isEmpty()
                || !(data.get(0) instanceof Map<?, ?> first)
                || !(first.get("embedding") instanceof List<?> values)) {
            throw new IllegalStateException("embedding service returned an invalid response");
        }
        if (values.size() != dimensions()) {
            throw new IllegalStateException(
                    "expected " + dimensions() + " embedding dimensions, got " + values.size()
            );
        }
        float[] vector = new float[values.size()];
        for (int i = 0; i < values.size(); i++) {
            vector[i] = ((Number) values.get(i)).floatValue();
        }
        return VectorMath.normalize(vector);
    }

    @Override
    public String model() {
        return model;
    }

    @Override
    public int dimensions() {
        return DEFAULT_DIMENSIONS;
    }
}
