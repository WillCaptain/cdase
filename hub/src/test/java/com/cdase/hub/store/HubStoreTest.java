package com.cdase.hub.store;

import com.cdase.hub.db.Database;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

import java.nio.file.Files;
import java.nio.file.Path;
import java.util.List;
import java.util.Map;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

class HubStoreTest {

    private static final String ALICE = "a1b2c3d4";
    private static final String BOB = "b2c3d4e5";
    private static final String STRANGER = "deadbeef";

    private Path tempDir;
    private Database database;
    private HubStore store;

    @BeforeEach
    void setUp() throws Exception {
        tempDir = Files.createTempDirectory("cdase-hub-test");
        database = new Database(tempDir.resolve("test-db"));
        store = new HubStore(database);
    }

    @AfterEach
    void tearDown() throws Exception {
        database.close();
    }

    @Test
    void inboxOnlyReturnsMessagesFromTrustedUuids() throws Exception {
        store.login(ALICE, "alice", "m1", Map.of());
        store.login(BOB, "bob", "m2", Map.of());

        store.sendMessage(ALICE, BOB, "alice", "bob", "trusted hello", "message",
                null, "human", "message", null);
        store.sendMessage(STRANGER, BOB, "impostor", "bob", "spoof attempt", "message",
                null, "human", "message", null);

        List<Map<String, Object>> inbox = store.getMessages(BOB, List.of(ALICE), false);
        assertEquals(1, inbox.size());
        assertEquals("trusted hello", inbox.get(0).get("body"));
        assertEquals(ALICE, inbox.get(0).get("from_uuid"));
    }

    @Test
    void unreadCountRespectsTrustFilter() throws Exception {
        store.login(BOB, "bob", "m2", Map.of());
        store.sendMessage(ALICE, BOB, "alice", "bob", "one", "message", null, "human", "message", null);
        store.sendMessage(STRANGER, BOB, "x", "bob", "two", "message", null, "human", "message", null);

        assertEquals(1, store.countUnread(BOB, List.of(ALICE)));
        assertEquals(0, store.countUnread(BOB, List.of()));
    }

    @Test
    void loginAndPingByUuid() throws Exception {
        store.login(ALICE, "alice", "m1", Map.of("role", "lead"));
        assertTrue(store.ping(ALICE, "m1") != null);
        assertEquals(1, store.listUsers().size());
        assertEquals("alice", store.listUsers().get(0).get("name"));
    }
}
