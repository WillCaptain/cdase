package com.cdase.hub.apipool;

import com.cdase.hub.http.JsonUtil;
import com.sun.net.httpserver.HttpExchange;
import com.sun.net.httpserver.HttpServer;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

import java.net.InetSocketAddress;
import java.nio.charset.StandardCharsets;
import java.util.List;
import java.util.Map;
import java.util.concurrent.atomic.AtomicReference;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

class HttpKnowledgeBaseProviderTest {

    private HttpServer server;
    private HttpKnowledgeBaseProvider provider;
    private final AtomicReference<String> authorization = new AtomicReference<>();
    private final AtomicReference<Map<String, Object>> published = new AtomicReference<>();

    @BeforeEach
    void setUp() throws Exception {
        server = HttpServer.create(new InetSocketAddress("127.0.0.1", 0), 0);
        server.createContext("/api-pool/health", exchange ->
                respond(exchange, Map.of("ok", true, "provider", "legacy")));
        server.createContext("/api-pool/apis", exchange -> {
            if ("GET".equals(exchange.getRequestMethod())) {
                respond(exchange, Map.of(
                        "ok", true,
                        "api", Map.of(
                                "api_id", "x/y/z",
                                "version", "v1",
                                "status", "DEVELOPING"
                        )
                ));
                return;
            }
            authorization.set(exchange.getRequestHeaders().getFirst("Authorization"));
            published.set(read(exchange));
            respond(exchange, Map.of("ok", true, "api", Map.of("api_id", "x/y/z")));
        });
        server.createContext("/api-pool/search", exchange -> respond(exchange, Map.of(
                "ok", true,
                "results", List.of(Map.of("api_id", "x/y/z", "score", 0.9))
        )));
        server.createContext("/api-pool/transition", exchange -> respond(exchange, Map.of(
                "ok", true,
                "api", Map.of("api_id", "x/y/z", "version", "v1", "status", "RELEASED")
        )));
        server.createContext("/api-pool/graph", exchange -> respond(exchange, Map.of(
                "ok", true,
                "graph", Map.of("modules", List.of(), "apis", List.of(), "relations", List.of())
        )));
        server.start();
        provider = new HttpKnowledgeBaseProvider(
                "http://127.0.0.1:" + server.getAddress().getPort(),
                "legacy-token"
        );
    }

    @AfterEach
    void tearDown() {
        server.stop(0);
    }

    @Test
    void forwardsStructuredRecordsVectorsAndAuthorizationToLegacyHttpBackend() throws Exception {
        ApiDefinition definition = ApiDefinition.fromMap(Map.ofEntries(
                Map.entry("api_id", "x/y/z"),
                Map.entry("system", "x"),
                Map.entry("module", "y"),
                Map.entry("name", "z"),
                Map.entry("kind", "METHOD"),
                Map.entry("version", "v1"),
                Map.entry("status", "DEVELOPING"),
                Map.entry("capability", "Do z"),
                Map.entry("signature", "z()"),
                Map.entry("source", Map.of(
                        "repo", "github.com/acme/x",
                        "path", "cdase/api/modules/y.api.md",
                        "commit", "abc123",
                        "owner", "x-team"
                ))
        ));

        Map<String, Object> result = provider.upsert(
                definition,
                new float[]{0.5f, 0.5f},
                "test-model",
                "hash",
                true
        );
        assertEquals("x/y/z", result.get("api_id"));
        assertEquals("Bearer legacy-token", authorization.get());
        assertEquals("test-model", published.get().get("embedding_model"));
        assertEquals(List.of(0.5, 0.5), published.get().get("embedding"));

        List<Map<String, Object>> results = provider.search(
                "do z",
                new float[]{0.5f, 0.5f},
                Map.of(),
                10
        );
        assertEquals("x/y/z", results.get(0).get("api_id"));
        assertEquals("x/y/z", provider.get("x/y/z", "v1").get("api_id"));
        assertEquals(
                "RELEASED",
                provider.transition(
                        "x/y/z",
                        "v1",
                        ApiStatus.RELEASED,
                        "will",
                        null,
                        null
                ).get("status")
        );
        assertTrue(provider.graph("x").containsKey("modules"));
        assertEquals("legacy", provider.health().get("provider"));
    }

    private Map<String, Object> read(HttpExchange exchange) throws java.io.IOException {
        return JsonUtil.parseMap(new String(
                exchange.getRequestBody().readAllBytes(),
                StandardCharsets.UTF_8
        ));
    }

    private void respond(HttpExchange exchange, Map<String, Object> body) throws java.io.IOException {
        byte[] response = JsonUtil.toBytes(body);
        exchange.getResponseHeaders().set("Content-Type", "application/json");
        exchange.sendResponseHeaders(200, response.length);
        exchange.getResponseBody().write(response);
        exchange.close();
    }
}
