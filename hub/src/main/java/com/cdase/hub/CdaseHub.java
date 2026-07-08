package com.cdase.hub;

import com.cdase.hub.db.Database;
import com.cdase.hub.http.HubHttpServer;
import com.cdase.hub.store.HubStore;

import java.nio.file.Path;

public final class CdaseHub {

    public static void main(String[] args) throws Exception {
        String host = "0.0.0.0";
        int port = 7423;
        Path dataDir = Path.of("data");

        for (int i = 0; i < args.length; i++) {
            switch (args[i]) {
                case "--host" -> host = args[++i];
                case "--port" -> port = Integer.parseInt(args[++i]);
                case "--data" -> dataDir = Path.of(args[++i]);
                default -> throw new IllegalArgumentException("Unknown arg: " + args[i]);
            }
        }

        dataDir.toFile().mkdirs();
        Path dbFile = dataDir.resolve("cdase-hub");

        try (Database database = new Database(dbFile)) {
            HubStore store = new HubStore(database);
            HubHttpServer server = new HubHttpServer(host, port, store);
            System.out.printf("CDASE Hub (Java) listening on http://%s:%d  (db: %s.mv.db)%n",
                    host, port, dbFile.toAbsolutePath());
            server.start();
        }
    }

    private CdaseHub() {
    }
}
