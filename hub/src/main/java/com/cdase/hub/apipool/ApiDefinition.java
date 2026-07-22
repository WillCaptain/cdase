package com.cdase.hub.apipool;

import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

public record ApiDefinition(
        String apiId,
        String system,
        String module,
        String name,
        String kind,
        String version,
        ApiStatus status,
        String capability,
        List<String> useWhen,
        List<String> doNotUseWhen,
        String signature,
        List<Parameter> inputs,
        List<Parameter> outputs,
        List<ApiError> errors,
        List<String> sideEffects,
        String auth,
        String idempotency,
        String origin,
        String discoveryConfidence,
        String scanId,
        String approvalRef,
        List<DiscoveryEvidence> discoveryEvidence,
        Source source,
        List<Relation> relations
) {
    public ApiDefinition {
        apiId = required(apiId, "api_id");
        system = required(system, "system");
        module = required(module, "module");
        name = required(name, "name");
        kind = required(kind, "kind");
        version = required(version, "version");
        status = status == null ? ApiStatus.DEVELOPING : status;
        capability = required(capability, "capability");
        signature = required(signature, "signature");
        useWhen = copy(useWhen);
        doNotUseWhen = copy(doNotUseWhen);
        inputs = copy(inputs);
        outputs = copy(outputs);
        errors = copy(errors);
        sideEffects = copy(sideEffects);
        relations = copy(relations);
        discoveryEvidence = copy(discoveryEvidence);
        origin = origin == null || origin.isBlank() ? "NATIVE" : origin.trim().toUpperCase();
        if ("LEGACY_IMPORT".equals(origin)) {
            if (!"HIGH".equals(discoveryConfidence)
                    && !"MEDIUM".equals(discoveryConfidence)
                    && !"LOW".equals(discoveryConfidence)) {
                throw new IllegalArgumentException(
                        "legacy import requires discovery_confidence HIGH, MEDIUM, or LOW"
                );
            }
            scanId = required(scanId, "scan_id");
            approvalRef = required(approvalRef, "approval_ref");
            if (discoveryEvidence.isEmpty()) {
                throw new IllegalArgumentException(
                        "legacy import requires discovery_evidence"
                );
            }
        }
        if (source == null) {
            throw new IllegalArgumentException("missing field: source");
        }
        source = new Source(
                required(source.repo(), "source.repo"),
                required(source.path(), "source.path"),
                required(source.commit(), "source.commit"),
                required(source.owner(), "source.owner")
        );
    }

    public static ApiDefinition fromMap(Map<String, Object> body) {
        return new ApiDefinition(
                text(body.get("api_id")),
                text(body.get("system")),
                text(body.get("module")),
                text(body.get("name")),
                text(body.get("kind")),
                text(body.get("version")),
                ApiStatus.parse(body.get("status")),
                text(body.get("capability")),
                strings(body.get("use_when")),
                strings(body.get("do_not_use_when")),
                text(body.get("signature")),
                parameters(body.get("inputs")),
                parameters(body.get("outputs")),
                errors(body.get("errors")),
                strings(body.get("side_effects")),
                text(body.get("auth")),
                text(body.get("idempotency")),
                text(body.get("origin")),
                upper(body.get("discovery_confidence")),
                text(body.get("scan_id")),
                text(body.get("approval_ref")),
                discoveryEvidence(body.get("discovery_evidence")),
                Source.from(body.get("source")),
                relations(body.get("relations"))
        );
    }

    public String canonicalEmbeddingText() {
        List<String> lines = new ArrayList<>();
        lines.add("System: " + system);
        lines.add("Module: " + module);
        lines.add("API: " + name);
        lines.add("Kind: " + kind);
        lines.add("Capability: " + capability);
        lines.add("Signature: " + signature);
        addLines(lines, "Use when", useWhen);
        addLines(lines, "Do not use when", doNotUseWhen);
        inputs.forEach(p -> lines.add("Input: " + p.name() + " " + nullToEmpty(p.type())
                + " " + nullToEmpty(p.description())));
        outputs.forEach(p -> lines.add("Output: " + p.name() + " " + nullToEmpty(p.type())
                + " " + nullToEmpty(p.description())));
        errors.forEach(e -> lines.add("Error: " + e.code() + " " + nullToEmpty(e.description())));
        addLines(lines, "Side effect", sideEffects);
        if (auth != null) {
            lines.add("Authorization: " + auth);
        }
        if (idempotency != null) {
            lines.add("Idempotency: " + idempotency);
        }
        return String.join("\n", lines);
    }

    public String contentHash() {
        try {
            byte[] digest = MessageDigest.getInstance("SHA-256")
                    .digest(canonicalEmbeddingText().getBytes(StandardCharsets.UTF_8));
            StringBuilder out = new StringBuilder();
            for (byte b : digest) {
                out.append(String.format("%02x", b));
            }
            return out.toString();
        } catch (NoSuchAlgorithmException e) {
            throw new IllegalStateException("SHA-256 unavailable", e);
        }
    }

    public Map<String, Object> toMap() {
        Map<String, Object> out = new LinkedHashMap<>();
        out.put("api_id", apiId);
        out.put("system", system);
        out.put("module", module);
        out.put("name", name);
        out.put("kind", kind);
        out.put("version", version);
        out.put("status", status.name());
        out.put("capability", capability);
        out.put("use_when", useWhen);
        out.put("do_not_use_when", doNotUseWhen);
        out.put("signature", signature);
        out.put("inputs", inputs.stream().map(Parameter::toMap).toList());
        out.put("outputs", outputs.stream().map(Parameter::toMap).toList());
        out.put("errors", errors.stream().map(ApiError::toMap).toList());
        out.put("side_effects", sideEffects);
        out.put("auth", auth);
        out.put("idempotency", idempotency);
        out.put("origin", origin);
        out.put("discovery_confidence", discoveryConfidence);
        out.put("scan_id", scanId);
        out.put("approval_ref", approvalRef);
        out.put(
                "discovery_evidence",
                discoveryEvidence.stream().map(DiscoveryEvidence::toMap).toList()
        );
        out.put("source", source.toMap());
        out.put("relations", relations.stream().map(Relation::toMap).toList());
        return out;
    }

    public record Parameter(String name, String type, String description, boolean required) {
        static Parameter from(Map<?, ?> map) {
            return new Parameter(
                    ApiDefinition.required(text(map.get("name")), "parameter.name"),
                    text(map.get("type")),
                    text(map.get("description")),
                    Boolean.parseBoolean(String.valueOf(
                            map.get("required") == null ? false : map.get("required")
                    ))
            );
        }

        Map<String, Object> toMap() {
            return Map.of(
                    "name", name,
                    "type", nullToEmpty(type),
                    "description", nullToEmpty(description),
                    "required", required
            );
        }
    }

    public record ApiError(String code, String description) {
        static ApiError from(Map<?, ?> map) {
            return new ApiError(required(text(map.get("code")), "error.code"), text(map.get("description")));
        }

        Map<String, Object> toMap() {
            return Map.of("code", code, "description", nullToEmpty(description));
        }
    }

    public record Relation(String type, String targetApiId, String targetVersion) {
        static Relation from(Map<?, ?> map) {
            return new Relation(
                    required(text(map.get("type")), "relation.type"),
                    required(text(map.get("target_api_id")), "relation.target_api_id"),
                    text(map.get("target_version"))
            );
        }

        Map<String, Object> toMap() {
            Map<String, Object> out = new LinkedHashMap<>();
            out.put("type", type);
            out.put("target_api_id", targetApiId);
            out.put("target_version", targetVersion);
            return out;
        }
    }

    public record DiscoveryEvidence(
            String kind,
            String path,
            Integer line,
            String symbol,
            String detail
    ) {
        static DiscoveryEvidence from(Map<?, ?> map) {
            String kind = required(text(map.get("kind")), "discovery_evidence.kind");
            String path = required(text(map.get("path")), "discovery_evidence.path");
            Integer line = null;
            if (map.get("line") instanceof Number number) {
                line = number.intValue();
            }
            return new DiscoveryEvidence(
                    kind,
                    path,
                    line,
                    text(map.get("symbol")),
                    text(map.get("detail"))
            );
        }

        Map<String, Object> toMap() {
            Map<String, Object> out = new LinkedHashMap<>();
            out.put("kind", kind);
            out.put("path", path);
            out.put("line", line);
            out.put("symbol", symbol);
            out.put("detail", detail);
            return out;
        }
    }

    public record Source(String repo, String path, String commit, String owner) {
        static Source from(Object value) {
            if (!(value instanceof Map<?, ?> map)) {
                return new Source(null, null, null, null);
            }
            return new Source(
                    text(map.get("repo")),
                    text(map.get("path")),
                    text(map.get("commit")),
                    text(map.get("owner"))
            );
        }

        Map<String, Object> toMap() {
            Map<String, Object> out = new LinkedHashMap<>();
            out.put("repo", repo);
            out.put("path", path);
            out.put("commit", commit);
            out.put("owner", owner);
            return out;
        }
    }

    private static String required(String value, String field) {
        if (value == null || value.isBlank()) {
            throw new IllegalArgumentException("missing field: " + field);
        }
        return value.trim();
    }

    private static String text(Object value) {
        if (value == null) {
            return null;
        }
        String text = String.valueOf(value).trim();
        return text.isEmpty() ? null : text;
    }

    private static List<String> strings(Object value) {
        if (!(value instanceof List<?> list)) {
            return List.of();
        }
        return list.stream().map(ApiDefinition::text).filter(v -> v != null).toList();
    }

    private static List<Parameter> parameters(Object value) {
        if (!(value instanceof List<?> list)) {
            return List.of();
        }
        return list.stream()
                .filter(Map.class::isInstance)
                .map(v -> Parameter.from((Map<?, ?>) v))
                .toList();
    }

    private static List<ApiError> errors(Object value) {
        if (!(value instanceof List<?> list)) {
            return List.of();
        }
        return list.stream()
                .filter(Map.class::isInstance)
                .map(v -> ApiError.from((Map<?, ?>) v))
                .toList();
    }

    private static List<Relation> relations(Object value) {
        if (!(value instanceof List<?> list)) {
            return List.of();
        }
        return list.stream()
                .filter(Map.class::isInstance)
                .map(v -> Relation.from((Map<?, ?>) v))
                .toList();
    }

    private static List<DiscoveryEvidence> discoveryEvidence(Object value) {
        if (!(value instanceof List<?> list)) {
            return List.of();
        }
        return list.stream()
                .filter(Map.class::isInstance)
                .map(v -> DiscoveryEvidence.from((Map<?, ?>) v))
                .toList();
    }

    private static String upper(Object value) {
        String text = text(value);
        return text == null ? null : text.toUpperCase();
    }

    private static <T> List<T> copy(List<T> source) {
        return source == null ? List.of() : List.copyOf(source);
    }

    private static void addLines(List<String> target, String prefix, List<String> values) {
        values.forEach(value -> target.add(prefix + ": " + value));
    }

    private static String nullToEmpty(String value) {
        return value == null ? "" : value;
    }
}
