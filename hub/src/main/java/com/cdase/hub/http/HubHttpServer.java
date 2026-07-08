package com.cdase.hub.http;

import com.cdase.hub.store.HubStore;
import com.sun.net.httpserver.HttpExchange;
import com.sun.net.httpserver.HttpHandler;
import com.sun.net.httpserver.HttpServer;

import java.io.IOException;
import java.io.InputStream;
import java.net.InetSocketAddress;
import java.nio.charset.StandardCharsets;
import java.time.Instant;
import java.util.Arrays;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.concurrent.Executors;
import java.util.stream.Collectors;

public final class HubHttpServer {

    private final String host;
    private final int port;
    private final HubStore store;
    private HttpServer server;

    public HubHttpServer(String host, int port, HubStore store) {
        this.host = host;
        this.port = port;
        this.store = store;
    }

    public void start() throws IOException, InterruptedException {
        server = HttpServer.create(new InetSocketAddress(host, port), 0);
        server.createContext("/", new Router());
        server.setExecutor(Executors.newCachedThreadPool());
        server.start();
        Thread.currentThread().join();
    }

    private final class Router implements HttpHandler {
        @Override
        public void handle(HttpExchange exchange) throws IOException {
            try {
                route(exchange);
            } catch (Exception e) {
                respond(exchange, 500, Map.of("error", e.getMessage() == null ? "internal error" : e.getMessage()));
            }
        }

        private void route(HttpExchange exchange) throws Exception {
            String method = exchange.getRequestMethod();
            String path = exchange.getRequestURI().getPath();
            Map<String, String> query = parseQuery(exchange.getRequestURI().getRawQuery());

            if ("GET".equals(method) && "/health".equals(path)) {
                respond(exchange, 200, Map.of("ok", true, "service", "cdase-hub", "time", epochNow()));
                return;
            }
            if ("GET".equals(method) && "/users".equals(path)) {
                respond(exchange, 200, Map.of("users", store.listUsers()));
                return;
            }
            if ("GET".equals(method) && "/messages".equals(path)) {
                String userUuid = query.get("uuid");
                if (userUuid == null || userUuid.isBlank()) {
                    respond(exchange, 400, Map.of("error", "query param 'uuid' is required"));
                    return;
                }
                List<String> trust = parseTrust(query.get("trust"));
                if (trust.isEmpty()) {
                    respond(exchange, 400, Map.of("error", "query param 'trust' is required (comma-separated UUIDs from repo roster)"));
                    return;
                }
                boolean includeRead = "1".equals(query.get("all")) || "true".equalsIgnoreCase(query.get("all"));
                respond(exchange, 200, Map.of("messages", store.getMessages(userUuid, trust, includeRead)));
                return;
            }
            if ("GET".equals(method) && "/kb".equals(path)) {
                String q = query.getOrDefault("query", "");
                respond(exchange, 200, Map.of("results", store.kbSearch(q)));
                return;
            }

            if ("POST".equals(method)) {
                Map<String, Object> body = readJson(exchange);
                if (body == null) {
                    respond(exchange, 400, Map.of("error", "invalid JSON body"));
                    return;
                }
                handlePost(exchange, path, body);
                return;
            }

            respond(exchange, 404, Map.of("error", "not found"));
        }

        private void handlePost(HttpExchange exchange, String path, Map<String, Object> body) throws Exception {
            switch (path) {
                case "/login" -> {
                    if (!require(exchange, body, "uuid", "name", "machine_id")) {
                        return;
                    }
                    Map<String, String> extra = new LinkedHashMap<>();
                    putIfPresent(body, extra, "role");
                    putIfPresent(body, extra, "team");
                    putIfPresent(body, extra, "organization");
                    String userUuid = str(body.get("uuid"));
                    store.login(userUuid, str(body.get("name")), str(body.get("machine_id")), extra);
                    List<String> trust = parseTrust(str(body.get("trust")));
                    respond(exchange, 200, Map.of(
                            "ok", true,
                            "uuid", userUuid,
                            "user", str(body.get("name")),
                            "unread", store.countUnread(userUuid, trust)
                    ));
                }
                case "/ping" -> {
                    if (!require(exchange, body, "uuid", "machine_id")) {
                        return;
                    }
                    String userUuid = str(body.get("uuid"));
                    if (store.ping(userUuid, str(body.get("machine_id"))) == null) {
                        respond(exchange, 404, Map.of("error", "unknown user, login first"));
                        return;
                    }
                    List<String> trust = parseTrust(str(body.get("trust")));
                    respond(exchange, 200, Map.of("ok", true, "unread", store.countUnread(userUuid, trust)));
                }
                case "/messages" -> {
                    if (!require(exchange, body, "from_uuid", "to_uuid", "body")) {
                        return;
                    }
                    Map<String, Object> msg = store.sendMessage(
                            str(body.get("from_uuid")),
                            str(body.get("to_uuid")),
                            str(body.get("from")),
                            str(body.get("to")),
                            str(body.get("body")),
                            strOr(body.get("type"), "message"),
                            str(body.get("subject")),
                            strOr(body.get("from_actor"), "human"),
                            str(body.get("intent")),
                            str(body.get("thread_id"))
                    );
                    respond(exchange, 200, Map.of("ok", true, "message", msg));
                }
                case "/messages/ack" -> {
                    if (!require(exchange, body, "uuid", "ids")) {
                        return;
                    }
                    @SuppressWarnings("unchecked")
                    List<String> ids = (List<String>) body.get("ids");
                    int count = store.ackMessages(str(body.get("uuid")), ids);
                    respond(exchange, 200, Map.of("ok", true, "acknowledged", count));
                }
                case "/kb" -> {
                    if (!require(exchange, body, "key", "content")) {
                        return;
                    }
                    @SuppressWarnings("unchecked")
                    List<String> tags = body.get("tags") instanceof List<?> list
                            ? list.stream().map(String::valueOf).toList()
                            : List.of();
                    Map<String, Object> entry = store.kbSave(
                            str(body.get("key")),
                            str(body.get("content")),
                            tags,
                            str(body.get("author"))
                    );
                    respond(exchange, 200, Map.of("ok", true, "entry", Map.of(
                            "key", entry.get("key"),
                            "slug", entry.get("slug")
                    )));
                }
                default -> respond(exchange, 404, Map.of("error", "not found"));
            }
        }

        private List<String> parseTrust(String raw) {
            if (raw == null || raw.isBlank()) {
                return List.of();
            }
            return Arrays.stream(raw.split(","))
                    .map(String::trim)
                    .filter(s -> !s.isBlank())
                    .collect(Collectors.toList());
        }

        private boolean require(HttpExchange exchange, Map<String, Object> body, String... fields) throws IOException {
            List<String> missing = Arrays.stream(fields)
                    .filter(f -> body.get(f) == null || String.valueOf(body.get(f)).isBlank())
                    .toList();
            if (!missing.isEmpty()) {
                respond(exchange, 400, Map.of("error", "missing fields: " + String.join(", ", missing)));
                return false;
            }
            return true;
        }

        private Map<String, Object> readJson(HttpExchange exchange) throws IOException {
            try (InputStream in = exchange.getRequestBody()) {
                String raw = new String(in.readAllBytes(), StandardCharsets.UTF_8);
                if (raw.isBlank()) {
                    return Map.of();
                }
                return JsonUtil.parseMap(raw);
            } catch (Exception e) {
                return null;
            }
        }

        private void respond(HttpExchange exchange, int code, Map<String, ?> payload) throws IOException {
            JsonResponder.respond(exchange, code, payload);
        }

        private Map<String, String> parseQuery(String raw) {
            Map<String, String> out = new LinkedHashMap<>();
            if (raw == null || raw.isBlank()) {
                return out;
            }
            for (String part : raw.split("&")) {
                String[] kv = part.split("=", 2);
                if (kv.length == 2) {
                    out.put(kv[0], java.net.URLDecoder.decode(kv[1], StandardCharsets.UTF_8));
                }
            }
            return out;
        }

        private void putIfPresent(Map<String, Object> body, Map<String, String> extra, String key) {
            Object value = body.get(key);
            if (value != null && !String.valueOf(value).isBlank()) {
                extra.put(key, String.valueOf(value));
            }
        }

        private String str(Object value) {
            return value == null ? null : String.valueOf(value);
        }

        private String strOr(Object value, String fallback) {
            String s = str(value);
            return s == null || s.isBlank() ? fallback : s;
        }

        private double epochNow() {
            Instant now = Instant.now();
            return now.getEpochSecond() + now.getNano() / 1_000_000_000.0;
        }
    }
}
