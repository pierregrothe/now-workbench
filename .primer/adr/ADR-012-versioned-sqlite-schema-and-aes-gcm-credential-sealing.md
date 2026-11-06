# ADR-012: Versioned SQLite Schema and AES-256-GCM Credential Sealing

**Status:** accepted
**Date:** 2026-11-06
**Amends:** ADR-006 (connection lifecycle and schema management; the scoped
`db_session` / frozen-model boundary of ADR-006 is unchanged)

## Context

The persistence layer was built during prototyping. A review on 2026-11-06 found:

1. **Credential exposure.**
   - `GET/POST/PUT /api/instances` returned `InstanceRecord`, which carries the
     *decrypted* password, so every registered password reached the browser in plaintext.
   - `update_instance` wrote the decrypted password back as plaintext on any update that
     omitted it (rename, default toggle). `decrypt_secret` passed unprefixed values
     through, so reads kept working and the leak was invisible.
2. **Weak key custody.**
   - The master key lived in `data/.workbench_master.key`, next to `workbench.db`, so a
     copy of the data directory yielded every secret.
   - The cipher was a hand-built HMAC-SHA256 keystream with an HMAC tag. It was sound in
     construction but unreviewed, and the code, UI and Otto all described it as "AES-256".
3. **No schema versioning.**
   - `init_db()` re-ran every `CREATE TABLE IF NOT EXISTS`, plus ad-hoc `ALTER TABLE`
     column probes, on every `db_session()` call (about 66 call sites).
   - There was no `user_version`, no way to evolve the schema deliberately, and no
     guard against a newer database.
4. **Constraints living in application code only.**
   - Uniqueness of the default instance and of instance names was not enforced.
   - JSON validity, boolean domains and the message cascade (`delete_thread` deleted
     messages by hand) were all left to the application.
   - Timestamps mixed `CURRENT_TIMESTAMP` (naive, space-separated) with ISO-8601 UTC.
5. **Test isolation leak.**
   - `api/app.py` ran `create_app()` at import, and `create_app()` opened a database
     session.
   - The capture driver and the property engine read the import-time
     `settings.data_dir`.
   - Together these meant the pytest run wrote to the developer's real
     `data/workbench.db`.

Requirement (owner, 2026-11-06): instance registrations must hold their credentials
encrypted; other instance fields (name, URL, release) stay queryable plaintext.

## Decision

### 1. Encryption: AES-256-GCM via `cryptography`

- **Cipher.** Secrets are sealed with `AESGCM` (`cryptography >= 46`), using a 96-bit
  random nonce per seal. The stored BLOB is `0x01 || nonce || ciphertext+tag`; the
  version byte allows future rotation.
- **Context binding.** Every ciphertext is bound to a context string through GCM
  associated data: `instance:<id>` for instance credentials, `secret:<name>` for
  application secrets. A blob copied to another row or slot fails authentication.
- **What is sealed.** Instance credentials (username *and* password) are sealed together
  as one JSON blob in `instances.credentials_sealed`. Name, URL, auth type, release and
  status remain plaintext columns so they can be indexed, sorted and shown.
- **Where the API key lives.** The Claude API key moves out of the preferences JSON
  into a dedicated `secrets(name, sealed)` table.
- **Master key resolution** (all outside the data directory):
  1. `WORKBENCH_MASTER_KEY`: urlsafe base64 of exactly 32 bytes, for containers and CI
     secrets.
  2. `WORKBENCH_KEY_FILE`: an explicit key file path.
  3. `$XDG_CONFIG_HOME/now-workbench/master.key` (default `~/.config/...`). It is created
     on first use with mode 0600 under a 0700 directory, using `O_EXCL` so concurrent
     CLI and server starts cannot write two different keys.
- **Docker.** `docker-compose.yml` mounts the key in its own named volume
  (`workbench-keys`), separate from `./data`.

Rejected alternatives:
- **OS keychain (`keyring`):** headless Ubuntu servers (srv01/srv02) have no Secret
  Service, so it would need a second code path anyway.
- **Encrypting whole instance rows (or SQLCipher):** breaks indexing and uniqueness on
  name, needs a native build, and exceeds the stated requirement.
- **PBKDF2 over a passphrase:** the key is random, not human-chosen, so key stretching
  adds cost without adding security.

### 2. API boundary: `InstancePublic`

- `InstanceRecord` (with decrypted credentials) is backend-only. Instance routes return
  `InstancePublic`, which carries `has_password: bool` and never the password.
- Duplicate-name registration or rename returns HTTP 409.

### 3. Versioned schema (`db/schema.py`)

- `PRAGMA user_version` tracks the schema version. `MIGRATIONS[n]` upgrades v(n) to
  v(n+1). Each step runs in its own `BEGIN IMMEDIATE` transaction and rolls back on
  failure. Migrations are append-only.
- `init_db()` reads `user_version` (one pragma) and migrates only when it is behind.
  The full migration runs under a process lock. A database newer than the build raises
  instead of being corrupted.
- A pre-v1 prototype file (tables present, `user_version = 0`) is renamed to
  `workbench.db.prototype-<UTC>.bak` together with its WAL sidecars, and a clean v1
  schema starts. There is no in-place data migration, because the prototype held no
  data worth carrying, in line with the no-backward-compat rule.

### 4. Schema v1 constraints (STRICT tables)

- **Instances:**
  - `name` is `UNIQUE COLLATE NOCASE` (lookups by name were already case-insensitive).
  - A partial unique index `ON instances(is_default) WHERE is_default = 1` allows at
    most one default instance.
  - `auth_type` is limited by `CHECK` to `basic | oauth | token`, and boolean columns by
    `CHECK (x IN (0, 1))`.
- **JSON columns** carry `CHECK (json_valid(...))`.
- **Cascades:** `chat_messages` and `instance_plugins` cascade from their parents via
  `ON DELETE CASCADE`. `seed_operations` deliberately has no foreign key, so the audit
  history survives instance deletion.
- **Indexes:** `chat_messages(thread_id, created_at)`, `chat_threads(archived,
  updated_at DESC)`, `seed_operations(created_at DESC)`.
- **Preferences** are a singleton row (`CHECK (id = 1)`) holding only non-secret JSON,
  validated by Pydantic on read.
- **Timestamps** default to UTC ISO-8601 with a `Z` suffix.

### 5. Connection pragmas (every connection)

- `foreign_keys = ON`, `busy_timeout = 5000` (the CLI and the server share the file).
- For file databases: `journal_mode = WAL` and `synchronous = NORMAL`. `NORMAL` is
  durable at checkpoint and safe under WAL, and avoids an fsync per commit.

### 6. Side-effect-free import

- Startup seeding moves into the FastAPI `lifespan` hook.
- Every data-directory consumer resolves through `settings.get_data_dir()`, which honors
  a runtime `WORKBENCH_DATA_DIR`.
- The test fixture also isolates the master key (`WORKBENCH_KEY_FILE` under
  `tmp_path`), so a test run never touches the developer's data or key.

## Consequences

- Passwords and usernames are unreadable from a copied `workbench.db`, and passwords
  never leave the backend through the REST API.
- **Losing the master key makes stored credentials and the API key unrecoverable.** It
  must be backed up separately from `data/`. When moving to another machine, copy
  `~/.config/now-workbench/master.key`, or set `WORKBENCH_MASTER_KEY`.
- Schema changes are now explicit, reviewed migration entries. Per-session overhead
  drops to one pragma read instead of eight DDL statements.
- New runtime dependency: `cryptography` (a wheel is available for macOS arm64 and
  Linux x86_64/arm64; no compiler is needed).
- Existing prototype databases are retired, not migrated: instances and the API key must
  be registered again once (the prototype held only test-generated data).
- Decrypted credentials reach the Node capture scripts (`chrome_capture.mjs`,
  `playbook_runner.mjs`) only as a JSON object on stdin (`--credentials-stdin`). The old
  `--username` and `--password` arguments were removed (2026-11-06), because argv is
  readable by any local user through the process list.
