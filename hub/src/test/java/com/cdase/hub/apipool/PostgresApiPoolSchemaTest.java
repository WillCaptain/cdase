package com.cdase.hub.apipool;

import org.junit.jupiter.api.Test;

import java.io.InputStream;
import java.nio.charset.StandardCharsets;

import static org.junit.jupiter.api.Assertions.assertTrue;

class PostgresApiPoolSchemaTest {

    @Test
    void productionSchemaUsesRelationalTablesAndPgvectorColumn() throws Exception {
        String sql;
        try (InputStream input = getClass().getClassLoader()
                .getResourceAsStream("api-pool-postgres.sql")) {
            assertTrue(input != null, "api-pool-postgres.sql must be packaged");
            sql = new String(input.readAllBytes(), StandardCharsets.UTF_8);
        }

        assertTrue(sql.contains("CREATE EXTENSION IF NOT EXISTS vector"));
        assertTrue(sql.contains("embedding        vector(384)"));
        assertTrue(sql.contains("CREATE TABLE IF NOT EXISTS api_operations"));
        assertTrue(sql.contains("CREATE TABLE IF NOT EXISTS api_versions"));
        assertTrue(sql.contains("CREATE TABLE IF NOT EXISTS api_parameters"));
        assertTrue(sql.contains("CREATE TABLE IF NOT EXISTS api_discovery_evidence"));
        assertTrue(sql.contains("CREATE TABLE IF NOT EXISTS api_relations"));
        assertTrue(sql.contains("CREATE TABLE IF NOT EXISTS api_lifecycle_events"));
        assertTrue(sql.contains("discovery_confidence"));
        assertTrue(sql.contains("approval_ref"));
        assertTrue(sql.contains("vector_cosine_ops"));
    }
}
