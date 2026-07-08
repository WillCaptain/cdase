package com.cdase.hub.db;

import java.io.IOException;
import java.io.InputStream;
import java.nio.charset.StandardCharsets;
import java.nio.file.Path;
import java.sql.Connection;
import java.sql.DriverManager;
import java.sql.SQLException;
import java.sql.Statement;

public final class Database implements AutoCloseable {

    private final Connection connection;

    public Database(Path dbFile) throws SQLException, IOException {
        String url = "jdbc:h2:" + dbFile.toAbsolutePath() + ";DATABASE_TO_LOWER=TRUE";
        connection = DriverManager.getConnection(url, "sa", "");
        initSchema();
    }

    private void initSchema() throws IOException, SQLException {
        String sql;
        try (InputStream in = getClass().getClassLoader().getResourceAsStream("schema.sql")) {
            if (in == null) {
                throw new IOException("schema.sql not found on classpath");
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

    public Connection connection() {
        return connection;
    }

    @Override
    public void close() throws SQLException {
        connection.close();
    }
}
