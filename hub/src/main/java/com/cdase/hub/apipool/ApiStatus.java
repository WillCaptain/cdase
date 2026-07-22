package com.cdase.hub.apipool;

import java.util.Locale;
import java.util.Set;

public enum ApiStatus {
    DEVELOPING,
    RELEASED,
    SUPERSEDED,
    DEPRECATED,
    RETIRED;

    private static final Set<String> TRANSITIONS = Set.of(
            "DEVELOPING:RELEASED",
            "DEVELOPING:RETIRED",
            "RELEASED:SUPERSEDED",
            "RELEASED:DEPRECATED",
            "RELEASED:RETIRED",
            "SUPERSEDED:DEPRECATED",
            "SUPERSEDED:RETIRED",
            "DEPRECATED:RETIRED"
    );

    public static ApiStatus parse(Object value) {
        if (value == null || String.valueOf(value).isBlank()) {
            return DEVELOPING;
        }
        try {
            return valueOf(String.valueOf(value).trim().toUpperCase(Locale.ROOT));
        } catch (IllegalArgumentException e) {
            throw new IllegalArgumentException(
                    "invalid API status; expected DEVELOPING, RELEASED, SUPERSEDED, DEPRECATED, or RETIRED"
            );
        }
    }

    public boolean canTransitionTo(ApiStatus next) {
        return this == next || TRANSITIONS.contains(name() + ":" + next.name());
    }
}
