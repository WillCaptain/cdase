package com.cdase.hub.apipool;

import com.cdase.hub.db.Database;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

class ApiPoolServiceTest {

    private Path tempDir;
    private Database database;
    private ApiPoolService service;

    @BeforeEach
    void setUp() throws Exception {
        tempDir = Files.createTempDirectory("cdase-api-pool-test");
        database = new Database(tempDir.resolve("test-db"));
        service = new ApiPoolService(
                new JdbcKnowledgeBaseProvider(database.connection()),
                new TestEmbeddingProvider()
        );
    }

    @AfterEach
    void tearDown() throws Exception {
        service.close();
        database.close();
    }

    @Test
    void publishSearchGetAndGraphPreserveStructuredApiData() throws Exception {
        Map<String, Object> published = service.publish(invoiceApi("v1", "DEVELOPING"));
        assertTrue((Boolean) published.get("ok"));

        Map<String, Object> search = service.search(Map.of(
                "query", "create payable invoice for accepted order",
                "limit", 10
        ));
        @SuppressWarnings("unchecked")
        List<Map<String, Object>> results = (List<Map<String, Object>>) search.get("results");
        assertEquals(1, results.size());
        assertEquals("billing/invoice/createInvoice", results.get(0).get("api_id"));
        assertEquals("coordinate before creating a duplicate", results.get(0).get("reuse_guidance"));
        assertTrue((Boolean) search.get("semantic_search"));

        Map<String, Object> fetched = service.get("billing/invoice/createInvoice", "v1");
        @SuppressWarnings("unchecked")
        Map<String, Object> api = (Map<String, Object>) fetched.get("api");
        assertEquals("POST /invoices", api.get("signature"));
        assertEquals(1, ((List<?>) api.get("inputs")).size());
        assertEquals(1, ((List<?>) api.get("outputs")).size());
        assertEquals(1, ((List<?>) api.get("errors")).size());
        assertEquals(1, ((List<?>) api.get("relations")).size());
        assertEquals(TestEmbeddingProvider.MODEL, api.get("embedding_model"));

        Map<String, Object> graphResponse = service.graph("billing");
        @SuppressWarnings("unchecked")
        Map<String, Object> graph = (Map<String, Object>) graphResponse.get("graph");
        assertEquals(1, ((List<?>) graph.get("modules")).size());
        assertEquals(1, ((List<?>) graph.get("apis")).size());
        assertEquals(1, ((List<?>) graph.get("relations")).size());
    }

    @Test
    void releasedContractIsImmutableAndRequiresNewVersion() throws Exception {
        service.publish(invoiceApi("v1", "DEVELOPING"));
        service.transition(
                "billing/invoice/createInvoice",
                Map.of("version", "v1", "status", "RELEASED", "actor", "will")
        );

        Map<String, Object> changed = invoiceApi("v1", "RELEASED");
        changed.put("capability", "Create or replace any invoice");
        assertThrows(IllegalStateException.class, () -> service.publish(changed));

        Map<String, Object> v2 = invoiceApi("v2", "DEVELOPING");
        v2.put("capability", "Create an invoice with tax details");
        assertTrue((Boolean) service.publish(v2).get("ok"));

        @SuppressWarnings("unchecked")
        Map<String, Object> storedV1 = (Map<String, Object>) service
                .get("billing/invoice/createInvoice", "v1")
                .get("api");
        @SuppressWarnings("unchecked")
        Map<String, Object> storedV2 = (Map<String, Object>) service
                .get("billing/invoice/createInvoice", "v2")
                .get("api");
        assertEquals(
                "Create a payable invoice for an accepted order",
                storedV1.get("capability")
        );
        assertEquals("Create an invoice with tax details", storedV2.get("capability"));
    }

    @Test
    void lifecycleTransitionsAreValidatedAndRetiredApisAreExcluded() throws Exception {
        service.publish(invoiceApi("v1", "DEVELOPING"));
        service.transition(
                "billing/invoice/createInvoice",
                Map.of("version", "v1", "status", "RELEASED", "actor", "will")
        );

        assertThrows(
                IllegalStateException.class,
                () -> service.transition(
                        "billing/invoice/createInvoice",
                        Map.of("version", "v1", "status", "DEVELOPING")
                )
        );

        service.publish(invoiceApi("v2", "DEVELOPING"));
        service.transition(
                "billing/invoice/createInvoice",
                Map.of("version", "v2", "status", "RELEASED", "actor", "will")
        );
        service.transition(
                "billing/invoice/createInvoice",
                Map.of(
                        "version", "v1",
                        "status", "SUPERSEDED",
                        "actor", "will",
                        "superseded_by_version", "v2"
                )
        );
        service.transition(
                "billing/invoice/createInvoice",
                Map.of("version", "v1", "status", "RETIRED", "actor", "will")
        );

        Map<String, Object> search = service.search(Map.of("query", "invoice"));
        @SuppressWarnings("unchecked")
        List<Map<String, Object>> results = (List<Map<String, Object>>) search.get("results");
        assertFalse(results.isEmpty());
        assertTrue(results.stream().noneMatch(row -> "v1".equals(row.get("version"))));

        Map<String, Object> fetched = service.get("billing/invoice/createInvoice", "v1");
        @SuppressWarnings("unchecked")
        Map<String, Object> api = (Map<String, Object>) fetched.get("api");
        assertEquals("RETIRED", api.get("status"));
        assertEquals(4, ((List<?>) api.get("lifecycle_events")).size());
    }

    @Test
    void releasedApisRankAboveDevelopingApisForEquivalentMatches() throws Exception {
        service.publish(invoiceApi("v1", "DEVELOPING"));

        Map<String, Object> released = invoiceApi("v2", "DEVELOPING");
        service.publish(released);
        service.transition(
                "billing/invoice/createInvoice",
                Map.of("version", "v2", "status", "RELEASED")
        );

        Map<String, Object> search = service.search(Map.of("query", "create invoice"));
        @SuppressWarnings("unchecked")
        List<Map<String, Object>> results = (List<Map<String, Object>>) search.get("results");
        assertEquals("v2", results.get(0).get("version"));
        assertEquals("RELEASED", results.get(0).get("status"));
    }

    @Test
    void definitionValidationRejectsMissingDiscoverySemantics() {
        Map<String, Object> invalid = new LinkedHashMap<>(invoiceApi("v1", "DEVELOPING"));
        invalid.remove("capability");
        assertThrows(IllegalArgumentException.class, () -> service.publish(invalid));
    }

    @Test
    void apiIdCannotBeClaimedByAnotherSourceRepository() throws Exception {
        service.publish(invoiceApi("v1", "DEVELOPING"));
        Map<String, Object> poisoned = invoiceApi("v2", "DEVELOPING");
        @SuppressWarnings("unchecked")
        Map<String, Object> source = new LinkedHashMap<>(
                (Map<String, Object>) poisoned.get("source")
        );
        source.put("repo", "github.com/attacker/fake-billing");
        poisoned.put("source", source);

        IllegalStateException error = assertThrows(
                IllegalStateException.class,
                () -> service.publish(poisoned)
        );
        assertTrue(error.getMessage().contains("different source repository"));
    }

    @Test
    void dirtySourceRevisionCannotBeReleased() throws Exception {
        Map<String, Object> developing = invoiceApi("v1", "DEVELOPING");
        @SuppressWarnings("unchecked")
        Map<String, Object> source = new LinkedHashMap<>(
                (Map<String, Object>) developing.get("source")
        );
        source.put("commit", "abc123+dirty");
        developing.put("source", source);
        service.publish(developing);

        IllegalStateException error = assertThrows(
                IllegalStateException.class,
                () -> service.transition(
                        "billing/invoice/createInvoice",
                        Map.of("version", "v1", "status", "RELEASED")
                )
        );
        assertTrue(error.getMessage().contains("committed source revision"));
    }

    @Test
    void releasedVersionCannotBeRepublishedFromDirtySource() throws Exception {
        service.publish(invoiceApi("v1", "DEVELOPING"));
        service.transition(
                "billing/invoice/createInvoice",
                Map.of("version", "v1", "status", "RELEASED")
        );
        Map<String, Object> dirty = invoiceApi("v1", "RELEASED");
        @SuppressWarnings("unchecked")
        Map<String, Object> source = new LinkedHashMap<>(
                (Map<String, Object>) dirty.get("source")
        );
        source.put("commit", "abc123+dirty");
        dirty.put("source", source);

        assertThrows(IllegalStateException.class, () -> service.publish(dirty));
    }

    @Test
    void applicationGraphContextReranksWithoutRestrictingGlobalRecall() throws Exception {
        service.publish(invoiceApi("v1", "DEVELOPING"));
        Map<String, Object> external = invoiceApi("v1", "DEVELOPING");
        external.put("api_id", "commerce/invoice/createInvoice");
        external.put("system", "commerce");
        external.put("module", "invoice");
        @SuppressWarnings("unchecked")
        Map<String, Object> source = new LinkedHashMap<>(
                (Map<String, Object>) external.get("source")
        );
        source.put("repo", "github.com/acme/commerce");
        external.put("source", source);
        service.publish(external);

        Map<String, Object> search = service.search(Map.of(
                "query", "create payable invoice",
                "filters", Map.of(
                        "context_system", "billing",
                        "context_module", "invoice"
                )
        ));
        @SuppressWarnings("unchecked")
        List<Map<String, Object>> results = (List<Map<String, Object>>) search.get("results");
        assertEquals(2, results.size());
        assertEquals("billing/invoice/createInvoice", results.get(0).get("api_id"));
        assertEquals(0.25, ((Number) results.get(0).get("context_score")).doubleValue(), 0.0001);
        assertEquals("commerce/invoice/createInvoice", results.get(1).get("api_id"));
    }

    @Test
    void embeddingOutageDoesNotLoseRelationalApiReservation() throws Exception {
        ApiPoolService degraded = new ApiPoolService(
                new JdbcKnowledgeBaseProvider(database.connection()),
                new EmbeddingProvider() {
                    @Override
                    public float[] embed(String text) {
                        throw new IllegalStateException("embedding offline");
                    }

                    @Override
                    public String model() {
                        return HttpBgeEmbeddingProvider.DEFAULT_MODEL;
                    }

                    @Override
                    public int dimensions() {
                        return 384;
                    }
                }
        );

        Map<String, Object> result = degraded.publish(invoiceApi("v1", "DEVELOPING"));
        assertTrue((Boolean) result.get("ok"));
        assertTrue(String.valueOf(result.get("warning")).contains("without embedding"));
        Map<String, Object> fetched = degraded.get("billing/invoice/createInvoice", "v1");
        @SuppressWarnings("unchecked")
        Map<String, Object> api = (Map<String, Object>) fetched.get("api");
        assertEquals(0, api.get("embedding_dimensions"));
    }

    @Test
    void publishCannotBypassLifecycleTransitions() throws Exception {
        assertThrows(
                IllegalStateException.class,
                () -> service.publish(invoiceApi("v1", "RELEASED"))
        );

        service.publish(invoiceApi("v1", "DEVELOPING"));
        Map<String, Object> bypass = invoiceApi("v1", "SUPERSEDED");
        IllegalStateException error = assertThrows(
                IllegalStateException.class,
                () -> service.publish(bypass)
        );
        assertTrue(error.getMessage().contains("transition endpoint"));
    }

    @Test
    void supersededRequiresAnExistingReleasedSuccessor() throws Exception {
        service.publish(invoiceApi("v1", "DEVELOPING"));
        service.transition(
                "billing/invoice/createInvoice",
                Map.of("version", "v1", "status", "RELEASED")
        );

        assertThrows(
                IllegalArgumentException.class,
                () -> service.transition(
                        "billing/invoice/createInvoice",
                        Map.of("version", "v1", "status", "SUPERSEDED")
                )
        );
        assertThrows(
                IllegalStateException.class,
                () -> service.transition(
                        "billing/invoice/createInvoice",
                        Map.of(
                                "version", "v1",
                                "status", "SUPERSEDED",
                                "superseded_by_version", "v2"
                        )
                )
        );

        service.publish(invoiceApi("v2", "DEVELOPING"));
        assertThrows(
                IllegalStateException.class,
                () -> service.transition(
                        "billing/invoice/createInvoice",
                        Map.of(
                                "version", "v1",
                                "status", "SUPERSEDED",
                                "superseded_by_version", "v2"
                        )
                )
        );
    }

    @Test
    void resyncReembedsOnlyWhenSemanticContentOrModelChanges() throws Exception {
        RecordingEmbeddingProvider recording = new RecordingEmbeddingProvider();
        ApiPoolService tracked = new ApiPoolService(
                new JdbcKnowledgeBaseProvider(database.connection()),
                recording
        );

        Map<String, Object> first = tracked.publish(invoiceApi("v1", "DEVELOPING"));
        assertEquals(1, recording.calls);
        assertEquals(true, first.get("embedding_updated"));
        @SuppressWarnings("unchecked")
        Map<String, Object> firstApi = (Map<String, Object>) first.get("api");
        String firstHash = String.valueOf(firstApi.get("content_hash"));

        Map<String, Object> sourceOnly = invoiceApi("v1", "DEVELOPING");
        @SuppressWarnings("unchecked")
        Map<String, Object> source = new LinkedHashMap<>(
                (Map<String, Object>) sourceOnly.get("source")
        );
        source.put("commit", "def456");
        sourceOnly.put("source", source);
        Map<String, Object> second = tracked.publish(sourceOnly);
        assertEquals(1, recording.calls);
        assertEquals(false, second.get("embedding_updated"));
        @SuppressWarnings("unchecked")
        Map<String, Object> secondApi = (Map<String, Object>) second.get("api");
        assertEquals(4, secondApi.get("embedding_dimensions"));
        assertEquals(firstHash, secondApi.get("content_hash"));

        Map<String, Object> semanticChange = new LinkedHashMap<>(sourceOnly);
        semanticChange.put("capability", "Create an invoice including tax details");
        Map<String, Object> third = tracked.publish(semanticChange);
        assertEquals(2, recording.calls);
        assertEquals(true, third.get("embedding_updated"));
        @SuppressWarnings("unchecked")
        Map<String, Object> thirdApi = (Map<String, Object>) third.get("api");
        String updatedHash = String.valueOf(thirdApi.get("content_hash"));
        assertFalse(firstHash.equals(updatedHash));
        try (java.sql.PreparedStatement ps = database.connection().prepareStatement(
                "SELECT COUNT(*) FROM api_versions WHERE api_id = ? AND version = ?"
        )) {
            ps.setString(1, "billing/invoice/createInvoice");
            ps.setString(2, "v1");
            try (java.sql.ResultSet rs = ps.executeQuery()) {
                rs.next();
                assertEquals(1, rs.getInt(1));
            }
        }

        tracked.transition(
                "billing/invoice/createInvoice",
                Map.of("version", "v1", "status", "RELEASED")
        );
        assertEquals(2, recording.calls);
        @SuppressWarnings("unchecked")
        Map<String, Object> released = (Map<String, Object>) tracked
                .get("billing/invoice/createInvoice", "v1")
                .get("api");
        assertEquals(updatedHash, released.get("content_hash"));
    }

    @Test
    void searchEmbeddingOutageFallsBackToLexicalSearch() throws Exception {
        service.publish(invoiceApi("v1", "DEVELOPING"));
        ApiPoolService degraded = new ApiPoolService(
                new JdbcKnowledgeBaseProvider(database.connection()),
                new FailingEmbeddingProvider()
        );
        Map<String, Object> result = degraded.search(Map.of("query", "payable invoice"));
        assertEquals(false, result.get("semantic_search"));
        assertTrue(String.valueOf(result.get("warning")).contains("lexical search"));
        assertEquals(1, ((List<?>) result.get("results")).size());
    }

    @Test
    void bgeQueryInstructionIsAppliedOnlyToSearchQueries() throws Exception {
        RecordingEmbeddingProvider recording = new RecordingEmbeddingProvider();
        ApiPoolService tracked = new ApiPoolService(
                new JdbcKnowledgeBaseProvider(database.connection()),
                recording
        );
        tracked.publish(invoiceApi("v1", "DEVELOPING"));
        assertFalse(recording.texts.get(0).startsWith(EmbeddingProvider.BGE_QUERY_PREFIX));

        tracked.search(Map.of("query", "find invoice API"));
        assertTrue(recording.texts.get(1).startsWith(EmbeddingProvider.BGE_QUERY_PREFIX));
    }

    @Test
    void semanticSimilarityRanksEqualLifecycleVersions() throws Exception {
        JdbcKnowledgeBaseProvider provider =
                new JdbcKnowledgeBaseProvider(database.connection());
        Map<String, Object> firstMap = invoiceApi("v1", "DEVELOPING");
        firstMap.put("capability", "Synthetic capability alpha");
        ApiDefinition first = ApiDefinition.fromMap(firstMap);
        Map<String, Object> secondMap = invoiceApi("v2", "DEVELOPING");
        secondMap.put("capability", "Synthetic capability beta");
        ApiDefinition second = ApiDefinition.fromMap(secondMap);
        provider.upsert(first, new float[]{1, 0}, "test-2", first.contentHash(), true);
        provider.upsert(second, new float[]{0, 1}, "test-2", second.contentHash(), true);

        List<Map<String, Object>> results = provider.search(
                "needle",
                new float[]{1, 0},
                Map.of("system", "billing"),
                10
        );
        assertEquals("v1", results.get(0).get("version"));
        assertEquals(
                1.0,
                ((Number) results.get(0).get("semantic_score")).doubleValue(),
                0.0001
        );
    }

    @Test
    @SuppressWarnings("unchecked")
    void verifyReturnsSyncedStaleMissingAndConflictStates() throws Exception {
        service.publish(invoiceApi("v1", "DEVELOPING"));
        Map<String, Object> local = invoiceApi("v1", "DEVELOPING");
        local.put("content_hash", ApiDefinition.fromMap(local).contentHash());

        Map<String, Object> synced = service.verify(Map.of("apis", List.of(local)));
        assertTrue((Boolean) synced.get("ok"));
        assertEquals(1, ((Map<?, ?>) synced.get("counts")).get("SYNCED"));

        Map<String, Object> staleApi = new LinkedHashMap<>(local);
        staleApi.put("capability", "Create a different invoice");
        staleApi.put("content_hash", ApiDefinition.fromMap(staleApi).contentHash());
        Map<String, Object> stale = service.verify(Map.of("apis", List.of(staleApi)));
        assertEquals(
                "STALE",
                ((List<Map<String, Object>>) stale.get("states")).get(0).get("state")
        );

        Map<String, Object> missingApi = new LinkedHashMap<>(local);
        missingApi.put("api_id", "billing/invoice/missing");
        Map<String, Object> missing = service.verify(Map.of("apis", List.of(missingApi)));
        assertEquals(
                "MISSING",
                ((List<Map<String, Object>>) missing.get("states")).get(0).get("state")
        );

        Map<String, Object> conflictApi = new LinkedHashMap<>(local);
        conflictApi.put("source", Map.of(
                "repo", "github.com/other/billing",
                "path", "cdase/api/modules/invoice.api.md",
                "commit", "abc123",
                "owner", "billing-team"
        ));
        Map<String, Object> conflict = service.verify(Map.of("apis", List.of(conflictApi)));
        assertEquals(
                "CONFLICT",
                ((List<Map<String, Object>>) conflict.get("states")).get(0).get("state")
        );
    }

    @Test
    void legacyImportProvenanceIsValidatedAndStoredOutsideSemanticHash() throws Exception {
        Map<String, Object> legacy = invoiceApi("v1", "DEVELOPING");
        String nativeHash = ApiDefinition.fromMap(legacy).contentHash();
        legacy.put("origin", "LEGACY_IMPORT");
        legacy.put("discovery_confidence", "HIGH");
        legacy.put("scan_id", "legacy-scan-1");
        legacy.put("approval_ref", "cdase/run_log/approval.json");
        legacy.put("discovery_evidence", List.of(Map.of(
                "kind", "http_route",
                "path", "src/BillingController.java",
                "line", 42,
                "symbol", "POST /invoices",
                "detail", "Explicit route"
        )));

        assertEquals(nativeHash, ApiDefinition.fromMap(legacy).contentHash());
        service.publish(legacy);
        @SuppressWarnings("unchecked")
        Map<String, Object> stored = (Map<String, Object>) service
                .get("billing/invoice/createInvoice", "v1")
                .get("api");
        assertEquals("LEGACY_IMPORT", stored.get("origin"));
        assertEquals("HIGH", stored.get("discovery_confidence"));
        assertEquals(1, ((List<?>) stored.get("discovery_evidence")).size());

        Map<String, Object> invalid = invoiceApi("v2", "DEVELOPING");
        invalid.put("origin", "LEGACY_IMPORT");
        assertThrows(IllegalArgumentException.class, () -> service.publish(invalid));
    }

    private static Map<String, Object> invoiceApi(String version, String status) {
        Map<String, Object> api = new LinkedHashMap<>();
        api.put("api_id", "billing/invoice/createInvoice");
        api.put("system", "billing");
        api.put("module", "invoice");
        api.put("name", "createInvoice");
        api.put("kind", "REST");
        api.put("version", version);
        api.put("status", status);
        api.put("capability", "Create a payable invoice for an accepted order");
        api.put("use_when", List.of("An order has passed validation"));
        api.put("do_not_use_when", List.of("Creating a draft quotation"));
        api.put("signature", "POST /invoices");
        api.put("inputs", List.of(Map.of(
                "name", "orderId",
                "type", "string",
                "description", "Accepted order identifier",
                "required", true
        )));
        api.put("outputs", List.of(Map.of(
                "name", "invoiceId",
                "type", "string",
                "description", "Created invoice identifier",
                "required", true
        )));
        api.put("errors", List.of(Map.of(
                "code", "ORDER_NOT_FOUND",
                "description", "Order does not exist"
        )));
        api.put("side_effects", List.of("Persists invoice", "Emits InvoiceCreated"));
        api.put("auth", "billing.invoice.write");
        api.put("idempotency", "By orderId");
        api.put("source", Map.of(
                "repo", "github.com/acme/billing",
                "path", "cdase/api/modules/invoice.api.md",
                "commit", "abc123",
                "owner", "billing-team"
        ));
        api.put("relations", List.of(Map.of(
                "type", "DEPENDS_ON",
                "target_api_id", "orders/order/getOrder",
                "target_version", "v1"
        )));
        return api;
    }

    private static final class TestEmbeddingProvider implements EmbeddingProvider {
        private static final String MODEL = "test-embedding-4";

        @Override
        public float[] embed(String text) {
            float[] vector = new float[4];
            for (String word : text.toLowerCase().split("\\W+")) {
                vector[Math.floorMod(word.hashCode(), vector.length)] += 1;
            }
            return VectorMath.normalize(vector);
        }

        @Override
        public String model() {
            return MODEL;
        }

        @Override
        public int dimensions() {
            return 4;
        }
    }

    private static final class RecordingEmbeddingProvider implements EmbeddingProvider {
        private int calls;
        private final List<String> texts = new ArrayList<>();

        @Override
        public float[] embed(String text) {
            calls++;
            texts.add(text);
            return VectorMath.normalize(new float[]{
                    text.length(),
                    text.contains("invoice") ? 1 : 0,
                    text.contains("tax") ? 1 : 0,
                    1
            });
        }

        @Override
        public String model() {
            return "recording-model";
        }

        @Override
        public int dimensions() {
            return 4;
        }
    }

    private static final class FailingEmbeddingProvider implements EmbeddingProvider {
        @Override
        public float[] embed(String text) {
            throw new IllegalStateException("embedding offline");
        }

        @Override
        public String model() {
            return HttpBgeEmbeddingProvider.DEFAULT_MODEL;
        }

        @Override
        public int dimensions() {
            return 384;
        }
    }
}
