package com.cdase.hub.apipool;

import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.condition.EnabledIfEnvironmentVariable;

import java.util.List;
import java.util.Map;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;

/**
 * Opt-in production-dialect test. CI/developers can point it at a disposable
 * PostgreSQL database with pgvector installed.
 */
@EnabledIfEnvironmentVariable(named = "CDASE_TEST_POSTGRES_URL", matches = ".+")
class PostgresApiPoolIntegrationTest {

    @Test
    void postgresPgvectorProviderPublishesAndSearches() throws Exception {
        try (JdbcKnowledgeBaseProvider provider = JdbcKnowledgeBaseProvider.connect(
                System.getenv("CDASE_TEST_POSTGRES_URL"),
                System.getenv().getOrDefault("CDASE_TEST_POSTGRES_USER", ""),
                System.getenv().getOrDefault("CDASE_TEST_POSTGRES_PASSWORD", "")
        )) {
            String unique = Long.toString(System.nanoTime());
            ApiDefinition definition = ApiDefinition.fromMap(Map.ofEntries(
                    Map.entry("api_id", "test/api/ping-" + unique),
                    Map.entry("system", "test"),
                    Map.entry("module", "api"),
                    Map.entry("name", "ping"),
                    Map.entry("kind", "METHOD"),
                    Map.entry("version", "v1"),
                    Map.entry("status", "DEVELOPING"),
                    Map.entry("capability", "Check whether a test service is available"),
                    Map.entry("signature", "ping() -> boolean"),
                    Map.entry("source", Map.of(
                            "repo", "test/repository",
                            "path", "cdase/api/modules/test.api.md",
                            "commit", unique,
                            "owner", "test"
                    ))
            ));
            provider.upsert(
                    definition,
                    null,
                    "disabled",
                    definition.contentHash(),
                    true
            );

            List<Map<String, Object>> results = provider.search(
                    "check test service available",
                    null,
                    Map.of("system", "test"),
                    20
            );
            assertFalse(results.isEmpty());
            assertEquals(definition.apiId(), results.get(0).get("api_id"));

            float[] vectorA = new float[384];
            float[] vectorB = new float[384];
            vectorA[0] = 1;
            vectorB[1] = 1;
            ApiDefinition semanticA = semanticDefinition(
                    "test/semantic/candidate-a-" + unique,
                    "candidateA",
                    unique
            );
            ApiDefinition semanticB = semanticDefinition(
                    "test/semantic/candidate-b-" + unique,
                    "candidateB",
                    unique
            );
            provider.upsert(
                    semanticA,
                    vectorA,
                    HttpBgeEmbeddingProvider.DEFAULT_MODEL,
                    semanticA.contentHash(),
                    true
            );
            provider.upsert(
                    semanticB,
                    vectorB,
                    HttpBgeEmbeddingProvider.DEFAULT_MODEL,
                    semanticB.contentHash(),
                    true
            );
            List<Map<String, Object>> semanticResults = provider.search(
                    "needle",
                    vectorA,
                    Map.of("system", "test", "module", "semantic"),
                    20
            );
            assertEquals(semanticA.apiId(), semanticResults.get(0).get("api_id"));
            assertEquals(
                    1.0,
                    ((Number) semanticResults.get(0).get("semantic_score")).doubleValue(),
                    0.0001
            );
        }
    }

    private static ApiDefinition semanticDefinition(
            String apiId,
            String name,
            String revision
    ) {
        return ApiDefinition.fromMap(Map.ofEntries(
                Map.entry("api_id", apiId),
                Map.entry("system", "test"),
                Map.entry("module", "semantic"),
                Map.entry("name", name),
                Map.entry("kind", "METHOD"),
                Map.entry("version", "v1"),
                Map.entry("status", "DEVELOPING"),
                Map.entry("capability", "Unrelated synthetic capability"),
                Map.entry("signature", name + "() -> boolean"),
                Map.entry("source", Map.of(
                        "repo", "test/repository",
                        "path", "cdase/api/modules/semantic.api.md",
                        "commit", revision,
                        "owner", "test"
                ))
        ));
    }
}
