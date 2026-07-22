package com.cdase.hub.apipool;

import com.cdase.hub.http.JsonUtil;
import com.sun.net.httpserver.HttpServer;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

import java.net.InetSocketAddress;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.concurrent.atomic.AtomicReference;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

class HttpBgeEmbeddingProviderTest {

    private HttpServer server;
    private String endpoint;
    private final AtomicReference<String> authorization = new AtomicReference<>();
    private final AtomicReference<Map<String, Object>> request = new AtomicReference<>();

    @BeforeEach
    void setUp() throws Exception {
        server = HttpServer.create(new InetSocketAddress("127.0.0.1", 0), 0);
        endpoint = "http://127.0.0.1:" + server.getAddress().getPort() + "/v1/embeddings";
        server.start();
    }

    @AfterEach
    void tearDown() {
        server.stop(0);
    }

    @Test
    void callsOpenAiCompatibleBgeEndpointAndNormalizesVector() throws Exception {
        server.createContext("/v1/embeddings", exchange -> {
            authorization.set(exchange.getRequestHeaders().getFirst("Authorization"));
            request.set(JsonUtil.parseMap(new String(
                    exchange.getRequestBody().readAllBytes(),
                    StandardCharsets.UTF_8
            )));
            List<Float> embedding = new ArrayList<>();
            for (int i = 0; i < 384; i++) {
                embedding.add(i == 0 ? 3f : i == 1 ? 4f : 0f);
            }
            byte[] response = JsonUtil.toBytes(Map.of(
                    "data", List.of(Map.of("embedding", embedding))
            ));
            exchange.sendResponseHeaders(200, response.length);
            exchange.getResponseBody().write(response);
            exchange.close();
        });

        HttpBgeEmbeddingProvider provider = new HttpBgeEmbeddingProvider(
                endpoint,
                null,
                "secret"
        );
        float[] vector = provider.embed("create an invoice");

        assertEquals(384, vector.length);
        assertEquals(0.6f, vector[0], 0.0001);
        assertEquals(0.8f, vector[1], 0.0001);
        assertEquals("Bearer secret", authorization.get());
        assertEquals(HttpBgeEmbeddingProvider.DEFAULT_MODEL, request.get().get("model"));
        assertEquals("create an invoice", request.get().get("input"));
    }

    @Test
    void rejectsUnexpectedEmbeddingDimensions() {
        server.createContext("/v1/embeddings", exchange -> {
            byte[] response = JsonUtil.toBytes(Map.of(
                    "data", List.of(Map.of("embedding", List.of(1.0, 2.0)))
            ));
            exchange.sendResponseHeaders(200, response.length);
            exchange.getResponseBody().write(response);
            exchange.close();
        });
        HttpBgeEmbeddingProvider provider = new HttpBgeEmbeddingProvider(endpoint, null, null);
        IllegalStateException error = assertThrows(
                IllegalStateException.class,
                () -> provider.embed("query")
        );
        assertTrue(error.getMessage().contains("expected 384"));
    }
}
