package com.cdase.hub.apipool;

import com.cdase.hub.db.Database;

import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.util.Locale;
import java.util.Map;

public final class ApiPoolRuntime implements AutoCloseable {

    private final ApiPoolService service;
    private final String providerName;
    private final String writeToken;

    private ApiPoolRuntime(ApiPoolService service, String providerName, String writeToken) {
        this.service = service;
        this.providerName = providerName;
        this.writeToken = writeToken;
    }

    public static ApiPoolRuntime fromEnvironment(Database hubDatabase) throws Exception {
        Map<String, String> env = System.getenv();
        String providerName = value(env, "CDASE_KB_PROVIDER", "embedded")
                .toLowerCase(Locale.ROOT);

        KnowledgeBaseProvider provider = switch (providerName) {
            case "embedded" -> new JdbcKnowledgeBaseProvider(hubDatabase.openConnection(), true);
            case "postgres", "jdbc" -> JdbcKnowledgeBaseProvider.connect(
                    required(env, "CDASE_KB_JDBC_URL"),
                    value(env, "CDASE_KB_JDBC_USER", ""),
                    value(env, "CDASE_KB_JDBC_PASSWORD", "")
            );
            case "http", "legacy-http" -> new HttpKnowledgeBaseProvider(
                    required(env, "CDASE_KB_HTTP_URL"),
                    env.get("CDASE_KB_HTTP_TOKEN")
            );
            default -> throw new IllegalArgumentException(
                    "CDASE_KB_PROVIDER must be embedded, postgres, jdbc, or http"
            );
        };

        String embeddingUrl = env.get("CDASE_EMBEDDING_URL");
        EmbeddingProvider embeddings = embeddingUrl == null || embeddingUrl.isBlank()
                ? new DisabledEmbeddingProvider()
                : new HttpBgeEmbeddingProvider(
                        embeddingUrl,
                        value(env, "CDASE_EMBEDDING_MODEL", HttpBgeEmbeddingProvider.DEFAULT_MODEL),
                        env.get("CDASE_EMBEDDING_TOKEN")
                );
        return new ApiPoolRuntime(
                new ApiPoolService(provider, embeddings),
                providerName,
                env.get("CDASE_KB_WRITE_TOKEN")
        );
    }

    public ApiPoolService service() {
        return service;
    }

    public String providerName() {
        return providerName;
    }

    public boolean writesEnabled() {
        return writeToken != null && !writeToken.isBlank();
    }

    public boolean authorized(String authorizationHeader) {
        if (!writesEnabled()) {
            return false;
        }
        if (authorizationHeader == null) {
            return false;
        }
        return MessageDigest.isEqual(
                ("Bearer " + writeToken).getBytes(StandardCharsets.UTF_8),
                authorizationHeader.getBytes(StandardCharsets.UTF_8)
        );
    }

    @Override
    public void close() throws Exception {
        service.close();
    }

    private static String required(Map<String, String> env, String key) {
        String value = env.get(key);
        if (value == null || value.isBlank()) {
            throw new IllegalArgumentException(key + " is required");
        }
        return value;
    }

    private static String value(Map<String, String> env, String key, String fallback) {
        String value = env.get(key);
        return value == null || value.isBlank() ? fallback : value;
    }
}
