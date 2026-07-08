package com.cdase.hub.http;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;

import java.util.Map;

public final class JsonUtil {

    private static final ObjectMapper MAPPER = new ObjectMapper();

    private JsonUtil() {
    }

    public static byte[] toBytes(Map<String, ?> payload) {
        try {
            return MAPPER.writeValueAsBytes(payload);
        } catch (JsonProcessingException e) {
            throw new IllegalStateException("Failed to serialize JSON", e);
        }
    }

    @SuppressWarnings("unchecked")
    public static Map<String, Object> parseMap(String json) throws JsonProcessingException {
        return MAPPER.readValue(json, Map.class);
    }
}
