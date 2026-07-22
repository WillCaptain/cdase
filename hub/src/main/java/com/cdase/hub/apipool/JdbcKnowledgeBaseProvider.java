package com.cdase.hub.apipool;

import java.io.IOException;
import java.io.InputStream;
import java.nio.charset.StandardCharsets;
import java.sql.Connection;
import java.sql.DriverManager;
import java.sql.PreparedStatement;
import java.sql.ResultSet;
import java.sql.SQLException;
import java.sql.Statement;
import java.sql.Timestamp;
import java.time.Instant;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.LinkedHashMap;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Set;

public final class JdbcKnowledgeBaseProvider implements KnowledgeBaseProvider {

    private static final Set<ApiStatus> DEFAULT_SEARCH_STATUSES = Set.of(
            ApiStatus.DEVELOPING,
            ApiStatus.RELEASED,
            ApiStatus.SUPERSEDED,
            ApiStatus.DEPRECATED
    );

    private final Connection connection;
    private final boolean ownsConnection;
    private final boolean postgres;

    public JdbcKnowledgeBaseProvider(Connection connection) throws SQLException {
        this(connection, false);
    }

    public JdbcKnowledgeBaseProvider(Connection connection, boolean ownsConnection) throws SQLException {
        this.connection = connection;
        this.ownsConnection = ownsConnection;
        this.postgres = connection.getMetaData().getDatabaseProductName()
                .toLowerCase(Locale.ROOT).contains("postgresql");
    }

    public static JdbcKnowledgeBaseProvider connect(
            String url,
            String user,
            String password
    ) throws SQLException, IOException {
        Connection connection = DriverManager.getConnection(url, user, password);
        JdbcKnowledgeBaseProvider provider = new JdbcKnowledgeBaseProvider(connection, true);
        if (provider.postgres) {
            provider.initializePostgresSchema();
        }
        return provider;
    }

    @Override
    public synchronized Map<String, Object> upsert(
            ApiDefinition definition,
            float[] embedding,
            String embeddingModel,
            String contentHash,
            boolean replaceEmbedding
    ) throws Exception {
        boolean previousAutoCommit = connection.getAutoCommit();
        connection.setAutoCommit(false);
        try {
            ExistingOperation operation = existingOperation(definition.apiId());
            if (operation != null
                    && operation.sourceRepo() != null
                    && definition.source().repo() != null
                    && !operation.sourceRepo().equals(definition.source().repo())) {
                throw new IllegalStateException(
                        "API id is owned by a different source repository: " + operation.sourceRepo()
                );
            }
            ExistingVersion existing = existingVersion(definition.apiId(), definition.version());
            if (existing != null
                    && existing.status() != ApiStatus.DEVELOPING
                    && !existing.contentHash().equals(contentHash)) {
                throw new IllegalStateException(
                        "released API contracts are immutable; publish a new version"
                );
            }

            Instant now = Instant.now();
            upsertSystem(definition.system(), now);
            upsertModule(definition.system(), definition.module(), now);
            upsertOperation(definition, now);
            upsertVersion(
                    definition,
                    embedding,
                    embeddingModel,
                    contentHash,
                    now,
                    existing == null,
                    replaceEmbedding
            );
            replaceChildren(definition);
            if (existing == null) {
                insertLifecycleEvent(
                        definition.apiId(),
                        definition.version(),
                        null,
                        definition.status(),
                        definition.source().owner(),
                        "API version published",
                        null,
                        now
                );
            } else if (existing.status() != definition.status()) {
                if (!existing.status().canTransitionTo(definition.status())) {
                    throw new IllegalStateException(
                            "invalid lifecycle transition: " + existing.status() + " -> " + definition.status()
                    );
                }
                insertLifecycleEvent(
                        definition.apiId(),
                        definition.version(),
                        existing.status(),
                        definition.status(),
                        definition.source().owner(),
                        "API version updated",
                        null,
                        now
                );
            }
            connection.commit();
            return get(definition.apiId(), definition.version());
        } catch (Exception e) {
            connection.rollback();
            throw e;
        } finally {
            connection.setAutoCommit(previousAutoCommit);
        }
    }

    @Override
    public synchronized Map<String, Object> get(String apiId, String version) throws Exception {
        String sql = """
                SELECT o.*, v.version, v.lifecycle_status, v.source_commit,
                       COALESCE(v.capability, o.capability) AS version_capability,
                       COALESCE(v.signature, o.signature) AS version_signature,
                       COALESCE(v.auth_rule, o.auth_rule) AS version_auth_rule,
                       COALESCE(v.idempotency, o.idempotency) AS version_idempotency,
                       COALESCE(v.source_repo, o.source_repo) AS version_source_repo,
                       COALESCE(v.source_path, o.source_path) AS version_source_path,
                       COALESCE(v.source_owner, o.source_owner) AS version_source_owner,
                       v.origin_type, v.discovery_confidence, v.scan_id, v.approval_ref,
                       v.content_hash, v.embedding_model, v.embedding_dims,
                       v.created_at AS version_created_at, v.updated_at AS version_updated_at,
                       v.released_at
                  FROM api_operations o
                  JOIN api_versions v ON v.api_id = o.api_id
                 WHERE o.api_id = ?
                """ + (version == null || version.isBlank()
                ? " ORDER BY v.updated_at DESC"
                : " AND v.version = ?");
        try (PreparedStatement ps = connection.prepareStatement(sql)) {
            ps.setString(1, apiId);
            if (version != null && !version.isBlank()) {
                ps.setString(2, version);
            }
            try (ResultSet rs = ps.executeQuery()) {
                if (!rs.next()) {
                    return Map.of();
                }
                return readFullDefinition(rs);
            }
        }
    }

    @Override
    public synchronized List<Map<String, Object>> search(
            String query,
            float[] queryEmbedding,
            Map<String, String> filters,
            int limit
    ) throws Exception {
        int safeLimit = Math.max(1, Math.min(limit, 100));
        int candidateLimit = Math.min(safeLimit * 3, 300);
        List<Map<String, Object>> candidates = new ArrayList<>(postgres
                ? searchPostgres(query, queryEmbedding, filters, candidateLimit)
                : searchPortable(query, queryEmbedding, filters, candidateLimit));
        for (Map<String, Object> candidate : candidates) {
            candidate.put("context_score", contextScore(candidate, filters));
            candidate.put("score", combinedScore(candidate));
        }
        candidates.sort(Comparator.comparingDouble(this::combinedScore).reversed());
        return candidates.stream().limit(safeLimit).toList();
    }

    @Override
    public synchronized Map<String, Object> transition(
            String apiId,
            String version,
            ApiStatus status,
            String actor,
            String note,
            String supersededByVersion
    ) throws Exception {
        ExistingVersion existing = existingVersion(apiId, version);
        if (existing == null) {
            throw new IllegalArgumentException("API version not found");
        }
        if (!existing.status().canTransitionTo(status)) {
            throw new IllegalStateException(
                    "invalid lifecycle transition: " + existing.status() + " -> " + status
            );
        }
        Instant now = Instant.now();
        String sql = """
                UPDATE api_versions
                   SET lifecycle_status = ?, updated_at = ?,
                       released_at = CASE WHEN ? = 'RELEASED' THEN COALESCE(released_at, ?) ELSE released_at END
                 WHERE api_id = ? AND version = ?
                """;
        try (PreparedStatement ps = connection.prepareStatement(sql)) {
            ps.setString(1, status.name());
            ps.setTimestamp(2, Timestamp.from(now));
            ps.setString(3, status.name());
            ps.setTimestamp(4, Timestamp.from(now));
            ps.setString(5, apiId);
            ps.setString(6, version);
            ps.executeUpdate();
        }
        insertLifecycleEvent(
                apiId,
                version,
                existing.status(),
                status,
                actor,
                note,
                supersededByVersion,
                now
        );
        return get(apiId, version);
    }

    @Override
    public synchronized Map<String, Object> graph(String system) throws Exception {
        List<Map<String, Object>> modules = new ArrayList<>();
        String moduleSql = """
                SELECT system_key, module_key, name, description
                  FROM api_modules
                 WHERE (? IS NULL OR system_key = ?)
                 ORDER BY system_key, module_key
                """;
        try (PreparedStatement ps = connection.prepareStatement(moduleSql)) {
            ps.setString(1, blankToNull(system));
            ps.setString(2, blankToNull(system));
            try (ResultSet rs = ps.executeQuery()) {
                while (rs.next()) {
                    modules.add(row(
                            "system", rs.getString("system_key"),
                            "module", rs.getString("module_key"),
                            "name", rs.getString("name"),
                            "description", rs.getString("description")
                    ));
                }
            }
        }

        List<Map<String, Object>> apis = new ArrayList<>();
        String apiSql = """
                SELECT o.api_id, o.system_key, o.module_key, o.operation_name,
                       v.version, v.lifecycle_status
                  FROM api_operations o
                  JOIN api_versions v ON v.api_id = o.api_id
                 WHERE (? IS NULL OR o.system_key = ?)
                 ORDER BY o.system_key, o.module_key, o.operation_name, v.version
                """;
        try (PreparedStatement ps = connection.prepareStatement(apiSql)) {
            ps.setString(1, blankToNull(system));
            ps.setString(2, blankToNull(system));
            try (ResultSet rs = ps.executeQuery()) {
                while (rs.next()) {
                    apis.add(row(
                            "api_id", rs.getString("api_id"),
                            "system", rs.getString("system_key"),
                            "module", rs.getString("module_key"),
                            "name", rs.getString("operation_name"),
                            "version", rs.getString("version"),
                            "status", rs.getString("lifecycle_status")
                    ));
                }
            }
        }

        List<Map<String, Object>> relations = new ArrayList<>();
        String relationSql = """
                SELECT r.api_id, r.version, r.relation_type, r.target_api_id, r.target_version
                  FROM api_relations r
                  JOIN api_operations o ON o.api_id = r.api_id
                 WHERE (? IS NULL OR o.system_key = ?)
                """;
        try (PreparedStatement ps = connection.prepareStatement(relationSql)) {
            ps.setString(1, blankToNull(system));
            ps.setString(2, blankToNull(system));
            try (ResultSet rs = ps.executeQuery()) {
                while (rs.next()) {
                    relations.add(row(
                            "api_id", rs.getString("api_id"),
                            "version", rs.getString("version"),
                            "type", rs.getString("relation_type"),
                            "target_api_id", rs.getString("target_api_id"),
                            "target_version", rs.getString("target_version")
                    ));
                }
            }
        }
        return row("modules", modules, "apis", apis, "relations", relations);
    }

    @Override
    public synchronized Map<String, Object> health() throws Exception {
        try (Statement stmt = connection.createStatement();
             ResultSet rs = stmt.executeQuery("SELECT COUNT(*) FROM api_versions")) {
            rs.next();
            return row(
                    "ok", true,
                    "provider", postgres ? "postgres" : "embedded",
                    "api_versions", rs.getLong(1),
                    "vector_storage", postgres ? "pgvector(384)" : "relational-text-vector"
            );
        }
    }

    @Override
    public synchronized void close() throws Exception {
        if (ownsConnection) {
            connection.close();
        }
    }

    private void initializePostgresSchema() throws IOException, SQLException {
        String sql;
        try (InputStream in = getClass().getClassLoader().getResourceAsStream("api-pool-postgres.sql")) {
            if (in == null) {
                throw new IOException("api-pool-postgres.sql not found");
            }
            sql = new String(in.readAllBytes(), StandardCharsets.UTF_8);
        }
        try (Statement stmt = connection.createStatement()) {
            for (String part : sql.split(";")) {
                String trimmed = part.trim();
                if (!trimmed.isEmpty()) {
                    stmt.execute(trimmed);
                }
            }
        }
    }

    private void upsertSystem(String system, Instant now) throws SQLException {
        String sql = postgres
                ? """
                  INSERT INTO api_systems(system_key, name, updated_at) VALUES (?, ?, ?)
                  ON CONFLICT(system_key) DO UPDATE SET name = EXCLUDED.name, updated_at = EXCLUDED.updated_at
                  """
                : "MERGE INTO api_systems(system_key, name, updated_at) KEY(system_key) VALUES (?, ?, ?)";
        try (PreparedStatement ps = connection.prepareStatement(sql)) {
            ps.setString(1, system);
            ps.setString(2, system);
            ps.setTimestamp(3, Timestamp.from(now));
            ps.executeUpdate();
        }
    }

    private void upsertModule(String system, String module, Instant now) throws SQLException {
        String sql = postgres
                ? """
                  INSERT INTO api_modules(system_key, module_key, name, updated_at) VALUES (?, ?, ?, ?)
                  ON CONFLICT(system_key, module_key) DO UPDATE
                  SET name = EXCLUDED.name, updated_at = EXCLUDED.updated_at
                  """
                : """
                  MERGE INTO api_modules(system_key, module_key, name, updated_at)
                  KEY(system_key, module_key) VALUES (?, ?, ?, ?)
                  """;
        try (PreparedStatement ps = connection.prepareStatement(sql)) {
            ps.setString(1, system);
            ps.setString(2, module);
            ps.setString(3, module);
            ps.setTimestamp(4, Timestamp.from(now));
            ps.executeUpdate();
        }
    }

    private void upsertOperation(ApiDefinition definition, Instant now) throws SQLException {
        String sql = postgres
                ? """
                  INSERT INTO api_operations(
                    api_id, system_key, module_key, operation_name, api_kind,
                    capability, signature, auth_rule, idempotency,
                    source_repo, source_path, source_owner, created_at, updated_at
                  ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                  ON CONFLICT(api_id) DO UPDATE SET
                    system_key = EXCLUDED.system_key,
                    module_key = EXCLUDED.module_key,
                    operation_name = EXCLUDED.operation_name,
                    api_kind = EXCLUDED.api_kind,
                    capability = EXCLUDED.capability,
                    signature = EXCLUDED.signature,
                    auth_rule = EXCLUDED.auth_rule,
                    idempotency = EXCLUDED.idempotency,
                    source_repo = EXCLUDED.source_repo,
                    source_path = EXCLUDED.source_path,
                    source_owner = EXCLUDED.source_owner,
                    updated_at = EXCLUDED.updated_at
                  """
                : """
                  MERGE INTO api_operations(
                    api_id, system_key, module_key, operation_name, api_kind,
                    capability, signature, auth_rule, idempotency,
                    source_repo, source_path, source_owner, created_at, updated_at
                  ) KEY(api_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                  """;
        try (PreparedStatement ps = connection.prepareStatement(sql)) {
            int i = 1;
            ps.setString(i++, definition.apiId());
            ps.setString(i++, definition.system());
            ps.setString(i++, definition.module());
            ps.setString(i++, definition.name());
            ps.setString(i++, definition.kind());
            ps.setString(i++, definition.capability());
            ps.setString(i++, definition.signature());
            ps.setString(i++, definition.auth());
            ps.setString(i++, definition.idempotency());
            ps.setString(i++, definition.source().repo());
            ps.setString(i++, definition.source().path());
            ps.setString(i++, definition.source().owner());
            ps.setTimestamp(i++, Timestamp.from(now));
            ps.setTimestamp(i, Timestamp.from(now));
            ps.executeUpdate();
        }
    }

    private void upsertVersion(
            ApiDefinition definition,
            float[] embedding,
            String embeddingModel,
            String contentHash,
            Instant now,
            boolean created,
            boolean replaceEmbedding
    ) throws SQLException {
        String vector = VectorMath.encode(embedding);
        if (created) {
            String vectorValue = postgres ? "CAST(? AS vector)" : "?";
            String sql = """
                    INSERT INTO api_versions(
                      api_id, version, lifecycle_status,
                      capability, signature, auth_rule, idempotency,
                      source_repo, source_path, source_owner,
                      origin_type, discovery_confidence, scan_id, approval_ref,
                      source_commit, content_hash,
                      embedding_model, embedding_dims, embedding, created_at, updated_at, released_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, %s, ?, ?, ?)
                    """.formatted(vectorValue);
            try (PreparedStatement ps = connection.prepareStatement(sql)) {
                int i = 1;
                ps.setString(i++, definition.apiId());
                ps.setString(i++, definition.version());
                ps.setString(i++, definition.status().name());
                ps.setString(i++, definition.capability());
                ps.setString(i++, definition.signature());
                ps.setString(i++, definition.auth());
                ps.setString(i++, definition.idempotency());
                ps.setString(i++, definition.source().repo());
                ps.setString(i++, definition.source().path());
                ps.setString(i++, definition.source().owner());
                ps.setString(i++, definition.origin());
                ps.setString(i++, definition.discoveryConfidence());
                ps.setString(i++, definition.scanId());
                ps.setString(i++, definition.approvalRef());
                ps.setString(i++, definition.source().commit());
                ps.setString(i++, contentHash);
                ps.setString(i++, embeddingModel);
                ps.setInt(i++, embedding == null ? 0 : embedding.length);
                ps.setString(i++, vector);
                ps.setTimestamp(i++, Timestamp.from(now));
                ps.setTimestamp(i++, Timestamp.from(now));
                ps.setTimestamp(i, definition.status() == ApiStatus.RELEASED
                        ? Timestamp.from(now)
                        : null);
                ps.executeUpdate();
            }
            return;
        }

        String embeddingUpdate = replaceEmbedding
                ? ", embedding_model = ?, embedding_dims = ?, embedding = "
                    + (postgres ? "CAST(? AS vector)" : "?")
                : "";
        String sql = """
                UPDATE api_versions
                   SET lifecycle_status = ?,
                       capability = ?, signature = ?, auth_rule = ?, idempotency = ?,
                       source_repo = ?, source_path = ?, source_owner = ?,
                       origin_type = ?, discovery_confidence = ?, scan_id = ?, approval_ref = ?,
                       source_commit = ?, content_hash = ?,
                       updated_at = ?%s
                 WHERE api_id = ? AND version = ?
                """.formatted(embeddingUpdate);
        try (PreparedStatement ps = connection.prepareStatement(sql)) {
            int i = 1;
            ps.setString(i++, definition.status().name());
            ps.setString(i++, definition.capability());
            ps.setString(i++, definition.signature());
            ps.setString(i++, definition.auth());
            ps.setString(i++, definition.idempotency());
            ps.setString(i++, definition.source().repo());
            ps.setString(i++, definition.source().path());
            ps.setString(i++, definition.source().owner());
            ps.setString(i++, definition.origin());
            ps.setString(i++, definition.discoveryConfidence());
            ps.setString(i++, definition.scanId());
            ps.setString(i++, definition.approvalRef());
            ps.setString(i++, definition.source().commit());
            ps.setString(i++, contentHash);
            ps.setTimestamp(i++, Timestamp.from(now));
            if (replaceEmbedding) {
                ps.setString(i++, embeddingModel);
                ps.setInt(i++, embedding == null ? 0 : embedding.length);
                ps.setString(i++, vector);
            }
            ps.setString(i++, definition.apiId());
            ps.setString(i, definition.version());
            ps.executeUpdate();
        }
    }

    private void replaceChildren(ApiDefinition definition) throws SQLException {
        deleteChildren(definition.apiId(), definition.version());
        insertParameters(definition, "INPUT", definition.inputs());
        insertParameters(definition, "OUTPUT", definition.outputs());
        insertGuidance(definition, "USE_WHEN", definition.useWhen());
        insertGuidance(definition, "DO_NOT_USE_WHEN", definition.doNotUseWhen());
        insertErrors(definition);
        insertSideEffects(definition);
        insertDiscoveryEvidence(definition);
        insertRelations(definition);
    }

    private void deleteChildren(String apiId, String version) throws SQLException {
        for (String table : List.of(
                "api_parameters",
                "api_usage_guidance",
                "api_errors",
                "api_side_effects",
                "api_discovery_evidence",
                "api_relations"
        )) {
            try (PreparedStatement ps = connection.prepareStatement(
                    "DELETE FROM " + table + " WHERE api_id = ? AND version = ?"
            )) {
                ps.setString(1, apiId);
                ps.setString(2, version);
                ps.executeUpdate();
            }
        }
    }

    private void insertParameters(
            ApiDefinition definition,
            String direction,
            List<ApiDefinition.Parameter> parameters
    ) throws SQLException {
        String sql = """
                INSERT INTO api_parameters(
                  api_id, version, direction, ordinal, param_name, param_type, description, is_required
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """;
        try (PreparedStatement ps = connection.prepareStatement(sql)) {
            for (int i = 0; i < parameters.size(); i++) {
                ApiDefinition.Parameter parameter = parameters.get(i);
                ps.setString(1, definition.apiId());
                ps.setString(2, definition.version());
                ps.setString(3, direction);
                ps.setInt(4, i);
                ps.setString(5, parameter.name());
                ps.setString(6, parameter.type());
                ps.setString(7, parameter.description());
                ps.setBoolean(8, parameter.required());
                ps.addBatch();
            }
            ps.executeBatch();
        }
    }

    private void insertGuidance(
            ApiDefinition definition,
            String type,
            List<String> guidance
    ) throws SQLException {
        String sql = """
                INSERT INTO api_usage_guidance(
                  api_id, version, guidance_type, ordinal, guidance_text
                ) VALUES (?, ?, ?, ?, ?)
                """;
        try (PreparedStatement ps = connection.prepareStatement(sql)) {
            for (int i = 0; i < guidance.size(); i++) {
                ps.setString(1, definition.apiId());
                ps.setString(2, definition.version());
                ps.setString(3, type);
                ps.setInt(4, i);
                ps.setString(5, guidance.get(i));
                ps.addBatch();
            }
            ps.executeBatch();
        }
    }

    private void insertErrors(ApiDefinition definition) throws SQLException {
        String sql = "INSERT INTO api_errors(api_id, version, error_code, description) VALUES (?, ?, ?, ?)";
        try (PreparedStatement ps = connection.prepareStatement(sql)) {
            for (ApiDefinition.ApiError error : definition.errors()) {
                ps.setString(1, definition.apiId());
                ps.setString(2, definition.version());
                ps.setString(3, error.code());
                ps.setString(4, error.description());
                ps.addBatch();
            }
            ps.executeBatch();
        }
    }

    private void insertSideEffects(ApiDefinition definition) throws SQLException {
        String sql = "INSERT INTO api_side_effects(api_id, version, ordinal, effect_text) VALUES (?, ?, ?, ?)";
        try (PreparedStatement ps = connection.prepareStatement(sql)) {
            for (int i = 0; i < definition.sideEffects().size(); i++) {
                ps.setString(1, definition.apiId());
                ps.setString(2, definition.version());
                ps.setInt(3, i);
                ps.setString(4, definition.sideEffects().get(i));
                ps.addBatch();
            }
            ps.executeBatch();
        }
    }

    private void insertDiscoveryEvidence(ApiDefinition definition) throws SQLException {
        String sql = """
                INSERT INTO api_discovery_evidence(
                  api_id, version, ordinal, evidence_kind, source_path,
                  source_line, source_symbol, detail
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """;
        try (PreparedStatement ps = connection.prepareStatement(sql)) {
            for (int i = 0; i < definition.discoveryEvidence().size(); i++) {
                ApiDefinition.DiscoveryEvidence evidence =
                        definition.discoveryEvidence().get(i);
                ps.setString(1, definition.apiId());
                ps.setString(2, definition.version());
                ps.setInt(3, i);
                ps.setString(4, evidence.kind());
                ps.setString(5, evidence.path());
                if (evidence.line() == null) {
                    ps.setNull(6, java.sql.Types.INTEGER);
                } else {
                    ps.setInt(6, evidence.line());
                }
                ps.setString(7, evidence.symbol());
                ps.setString(8, evidence.detail());
                ps.addBatch();
            }
            ps.executeBatch();
        }
    }

    private void insertRelations(ApiDefinition definition) throws SQLException {
        String sql = """
                INSERT INTO api_relations(
                  api_id, version, relation_type, target_api_id, target_version
                ) VALUES (?, ?, ?, ?, ?)
                """;
        try (PreparedStatement ps = connection.prepareStatement(sql)) {
            for (ApiDefinition.Relation relation : definition.relations()) {
                ps.setString(1, definition.apiId());
                ps.setString(2, definition.version());
                ps.setString(3, relation.type());
                ps.setString(4, relation.targetApiId());
                ps.setString(5, relation.targetVersion());
                ps.addBatch();
            }
            ps.executeBatch();
        }
    }

    private ExistingVersion existingVersion(String apiId, String version) throws SQLException {
        try (PreparedStatement ps = connection.prepareStatement(
                "SELECT lifecycle_status, content_hash FROM api_versions WHERE api_id = ? AND version = ?"
        )) {
            ps.setString(1, apiId);
            ps.setString(2, version);
            try (ResultSet rs = ps.executeQuery()) {
                if (!rs.next()) {
                    return null;
                }
                return new ExistingVersion(
                        ApiStatus.parse(rs.getString("lifecycle_status")),
                        rs.getString("content_hash")
                );
            }
        }
    }

    private ExistingOperation existingOperation(String apiId) throws SQLException {
        try (PreparedStatement ps = connection.prepareStatement(
                "SELECT source_repo FROM api_operations WHERE api_id = ?"
        )) {
            ps.setString(1, apiId);
            try (ResultSet rs = ps.executeQuery()) {
                if (!rs.next()) {
                    return null;
                }
                return new ExistingOperation(rs.getString("source_repo"));
            }
        }
    }

    private void insertLifecycleEvent(
            String apiId,
            String version,
            ApiStatus from,
            ApiStatus to,
            String actor,
            String note,
            String relatedVersion,
            Instant at
    ) throws SQLException {
        String sql = """
                INSERT INTO api_lifecycle_events(
                  api_id, version, from_status, to_status, actor, note, related_version, occurred_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """;
        try (PreparedStatement ps = connection.prepareStatement(sql)) {
            ps.setString(1, apiId);
            ps.setString(2, version);
            ps.setString(3, from == null ? null : from.name());
            ps.setString(4, to.name());
            ps.setString(5, actor);
            ps.setString(6, note);
            ps.setString(7, relatedVersion);
            ps.setTimestamp(8, Timestamp.from(at));
            ps.executeUpdate();
        }
    }

    private List<Map<String, Object>> searchPortable(
            String query,
            float[] queryEmbedding,
            Map<String, String> filters,
            int limit
    ) throws SQLException {
        StringBuilder sql = new StringBuilder("""
                SELECT o.api_id, o.system_key, o.module_key, o.operation_name, o.api_kind,
                       COALESCE(v.capability, o.capability) AS capability,
                       COALESCE(v.signature, o.signature) AS signature,
                       COALESCE(v.source_repo, o.source_repo) AS source_repo,
                       COALESCE(v.source_path, o.source_path) AS source_path,
                       v.version, v.lifecycle_status, v.embedding, v.embedding_model,
                       v.updated_at
                  FROM api_operations o
                  JOIN api_versions v ON v.api_id = o.api_id
                 WHERE v.lifecycle_status <> 'RETIRED'
                """);
        List<String> parameters = appendFilters(sql, filters);
        List<Map<String, Object>> candidates = new ArrayList<>();
        try (PreparedStatement ps = connection.prepareStatement(sql.toString())) {
            for (int i = 0; i < parameters.size(); i++) {
                ps.setString(i + 1, parameters.get(i));
            }
            try (ResultSet rs = ps.executeQuery()) {
                while (rs.next()) {
                    double lexical = lexicalScore(query, rs);
                    double semantic = VectorMath.cosine(
                            queryEmbedding,
                            VectorMath.decode(rs.getString("embedding"))
                    );
                    candidates.add(searchRow(rs, lexical, semantic));
                }
            }
        }
        candidates.sort(Comparator.comparingDouble(this::combinedScore).reversed());
        return candidates.stream().limit(limit).toList();
    }

    private List<Map<String, Object>> searchPostgres(
            String query,
            float[] queryEmbedding,
            Map<String, String> filters,
            int limit
    ) throws SQLException {
        String vector = VectorMath.encode(queryEmbedding);
        StringBuilder sql = new StringBuilder("""
                SELECT o.api_id, o.system_key, o.module_key, o.operation_name, o.api_kind,
                       COALESCE(v.capability, o.capability) AS capability,
                       COALESCE(v.signature, o.signature) AS signature,
                       COALESCE(v.source_repo, o.source_repo) AS source_repo,
                       COALESCE(v.source_path, o.source_path) AS source_path,
                       v.version, v.lifecycle_status, v.embedding_model, v.updated_at,
                       ts_rank(
                         to_tsvector(
                           'english',
                           o.operation_name || ' '
                             || COALESCE(v.capability, o.capability) || ' '
                             || COALESCE(v.signature, o.signature)
                         ),
                         plainto_tsquery('english', ?)
                       ) AS lexical_score,
                       CASE WHEN ? IS NULL OR v.embedding IS NULL THEN 0
                            ELSE 1 - (v.embedding <=> CAST(? AS vector)) END AS semantic_score
                  FROM api_operations o
                  JOIN api_versions v ON v.api_id = o.api_id
                 WHERE v.lifecycle_status <> 'RETIRED'
                """);
        List<String> parameters = appendFilters(sql, filters);
        sql.append("""
                 ORDER BY (
                   CASE v.lifecycle_status
                     WHEN 'RELEASED' THEN 0.30
                     WHEN 'DEVELOPING' THEN 0.20
                     WHEN 'SUPERSEDED' THEN 0.05
                     WHEN 'DEPRECATED' THEN 0.01
                     ELSE 0
                   END
                   + ts_rank(
                       to_tsvector(
                         'english',
                         o.operation_name || ' '
                           || COALESCE(v.capability, o.capability) || ' '
                           || COALESCE(v.signature, o.signature)
                       ),
                       plainto_tsquery('english', ?)
                     ) * 0.35
                   + CASE WHEN ? IS NULL OR v.embedding IS NULL THEN 0
                          ELSE (1 - (v.embedding <=> CAST(? AS vector))) * 0.65 END
                 ) DESC
                 LIMIT ?
                """);
        List<Map<String, Object>> results = new ArrayList<>();
        try (PreparedStatement ps = connection.prepareStatement(sql.toString())) {
            int i = 1;
            ps.setString(i++, query);
            ps.setString(i++, vector);
            ps.setString(i++, vector);
            for (String parameter : parameters) {
                ps.setString(i++, parameter);
            }
            ps.setString(i++, query);
            ps.setString(i++, vector);
            ps.setString(i++, vector);
            ps.setInt(i, limit);
            try (ResultSet rs = ps.executeQuery()) {
                while (rs.next()) {
                    results.add(searchRow(
                            rs,
                            rs.getDouble("lexical_score"),
                            rs.getDouble("semantic_score")
                    ));
                }
            }
        }
        return results;
    }

    private List<String> appendFilters(StringBuilder sql, Map<String, String> filters) {
        List<String> parameters = new ArrayList<>();
        if (filters != null) {
            addFilter(sql, parameters, "system", "o.system_key", filters.get("system"));
            addFilter(sql, parameters, "module", "o.module_key", filters.get("module"));
            addFilter(sql, parameters, "status", "v.lifecycle_status", filters.get("status"));
            addFilter(sql, parameters, "kind", "o.api_kind", filters.get("kind"));
        }
        return parameters;
    }

    private void addFilter(
            StringBuilder sql,
            List<String> parameters,
            String ignoredName,
            String column,
            String value
    ) {
        if (value != null && !value.isBlank()) {
            sql.append(" AND ").append(column).append(" = ?");
            parameters.add(value.trim());
        }
    }

    private Map<String, Object> searchRow(ResultSet rs, double lexical, double semantic)
            throws SQLException {
        ApiStatus status = ApiStatus.parse(rs.getString("lifecycle_status"));
        Map<String, Object> row = row(
                "api_id", rs.getString("api_id"),
                "system", rs.getString("system_key"),
                "module", rs.getString("module_key"),
                "name", rs.getString("operation_name"),
                "kind", rs.getString("api_kind"),
                "version", rs.getString("version"),
                "status", status.name(),
                "capability", rs.getString("capability"),
                "signature", rs.getString("signature"),
                "source_repo", rs.getString("source_repo"),
                "source_path", rs.getString("source_path"),
                "lexical_score", lexical,
                "semantic_score", semantic,
                "lifecycle_score", lifecycleScore(status)
        );
        row.put("score", combinedScore(row));
        row.put("reuse_guidance", reuseGuidance(status));
        return row;
    }

    private double combinedScore(Map<String, Object> row) {
        return ((Number) row.getOrDefault("semantic_score", 0)).doubleValue() * 0.65
                + ((Number) row.getOrDefault("lexical_score", 0)).doubleValue() * 0.35
                + ((Number) row.getOrDefault("lifecycle_score", 0)).doubleValue()
                + ((Number) row.getOrDefault("context_score", 0)).doubleValue();
    }

    private double contextScore(Map<String, Object> row, Map<String, String> filters) {
        if (filters == null) {
            return 0;
        }
        String contextSystem = filters.get("context_system");
        String contextModule = filters.get("context_module");
        double score = 0;
        if (contextSystem != null && contextSystem.equals(row.get("system"))) {
            score += 0.15;
            if (contextModule != null && contextModule.equals(row.get("module"))) {
                score += 0.10;
            }
        }
        return score;
    }

    private double lexicalScore(String query, ResultSet rs) throws SQLException {
        if (query == null || query.isBlank()) {
            return 0;
        }
        String haystack = String.join(" ",
                rs.getString("operation_name"),
                rs.getString("capability"),
                rs.getString("signature")
        ).toLowerCase(Locale.ROOT);
        LinkedHashSet<String> words = new LinkedHashSet<>(List.of(
                query.toLowerCase(Locale.ROOT).split("\\W+")
        ));
        if (words.isEmpty()) {
            return 0;
        }
        long matches = words.stream().filter(word -> !word.isBlank() && haystack.contains(word)).count();
        return (double) matches / words.size();
    }

    private double lifecycleScore(ApiStatus status) {
        return switch (status) {
            case RELEASED -> 0.30;
            case DEVELOPING -> 0.20;
            case SUPERSEDED -> 0.05;
            case DEPRECATED -> 0.01;
            case RETIRED -> 0;
        };
    }

    private String reuseGuidance(ApiStatus status) {
        return switch (status) {
            case RELEASED -> "preferred for reuse";
            case DEVELOPING -> "coordinate before creating a duplicate";
            case SUPERSEDED -> "use the superseding version";
            case DEPRECATED -> "avoid for new consumers";
            case RETIRED -> "not available for reuse";
        };
    }

    private Map<String, Object> readFullDefinition(ResultSet rs) throws SQLException {
        String apiId = rs.getString("api_id");
        String version = rs.getString("version");
        Map<String, Object> out = row(
                "api_id", apiId,
                "system", rs.getString("system_key"),
                "module", rs.getString("module_key"),
                "name", rs.getString("operation_name"),
                "kind", rs.getString("api_kind"),
                "version", version,
                "status", rs.getString("lifecycle_status"),
                "capability", rs.getString("version_capability"),
                "signature", rs.getString("version_signature"),
                "auth", rs.getString("version_auth_rule"),
                "idempotency", rs.getString("version_idempotency"),
                "origin", rs.getString("origin_type"),
                "discovery_confidence", rs.getString("discovery_confidence"),
                "scan_id", rs.getString("scan_id"),
                "approval_ref", rs.getString("approval_ref"),
                "content_hash", rs.getString("content_hash"),
                "embedding_model", rs.getString("embedding_model"),
                "embedding_dimensions", rs.getInt("embedding_dims"),
                "created_at", epoch(rs.getTimestamp("version_created_at")),
                "updated_at", epoch(rs.getTimestamp("version_updated_at")),
                "released_at", epoch(rs.getTimestamp("released_at"))
        );
        out.put("source", row(
                "repo", rs.getString("version_source_repo"),
                "path", rs.getString("version_source_path"),
                "commit", rs.getString("source_commit"),
                "owner", rs.getString("version_source_owner")
        ));
        out.put("inputs", readParameters(apiId, version, "INPUT"));
        out.put("outputs", readParameters(apiId, version, "OUTPUT"));
        out.put("use_when", readGuidance(apiId, version, "USE_WHEN"));
        out.put("do_not_use_when", readGuidance(apiId, version, "DO_NOT_USE_WHEN"));
        out.put("errors", readErrors(apiId, version));
        out.put("side_effects", readSideEffects(apiId, version));
        out.put("discovery_evidence", readDiscoveryEvidence(apiId, version));
        out.put("relations", readRelations(apiId, version));
        out.put("lifecycle_events", readEvents(apiId, version));
        return out;
    }

    private List<Map<String, Object>> readParameters(String apiId, String version, String direction)
            throws SQLException {
        String sql = """
                SELECT param_name, param_type, description, is_required
                  FROM api_parameters
                 WHERE api_id = ? AND version = ? AND direction = ?
                 ORDER BY ordinal
                """;
        List<Map<String, Object>> out = new ArrayList<>();
        try (PreparedStatement ps = connection.prepareStatement(sql)) {
            ps.setString(1, apiId);
            ps.setString(2, version);
            ps.setString(3, direction);
            try (ResultSet rs = ps.executeQuery()) {
                while (rs.next()) {
                    out.add(row(
                            "name", rs.getString("param_name"),
                            "type", rs.getString("param_type"),
                            "description", rs.getString("description"),
                            "required", rs.getBoolean("is_required")
                    ));
                }
            }
        }
        return out;
    }

    private List<String> readGuidance(String apiId, String version, String type) throws SQLException {
        String sql = """
                SELECT guidance_text FROM api_usage_guidance
                 WHERE api_id = ? AND version = ? AND guidance_type = ?
                 ORDER BY ordinal
                """;
        List<String> out = new ArrayList<>();
        try (PreparedStatement ps = connection.prepareStatement(sql)) {
            ps.setString(1, apiId);
            ps.setString(2, version);
            ps.setString(3, type);
            try (ResultSet rs = ps.executeQuery()) {
                while (rs.next()) {
                    out.add(rs.getString(1));
                }
            }
        }
        return out;
    }

    private List<Map<String, Object>> readErrors(String apiId, String version) throws SQLException {
        List<Map<String, Object>> out = new ArrayList<>();
        try (PreparedStatement ps = connection.prepareStatement(
                "SELECT error_code, description FROM api_errors WHERE api_id = ? AND version = ?"
        )) {
            ps.setString(1, apiId);
            ps.setString(2, version);
            try (ResultSet rs = ps.executeQuery()) {
                while (rs.next()) {
                    out.add(row("code", rs.getString(1), "description", rs.getString(2)));
                }
            }
        }
        return out;
    }

    private List<String> readSideEffects(String apiId, String version) throws SQLException {
        List<String> out = new ArrayList<>();
        try (PreparedStatement ps = connection.prepareStatement(
                "SELECT effect_text FROM api_side_effects WHERE api_id = ? AND version = ? ORDER BY ordinal"
        )) {
            ps.setString(1, apiId);
            ps.setString(2, version);
            try (ResultSet rs = ps.executeQuery()) {
                while (rs.next()) {
                    out.add(rs.getString(1));
                }
            }
        }
        return out;
    }

    private List<Map<String, Object>> readDiscoveryEvidence(String apiId, String version)
            throws SQLException {
        List<Map<String, Object>> out = new ArrayList<>();
        try (PreparedStatement ps = connection.prepareStatement("""
                SELECT evidence_kind, source_path, source_line, source_symbol, detail
                  FROM api_discovery_evidence
                 WHERE api_id = ? AND version = ?
                 ORDER BY ordinal
                """)) {
            ps.setString(1, apiId);
            ps.setString(2, version);
            try (ResultSet rs = ps.executeQuery()) {
                while (rs.next()) {
                    Integer line = rs.getObject("source_line") == null
                            ? null
                            : rs.getInt("source_line");
                    out.add(row(
                            "kind", rs.getString("evidence_kind"),
                            "path", rs.getString("source_path"),
                            "line", line,
                            "symbol", rs.getString("source_symbol"),
                            "detail", rs.getString("detail")
                    ));
                }
            }
        }
        return out;
    }

    private List<Map<String, Object>> readRelations(String apiId, String version) throws SQLException {
        List<Map<String, Object>> out = new ArrayList<>();
        try (PreparedStatement ps = connection.prepareStatement("""
                SELECT relation_type, target_api_id, target_version
                  FROM api_relations WHERE api_id = ? AND version = ?
                """)) {
            ps.setString(1, apiId);
            ps.setString(2, version);
            try (ResultSet rs = ps.executeQuery()) {
                while (rs.next()) {
                    out.add(row(
                            "type", rs.getString(1),
                            "target_api_id", rs.getString(2),
                            "target_version", rs.getString(3)
                    ));
                }
            }
        }
        return out;
    }

    private List<Map<String, Object>> readEvents(String apiId, String version) throws SQLException {
        List<Map<String, Object>> out = new ArrayList<>();
        try (PreparedStatement ps = connection.prepareStatement("""
                SELECT from_status, to_status, actor, note, related_version, occurred_at
                  FROM api_lifecycle_events
                 WHERE api_id = ? AND version = ?
                 ORDER BY occurred_at
                """)) {
            ps.setString(1, apiId);
            ps.setString(2, version);
            try (ResultSet rs = ps.executeQuery()) {
                while (rs.next()) {
                    out.add(row(
                            "from_status", rs.getString(1),
                            "to_status", rs.getString(2),
                            "actor", rs.getString(3),
                            "note", rs.getString(4),
                            "related_version", rs.getString(5),
                            "occurred_at", epoch(rs.getTimestamp(6))
                    ));
                }
            }
        }
        return out;
    }

    private static Map<String, Object> row(Object... entries) {
        Map<String, Object> out = new LinkedHashMap<>();
        for (int i = 0; i < entries.length; i += 2) {
            out.put(String.valueOf(entries[i]), entries[i + 1]);
        }
        return out;
    }

    private static String blankToNull(String value) {
        return value == null || value.isBlank() ? null : value;
    }

    private static Double epoch(Timestamp timestamp) {
        if (timestamp == null) {
            return null;
        }
        Instant instant = timestamp.toInstant();
        return instant.getEpochSecond() + instant.getNano() / 1_000_000_000.0;
    }

    private record ExistingVersion(ApiStatus status, String contentHash) {
    }

    private record ExistingOperation(String sourceRepo) {
    }
}
