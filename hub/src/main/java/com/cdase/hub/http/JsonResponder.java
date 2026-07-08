package com.cdase.hub.http;

import com.sun.net.httpserver.HttpExchange;

import java.io.IOException;
import java.util.Map;

final class JsonResponder {

    private JsonResponder() {
    }

    static void respond(HttpExchange exchange, int code, Map<String, ?> payload) throws IOException {
        respondRaw(exchange, code, JsonUtil.toBytes(payload), "application/json; charset=utf-8");
    }

    static void respondRaw(HttpExchange exchange, int code, byte[] bytes, String contentType) throws IOException {
        exchange.getResponseHeaders().set("Content-Type", contentType);
        exchange.getResponseHeaders().set("Access-Control-Allow-Origin", "*");
        exchange.sendResponseHeaders(code, bytes.length);
        exchange.getResponseBody().write(bytes);
        exchange.close();
    }
}
