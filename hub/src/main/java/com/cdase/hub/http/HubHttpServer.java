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

            if ("GET".equals(method) && ("/".equals(path) || path.isEmpty())) {
                respondRoot(exchange);
                return;
            }
            if ("GET".equals(method) && "/health".equals(path)) {
                respond(exchange, 200, Map.of("ok", true, "service", "cdase-hub", "time", epochNow()));
                return;
            }
            if ("GET".equals(method) && "/version".equals(path)) {
                respond(exchange, 200, Map.of(
                        "ok", true,
                        "service", "cdase-hub",
                        "version", hubVersion(),
                        "time", epochNow()
                ));
                return;
            }
            if ("GET".equals(method) && "/users".equals(path)) {
                String repoId = query.get("repo_id");
                Map<String, Object> payload = new LinkedHashMap<>();
                payload.put("users", store.listUsers(repoId));
                if (repoId != null && !repoId.isBlank()) {
                    payload.put("repo_id", repoId);
                }
                respond(exchange, 200, payload);
                return;
            }
            if ("GET".equals(method) && "/messages".equals(path)) {
                String userUuid = query.get("uuid");
                if (userUuid == null || userUuid.isBlank()) {
                    respond(exchange, 400, Map.of("error", "query param 'uuid' is required"));
                    return;
                }
                List<String> trust = parseTrust(query.get("trust"));
                boolean includeRead = "1".equals(query.get("all")) || "true".equalsIgnoreCase(query.get("all"));
                boolean allSenders = "all".equalsIgnoreCase(query.get("trust"))
                        || "*".equals(query.get("trust"));
                List<Map<String, Object>> messages = allSenders
                        ? store.getAllMessages(userUuid, includeRead)
                        : store.getMessages(userUuid, trust, includeRead);
                if (!allSenders && trust.isEmpty()) {
                    respond(exchange, 400, Map.of(
                            "error", "query param 'trust' is required (roster UUIDs, or 'all' for every sender)"));
                    return;
                }
                respond(exchange, 200, Map.of("messages", messages));
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
                    String repoId = str(body.get("repo_id"));
                    store.login(userUuid, str(body.get("name")), str(body.get("machine_id")), repoId, extra);
                    List<String> trust = parseTrust(str(body.get("trust")));
                    Map<String, Object> ok = new LinkedHashMap<>();
                    ok.put("ok", true);
                    ok.put("uuid", userUuid);
                    ok.put("user", str(body.get("name")));
                    ok.put("unread", store.countUnread(userUuid, trust));
                    if (repoId != null && !repoId.isBlank()) {
                        ok.put("repo_id", repoId);
                    }
                    respond(exchange, 200, ok);
                }
                case "/ping" -> {
                    if (!require(exchange, body, "uuid", "machine_id")) {
                        return;
                    }
                    String userUuid = str(body.get("uuid"));
                    String repoId = str(body.get("repo_id"));
                    if (store.ping(userUuid, str(body.get("machine_id")), repoId) == null) {
                        respond(exchange, 404, Map.of("error", "unknown user, login first"));
                        return;
                    }
                    List<String> trust = parseTrust(str(body.get("trust")));
                    Map<String, Object> ok = new LinkedHashMap<>();
                    ok.put("ok", true);
                    ok.put("unread", store.countUnread(userUuid, trust));
                    if (repoId != null && !repoId.isBlank()) {
                        ok.put("repo_id", repoId);
                    }
                    respond(exchange, 200, ok);
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

        /** Public landing for https://12th.ai/cdase/ — proves the hub is online. */
        private void respondRoot(HttpExchange exchange) throws IOException {
            String accept = exchange.getRequestHeaders().getFirst("Accept");
            boolean wantHtml = accept != null && accept.toLowerCase().contains("text/html");
            if (wantHtml) {
                String html = """
                        <!doctype html>
                        <html lang="en">
                        <head>
                          <meta charset="utf-8"/>
                          <meta name="viewport" content="width=device-width, initial-scale=1"/>
                          <title>CDASE Hub</title>
                          <style>
                            :root { color-scheme: light dark; font-family: ui-sans-serif, system-ui, sans-serif; }
                            body { margin: 0; min-height: 100vh; display: grid; place-items: center;
                                   background: #0f1419; color: #e7ecf3; }
                            main { max-width: 36rem; padding: 2rem; }
                            h1 { font-size: 1.75rem; margin: 0 0 .5rem; letter-spacing: -.02em; }
                            .ok { color: #3dd68c; font-weight: 600; }
                            p { line-height: 1.5; color: #a8b3c2; }
                            code { color: #9ecbff; }
                            ul { padding-left: 1.2rem; color: #c5ced9; }
                            a { color: #7eb6ff; }
                          </style>
                        </head>
                        <body>
                          <main>
                            <h1>CDASE Hub</h1>
                            <p class="ok">Online</p>
                            <p>Collaboration API for Context-Driven AI Software Engineering.</p>
                            <ul>
                              <li><a href="health"><code>GET /health</code></a></li>
                              <li><a href="version"><code>GET /version</code></a></li>
                              <li><code>GET /users</code>, <code>GET /messages</code>, <code>POST /login</code></li>
                            </ul>
                            <p>Public base: <code>https://12th.ai/cdase</code></p>
                          </main>
                        </body>
                        </html>
                        """;
                JsonResponder.respondRaw(exchange, 200, html.getBytes(StandardCharsets.UTF_8),
                        "text/html; charset=utf-8");
                return;
            }
            Map<String, Object> payload = new LinkedHashMap<>();
            payload.put("ok", true);
            payload.put("service", "cdase-hub");
            payload.put("status", "online");
            payload.put("version", hubVersion());
            payload.put("time", epochNow());
            payload.put("public_base", "https://12th.ai/cdase");
            payload.put("endpoints", Map.of(
                    "health", "GET /health",
                    "version", "GET /version",
                    "users", "GET /users?repo_id=",
                    "messages", "GET /messages?uuid=&trust=",
                    "login", "POST /login",
                    "ping", "POST /ping",
                    "send", "POST /messages",
                    "ack", "POST /messages/ack",
                    "kb", "GET|POST /kb"
            ));
            respond(exchange, 200, payload);
        }

        private String hubVersion() {
            return "1.0.0";
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
