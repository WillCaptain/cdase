package com.cdase.hub.store;

import com.cdase.hub.db.Database;

import java.sql.PreparedStatement;
import java.sql.ResultSet;
import java.sql.SQLException;
import java.sql.Timestamp;
import java.time.Instant;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Set;
import java.util.UUID;
import java.util.regex.Pattern;
import java.util.stream.Collectors;

public final class HubStore {

    public static final int ACTIVE_WINDOW_SECONDS = 180;

    private static final Pattern SLUG_SAFE = Pattern.compile("[^a-z0-9_-]+");

    private final Database database;

    public HubStore(Database database) {
        this.database = database;
    }

    public Map<String, Object> login(String userUuid, String name, String machineId, Map<String, String> extra)
            throws SQLException {
        return login(userUuid, name, machineId, null, extra);
    }

    public Map<String, Object> login(String userUuid, String name, String machineId, String repoId,
                                     Map<String, String> extra) throws SQLException {
        upsertUser(userUuid, name, extra);
        touchMachine(userUuid, machineId);
        if (repoId != null && !repoId.isBlank()) {
            touchProjectSession(userUuid, repoId, machineId);
        }
        return loadUser(userUuid);
    }

    public Map<String, Object> ping(String userUuid, String machineId) throws SQLException {
        return ping(userUuid, machineId, null);
    }

    public Map<String, Object> ping(String userUuid, String machineId, String repoId) throws SQLException {
        if (loadUser(userUuid).isEmpty()) {
            return null;
        }
        touchMachine(userUuid, machineId);
        if (repoId != null && !repoId.isBlank()) {
            touchProjectSession(userUuid, repoId, machineId);
        }
        return loadUser(userUuid);
    }

    public List<Map<String, Object>> listUsers() throws SQLException {
        return listUsers(null);
    }

    public List<Map<String, Object>> listUsers(String repoId) throws SQLException {
        if (repoId == null || repoId.isBlank()) {
            return listUsersGlobal();
        }
        return listUsersForProject(repoId);
    }

    private List<Map<String, Object>> listUsersGlobal() throws SQLException {
        String sql = """
                SELECT u.user_uuid, u.name, u.role, u.team, u.organization,
                       m.machine_id, m.last_seen
                FROM users u
                LEFT JOIN machines m ON m.user_uuid = u.user_uuid
                ORDER BY u.name, m.last_seen DESC
                """;
        Map<String, Map<String, Object>> grouped = new LinkedHashMap<>();
        Instant now = Instant.now();

        try (PreparedStatement ps = database.connection().prepareStatement(sql);
             ResultSet rs = ps.executeQuery()) {
            while (rs.next()) {
                String userUuid = rs.getString("user_uuid");
                Map<String, Object> row = grouped.computeIfAbsent(userUuid, id -> {
                    Map<String, Object> u = new LinkedHashMap<>();
                    u.put("uuid", id);
                    u.put("name", null);
                    u.put("role", null);
                    u.put("team", null);
                    u.put("machines", new ArrayList<String>());
                    u.put("last_seen", 0.0);
                    u.put("active", false);
                    return u;
                });
                row.put("name", rs.getString("name"));
                row.put("role", rs.getString("role"));
                row.put("team", rs.getString("team"));
                String machineId = rs.getString("machine_id");
                if (machineId != null) {
                    @SuppressWarnings("unchecked")
                    List<String> machines = (List<String>) row.get("machines");
                    if (!machines.contains(machineId)) {
                        machines.add(machineId);
                    }
                    Timestamp lastSeen = rs.getTimestamp("last_seen");
                    Instant seenInstant = lastSeen.toInstant();
                    double seen = epochSeconds(seenInstant);
                    double current = (double) row.get("last_seen");
                    if (seen > current) {
                        row.put("last_seen", seen);
                        row.put("active", now.getEpochSecond() - seenInstant.getEpochSecond() < ACTIVE_WINDOW_SECONDS);
                    }
                }
            }
        }

        List<Map<String, Object>> users = new ArrayList<>(grouped.values());
        users.sort(Comparator.comparingDouble(u -> -((Number) u.get("last_seen")).doubleValue()));
        return users;
    }

    private List<Map<String, Object>> listUsersForProject(String repoId) throws SQLException {
        String sql = """
                SELECT u.user_uuid, u.name, u.role, u.team, u.organization,
                       ps.machine_id, ps.last_seen
                FROM project_sessions ps
                JOIN users u ON u.user_uuid = ps.user_uuid
                WHERE ps.repo_id = ?
                ORDER BY u.name, ps.last_seen DESC
                """;
        Map<String, Map<String, Object>> grouped = new LinkedHashMap<>();
        Instant now = Instant.now();

        try (PreparedStatement ps = database.connection().prepareStatement(sql)) {
            ps.setString(1, repoId);
            try (ResultSet rs = ps.executeQuery()) {
                while (rs.next()) {
                    String userUuid = rs.getString("user_uuid");
                    Map<String, Object> row = grouped.computeIfAbsent(userUuid, id -> {
                        Map<String, Object> u = new LinkedHashMap<>();
                        u.put("uuid", id);
                        u.put("name", null);
                        u.put("role", null);
                        u.put("team", null);
                        u.put("machines", new ArrayList<String>());
                        u.put("last_seen", 0.0);
                        u.put("active", false);
                        u.put("repo_id", repoId);
                        return u;
                    });
                    row.put("name", rs.getString("name"));
                    row.put("role", rs.getString("role"));
                    row.put("team", rs.getString("team"));
                    String machineId = rs.getString("machine_id");
                    if (machineId != null) {
                        @SuppressWarnings("unchecked")
                        List<String> machines = (List<String>) row.get("machines");
                        if (!machines.contains(machineId)) {
                            machines.add(machineId);
                        }
                        Timestamp lastSeen = rs.getTimestamp("last_seen");
                        Instant seenInstant = lastSeen.toInstant();
                        double seen = epochSeconds(seenInstant);
                        double current = (double) row.get("last_seen");
                        if (seen > current) {
                            row.put("last_seen", seen);
                            row.put("active", now.getEpochSecond() - seenInstant.getEpochSecond()
                                    < ACTIVE_WINDOW_SECONDS);
                        }
                    }
                }
            }
        }

        List<Map<String, Object>> users = new ArrayList<>(grouped.values());
        users.sort(Comparator.comparingDouble(u -> -((Number) u.get("last_seen")).doubleValue()));
        return users;
    }

    public Map<String, Object> sendMessage(String fromUuid, String toUuid, String fromName, String toName,
                                           String body, String type, String subject, String actor,
                                           String intent, String threadId) throws SQLException {
        String id = UUID.randomUUID().toString().replace("-", "").substring(0, 12);
        String msgType = "task".equals(type) ? "task" : "message";
        String fromActor = "agent".equals(actor) ? "agent" : "human";
        String msgIntent = intent != null && !intent.isBlank() ? intent : msgType;
        Instant now = Instant.now();

        String sql = """
                INSERT INTO messages (id, from_uuid, to_uuid, from_name, to_name, from_actor, msg_type,
                                      intent, thread_id, subject, body, sent_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """;
        try (PreparedStatement ps = database.connection().prepareStatement(sql)) {
            ps.setString(1, id);
            ps.setString(2, fromUuid);
            ps.setString(3, toUuid);
            ps.setString(4, fromName);
            ps.setString(5, toName);
            ps.setString(6, fromActor);
            ps.setString(7, msgType);
            ps.setString(8, msgIntent);
            ps.setString(9, threadId);
            ps.setString(10, subject);
            ps.setString(11, body);
            ps.setTimestamp(12, Timestamp.from(now));
            ps.executeUpdate();
        }

        return messageRow(id, fromUuid, toUuid, fromName, toName, fromActor, msgType, msgIntent,
                threadId, subject, body, now, null);
    }

    public List<Map<String, Object>> getMessages(String toUuid, List<String> trustUuids, boolean includeRead)
            throws SQLException {
        if (trustUuids == null || trustUuids.isEmpty()) {
            return List.of();
        }
        String trustPlaceholders = trustUuids.stream().map(u -> "?").collect(Collectors.joining(","));
        String readClause = includeRead ? "" : " AND read_at IS NULL";
        String sql = "SELECT * FROM messages WHERE to_uuid = ? AND from_uuid IN (" + trustPlaceholders + ")"
                + readClause + " ORDER BY sent_at";

        List<Map<String, Object>> out = new ArrayList<>();
        try (PreparedStatement ps = database.connection().prepareStatement(sql)) {
            ps.setString(1, toUuid);
            for (int i = 0; i < trustUuids.size(); i++) {
                ps.setString(i + 2, trustUuids.get(i));
            }
            try (ResultSet rs = ps.executeQuery()) {
                while (rs.next()) {
                    out.add(readMessage(rs));
                }
            }
        }
        return out;
    }

    /** All messages to recipient — client applies repo roster trust filter. */
    public List<Map<String, Object>> getAllMessages(String toUuid, boolean includeRead) throws SQLException {
        String readClause = includeRead ? "" : " AND read_at IS NULL";
        String sql = "SELECT * FROM messages WHERE to_uuid = ?" + readClause + " ORDER BY sent_at";
        List<Map<String, Object>> out = new ArrayList<>();
        try (PreparedStatement ps = database.connection().prepareStatement(sql)) {
            ps.setString(1, toUuid);
            try (ResultSet rs = ps.executeQuery()) {
                while (rs.next()) {
                    out.add(readMessage(rs));
                }
            }
        }
        return out;
    }

    public int countAllUnread(String toUuid) throws SQLException {
        String sql = "SELECT COUNT(*) FROM messages WHERE to_uuid = ? AND read_at IS NULL";
        try (PreparedStatement ps = database.connection().prepareStatement(sql)) {
            ps.setString(1, toUuid);
            try (ResultSet rs = ps.executeQuery()) {
                rs.next();
                return rs.getInt(1);
            }
        }
    }

    public int countUnread(String toUuid, List<String> trustUuids) throws SQLException {
        if (trustUuids == null || trustUuids.isEmpty()) {
            return 0;
        }
        String trustPlaceholders = trustUuids.stream().map(u -> "?").collect(Collectors.joining(","));
        String sql = "SELECT COUNT(*) FROM messages WHERE to_uuid = ? AND read_at IS NULL AND from_uuid IN ("
                + trustPlaceholders + ")";
        try (PreparedStatement ps = database.connection().prepareStatement(sql)) {
            ps.setString(1, toUuid);
            for (int i = 0; i < trustUuids.size(); i++) {
                ps.setString(i + 2, trustUuids.get(i));
            }
            try (ResultSet rs = ps.executeQuery()) {
                rs.next();
                return rs.getInt(1);
            }
        }
    }

    public int ackMessages(String toUuid, List<String> ids) throws SQLException {
        if (ids == null || ids.isEmpty()) {
            return 0;
        }
        String placeholders = String.join(",", ids.stream().map(id -> "?").toList());
        String sql = "UPDATE messages SET read_at = ? WHERE to_uuid = ? AND read_at IS NULL AND id IN ("
                + placeholders + ")";
        try (PreparedStatement ps = database.connection().prepareStatement(sql)) {
            ps.setTimestamp(1, Timestamp.from(Instant.now()));
            ps.setString(2, toUuid);
            for (int i = 0; i < ids.size(); i++) {
                ps.setString(i + 3, ids.get(i));
            }
            return ps.executeUpdate();
        }
    }

    public Map<String, Object> kbSave(String key, String content, List<String> tags, String author)
            throws SQLException {
        String slug = slugify(key);
        String tagsCsv = tags == null ? "" : String.join(",", tags);
        Instant now = Instant.now();
        String sql = """
                MERGE INTO kb_entries (slug, entry_key, content, tags, author, updated_at) KEY(slug)
                VALUES (?, ?, ?, ?, ?, ?)
                """;
        try (PreparedStatement ps = database.connection().prepareStatement(sql)) {
            ps.setString(1, slug);
            ps.setString(2, key);
            ps.setString(3, content);
            ps.setString(4, tagsCsv);
            ps.setString(5, author);
            ps.setTimestamp(6, Timestamp.from(now));
            ps.executeUpdate();
        }
        Map<String, Object> entry = new LinkedHashMap<>();
        entry.put("key", key);
        entry.put("slug", slug);
        entry.put("content", content);
        entry.put("tags", tags == null ? List.of() : tags);
        entry.put("author", author);
        entry.put("updated_at", epochSeconds(now));
        return entry;
    }

    public List<Map<String, Object>> kbSearch(String query) throws SQLException {
        List<String> words = Pattern.compile("\\W+").splitAsStream(query.toLowerCase(Locale.ROOT))
                .filter(w -> !w.isBlank())
                .toList();

        String sql = "SELECT slug, entry_key, content, tags, author, updated_at FROM kb_entries";
        List<Map.Entry<Integer, Map<String, Object>>> scored = new ArrayList<>();

        try (PreparedStatement ps = database.connection().prepareStatement(sql);
             ResultSet rs = ps.executeQuery()) {
            while (rs.next()) {
                Map<String, Object> entry = kbRow(rs);
                String haystack = (entry.get("key") + " " + entry.get("content") + " "
                        + String.join(" ", (List<String>) entry.get("tags"))).toLowerCase(Locale.ROOT);
                int score = 0;
                for (String word : words) {
                    score += countOccurrences(haystack, word);
                }
                if (score > 0 || words.isEmpty()) {
                    scored.add(Map.entry(score, entry));
                }
            }
        }

        scored.sort((a, b) -> Integer.compare(b.getKey(), a.getKey()));
        return scored.stream().limit(20).map(Map.Entry::getValue).toList();
    }

    private void upsertUser(String userUuid, String name, Map<String, String> extra) throws SQLException {
        String role = extra == null ? null : extra.get("role");
        String team = extra == null ? null : extra.get("team");
        String organization = extra == null ? null : extra.get("organization");

        String merge = """
                MERGE INTO users (user_uuid, name, role, team, organization, created_at) KEY(user_uuid)
                VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                """;
        try (PreparedStatement ps = database.connection().prepareStatement(merge)) {
            ps.setString(1, userUuid);
            ps.setString(2, name);
            ps.setString(3, role);
            ps.setString(4, team);
            ps.setString(5, organization);
            ps.executeUpdate();
        }
    }

    private void touchMachine(String userUuid, String machineId) throws SQLException {
        String merge = """
                MERGE INTO machines (user_uuid, machine_id, last_seen) KEY(user_uuid, machine_id)
                VALUES (?, ?, CURRENT_TIMESTAMP)
                """;
        try (PreparedStatement ps = database.connection().prepareStatement(merge)) {
            ps.setString(1, userUuid);
            ps.setString(2, machineId);
            ps.executeUpdate();
        }
    }

    private void touchProjectSession(String userUuid, String repoId, String machineId) throws SQLException {
        String merge = """
                MERGE INTO project_sessions (user_uuid, repo_id, machine_id, last_seen)
                KEY(user_uuid, repo_id, machine_id)
                VALUES (?, ?, ?, CURRENT_TIMESTAMP)
                """;
        try (PreparedStatement ps = database.connection().prepareStatement(merge)) {
            ps.setString(1, userUuid);
            ps.setString(2, repoId);
            ps.setString(3, machineId);
            ps.executeUpdate();
        }
    }

    private Map<String, Object> loadUser(String userUuid) throws SQLException {
        try (PreparedStatement ps = database.connection().prepareStatement("SELECT * FROM users WHERE user_uuid = ?")) {
            ps.setString(1, userUuid);
            try (ResultSet rs = ps.executeQuery()) {
                if (!rs.next()) {
                    return Map.of();
                }
                Map<String, Object> user = new LinkedHashMap<>();
                user.put("uuid", rs.getString("user_uuid"));
                user.put("name", rs.getString("name"));
                user.put("role", rs.getString("role"));
                user.put("team", rs.getString("team"));
                user.put("organization", rs.getString("organization"));
                user.put("created_at", epochSeconds(rs.getTimestamp("created_at").toInstant()));
                return user;
            }
        }
    }

    private Map<String, Object> readMessage(ResultSet rs) throws SQLException {
        Instant sentAt = rs.getTimestamp("sent_at").toInstant();
        Timestamp readAt = rs.getTimestamp("read_at");
        return messageRow(
                rs.getString("id"),
                rs.getString("from_uuid"),
                rs.getString("to_uuid"),
                rs.getString("from_name"),
                rs.getString("to_name"),
                rs.getString("from_actor"),
                rs.getString("msg_type"),
                rs.getString("intent"),
                rs.getString("thread_id"),
                rs.getString("subject"),
                rs.getString("body"),
                sentAt,
                readAt == null ? null : readAt.toInstant()
        );
    }

    private Map<String, Object> messageRow(String id, String fromUuid, String toUuid, String fromName,
                                           String toName, String actor, String type, String intent,
                                           String threadId, String subject, String body,
                                           Instant sentAt, Instant readAt) {
        Map<String, Object> msg = new LinkedHashMap<>();
        msg.put("id", id);
        msg.put("from_uuid", fromUuid);
        msg.put("to_uuid", toUuid);
        msg.put("from", fromName);
        msg.put("to", toName);
        msg.put("from_actor", actor);
        msg.put("type", type);
        msg.put("intent", intent);
        if (threadId != null) {
            msg.put("thread_id", threadId);
        }
        msg.put("subject", subject);
        msg.put("body", body);
        msg.put("sent_at", epochSeconds(sentAt));
        msg.put("read", readAt != null);
        if (readAt != null) {
            msg.put("read_at", epochSeconds(readAt));
        }
        return msg;
    }

    private Map<String, Object> kbRow(ResultSet rs) throws SQLException {
        Map<String, Object> entry = new LinkedHashMap<>();
        entry.put("key", rs.getString("entry_key"));
        entry.put("slug", rs.getString("slug"));
        entry.put("content", rs.getString("content"));
        String tags = rs.getString("tags");
        entry.put("tags", tags == null || tags.isBlank() ? List.of() : List.of(tags.split(",")));
        entry.put("author", rs.getString("author"));
        entry.put("updated_at", epochSeconds(rs.getTimestamp("updated_at").toInstant()));
        return entry;
    }

    private static String slugify(String key) {
        String slug = SLUG_SAFE.matcher(key.toLowerCase(Locale.ROOT)).replaceAll("-").replaceAll("^-|-$", "");
        return slug.isBlank() ? UUID.randomUUID().toString().substring(0, 8) : slug;
    }

    private static double epochSeconds(Instant instant) {
        return instant.getEpochSecond() + instant.getNano() / 1_000_000_000.0;
    }

    private static int countOccurrences(String haystack, String needle) {
        int count = 0;
        int idx = 0;
        while ((idx = haystack.indexOf(needle, idx)) != -1) {
            count++;
            idx += needle.length();
        }
        return count;
    }
}
