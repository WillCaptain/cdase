CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS api_systems (
    system_key  VARCHAR(255) PRIMARY KEY,
    name        VARCHAR(255) NOT NULL,
    description TEXT,
    updated_at  TIMESTAMPTZ NOT NULL
);

CREATE TABLE IF NOT EXISTS api_modules (
    system_key  VARCHAR(255) NOT NULL REFERENCES api_systems(system_key) ON DELETE CASCADE,
    module_key  VARCHAR(255) NOT NULL,
    name        VARCHAR(255) NOT NULL,
    description TEXT,
    updated_at  TIMESTAMPTZ NOT NULL,
    PRIMARY KEY (system_key, module_key)
);

CREATE TABLE IF NOT EXISTS api_operations (
    api_id         VARCHAR(512) PRIMARY KEY,
    system_key     VARCHAR(255) NOT NULL,
    module_key     VARCHAR(255) NOT NULL,
    operation_name VARCHAR(255) NOT NULL,
    api_kind       VARCHAR(64) NOT NULL,
    capability     TEXT NOT NULL,
    signature      TEXT NOT NULL,
    auth_rule      TEXT,
    idempotency    TEXT,
    source_repo    VARCHAR(1024),
    source_path    VARCHAR(1024),
    source_owner   VARCHAR(255),
    created_at     TIMESTAMPTZ NOT NULL,
    updated_at     TIMESTAMPTZ NOT NULL,
    FOREIGN KEY (system_key, module_key)
        REFERENCES api_modules(system_key, module_key)
);

CREATE TABLE IF NOT EXISTS api_versions (
    api_id           VARCHAR(512) NOT NULL REFERENCES api_operations(api_id) ON DELETE CASCADE,
    version          VARCHAR(128) NOT NULL,
    lifecycle_status VARCHAR(32) NOT NULL
        CHECK (lifecycle_status IN ('DEVELOPING','RELEASED','SUPERSEDED','DEPRECATED','RETIRED')),
    capability       TEXT NOT NULL,
    signature        TEXT NOT NULL,
    auth_rule        TEXT,
    idempotency      TEXT,
    source_repo      VARCHAR(1024),
    source_path      VARCHAR(1024),
    source_owner     VARCHAR(255),
    origin_type      VARCHAR(32) NOT NULL DEFAULT 'NATIVE',
    discovery_confidence VARCHAR(16),
    scan_id          VARCHAR(255),
    approval_ref     VARCHAR(1024),
    source_commit    VARCHAR(255),
    content_hash     VARCHAR(64) NOT NULL,
    embedding_model  VARCHAR(255),
    embedding_dims   INTEGER,
    embedding        vector(384),
    created_at       TIMESTAMPTZ NOT NULL,
    updated_at       TIMESTAMPTZ NOT NULL,
    released_at      TIMESTAMPTZ,
    PRIMARY KEY (api_id, version)
);

ALTER TABLE api_versions ADD COLUMN IF NOT EXISTS capability TEXT;
ALTER TABLE api_versions ADD COLUMN IF NOT EXISTS signature TEXT;
ALTER TABLE api_versions ADD COLUMN IF NOT EXISTS auth_rule TEXT;
ALTER TABLE api_versions ADD COLUMN IF NOT EXISTS idempotency TEXT;
ALTER TABLE api_versions ADD COLUMN IF NOT EXISTS source_repo VARCHAR(1024);
ALTER TABLE api_versions ADD COLUMN IF NOT EXISTS source_path VARCHAR(1024);
ALTER TABLE api_versions ADD COLUMN IF NOT EXISTS source_owner VARCHAR(255);
ALTER TABLE api_versions ADD COLUMN IF NOT EXISTS origin_type VARCHAR(32) DEFAULT 'NATIVE';
ALTER TABLE api_versions ADD COLUMN IF NOT EXISTS discovery_confidence VARCHAR(16);
ALTER TABLE api_versions ADD COLUMN IF NOT EXISTS scan_id VARCHAR(255);
ALTER TABLE api_versions ADD COLUMN IF NOT EXISTS approval_ref VARCHAR(1024);

CREATE TABLE IF NOT EXISTS api_parameters (
    api_id      VARCHAR(512) NOT NULL,
    version     VARCHAR(128) NOT NULL,
    direction   VARCHAR(16) NOT NULL,
    ordinal     INTEGER NOT NULL,
    param_name  VARCHAR(255) NOT NULL,
    param_type  VARCHAR(512),
    description TEXT,
    is_required BOOLEAN NOT NULL,
    PRIMARY KEY (api_id, version, direction, ordinal),
    FOREIGN KEY (api_id, version) REFERENCES api_versions(api_id, version) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS api_usage_guidance (
    api_id         VARCHAR(512) NOT NULL,
    version        VARCHAR(128) NOT NULL,
    guidance_type  VARCHAR(32) NOT NULL,
    ordinal        INTEGER NOT NULL,
    guidance_text  TEXT NOT NULL,
    PRIMARY KEY (api_id, version, guidance_type, ordinal),
    FOREIGN KEY (api_id, version) REFERENCES api_versions(api_id, version) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS api_errors (
    api_id      VARCHAR(512) NOT NULL,
    version     VARCHAR(128) NOT NULL,
    error_code  VARCHAR(255) NOT NULL,
    description TEXT,
    PRIMARY KEY (api_id, version, error_code),
    FOREIGN KEY (api_id, version) REFERENCES api_versions(api_id, version) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS api_side_effects (
    api_id      VARCHAR(512) NOT NULL,
    version     VARCHAR(128) NOT NULL,
    ordinal     INTEGER NOT NULL,
    effect_text TEXT NOT NULL,
    PRIMARY KEY (api_id, version, ordinal),
    FOREIGN KEY (api_id, version) REFERENCES api_versions(api_id, version) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS api_discovery_evidence (
    api_id        VARCHAR(512) NOT NULL,
    version       VARCHAR(128) NOT NULL,
    ordinal       INTEGER NOT NULL,
    evidence_kind VARCHAR(64) NOT NULL,
    source_path   VARCHAR(1024) NOT NULL,
    source_line   INTEGER,
    source_symbol VARCHAR(512),
    detail        TEXT,
    PRIMARY KEY (api_id, version, ordinal),
    FOREIGN KEY (api_id, version) REFERENCES api_versions(api_id, version) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS api_relations (
    api_id         VARCHAR(512) NOT NULL,
    version        VARCHAR(128) NOT NULL,
    relation_type  VARCHAR(64) NOT NULL,
    target_api_id  VARCHAR(512) NOT NULL,
    target_version VARCHAR(128),
    PRIMARY KEY (api_id, version, relation_type, target_api_id),
    FOREIGN KEY (api_id, version) REFERENCES api_versions(api_id, version) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS api_lifecycle_events (
    id              BIGSERIAL PRIMARY KEY,
    api_id          VARCHAR(512) NOT NULL,
    version         VARCHAR(128) NOT NULL,
    from_status     VARCHAR(32),
    to_status       VARCHAR(32) NOT NULL,
    actor           VARCHAR(255),
    note            TEXT,
    related_version VARCHAR(128),
    occurred_at     TIMESTAMPTZ NOT NULL,
    FOREIGN KEY (api_id, version) REFERENCES api_versions(api_id, version) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_api_operations_scope
    ON api_operations(system_key, module_key, operation_name);
CREATE INDEX IF NOT EXISTS idx_api_versions_status
    ON api_versions(lifecycle_status, updated_at);
CREATE INDEX IF NOT EXISTS idx_api_relations_target
    ON api_relations(target_api_id);
CREATE INDEX IF NOT EXISTS idx_api_versions_search
    ON api_versions USING GIN (
        to_tsvector(
            'english',
            COALESCE(capability, '') || ' ' || COALESCE(signature, '')
        )
    );
CREATE INDEX IF NOT EXISTS idx_api_versions_embedding
    ON api_versions USING hnsw (embedding vector_cosine_ops);
