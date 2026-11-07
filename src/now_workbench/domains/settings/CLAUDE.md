# settings domain context (Claude-only)

## What this domain does

Stores each person's workbench preferences (Claude model, intent routing, capture defaults,
synthesis author and branding defaults, SDK fake mode, UI toggles) as one JSON row per owner,
and the workbench-wide named secrets, sealed with AES-256-GCM (ADR-012); today the only secret
is the Claude API key. It does NOT hold server configuration from the environment (that is
`settings` in `platform/config/settings.py`, read here lazily), seal instance credentials (the
instances domain seals its own with `seal_secret`), store admin-edited global limits (the
app_settings table belongs to the conversations domain), or validate a key against Anthropic
(`validate_api_key` in `interfaces/ai/client.py`).

## Public entry points (all from `now_workbench.domains.settings`)

- `PreferencesRepository` (conn):
  - `get_workbench_preferences` -> `WorkbenchPreferences`, with the key masked
    (`anthropic_api_key_masked`, `has_anthropic_api_key`, `anthropic_api_key_from_env`),
    never the key itself.
  - `update_workbench_preferences` (update) -> merged preferences; raises `ValueError` when a
    new key is given while one is stored, or while the environment supplies one.
  - `reset_workbench_preferences`: delete the owner's row; the shared key is untouched.
  - `get_decrypted_anthropic_api_key`: the environment key when set, else the stored one.
  - `delete_anthropic_api_key`, and the generic `get_secret` / `set_secret` (name, value).
- `WorkbenchPreferences`: frozen, every field defaulted; the three key fields are derived on
  read and never stored.
- `WorkbenchPreferencesUpdate`: all fields optional; None means "leave unchanged".

## Wiring

- Tables: user_preferences (email primary key, JSON payload) and secrets (name primary key,
  sealed blob).
- Imports only platform: `Repository`, `current_owner`, `seal_secret`, `unseal_secret`,
  `mask_api_key`, and `settings` (`anthropic_api_key`, `claude_model`), the last imported inside
  functions. No other domain.
- Callers (all interfaces): `interfaces/api/settings_api.py` (GET, PUT, DELETE of the key),
  `interfaces/api/otto_ws.py` (key and preferences per conversation), `interfaces/api/`
  `actions.py`, `captures.py`, `demos.py`, `instances.py`, `replies.py`; Otto tools in
  `interfaces/ai/tools/` (`system.py` show, update, reset; `bundles.py`, `demos.py`); the CLI
  (`interfaces/cli/config.py`, `interfaces/cli/main.py`).
- `identity` also writes user_preferences: `claim_orphans` moves the "" row to the first
  administrator.

## Invariants and gotchas

- Preference reads and writes are owner-scoped through `current_owner` and raise
  `NoOwnerError` outside an `owner_scope` (fail closed); `get_secret`, `set_secret` and
  `get_decrypted_anthropic_api_key` need no scope. The CLI opens one for the operator in its
  root callback (`interfaces/cli/main.py`); other non-request code must open its own.
- Secrets are NOT owner-scoped: one Claude key serves everyone. Who may change it is enforced
  at the interface, not here: the PUT route needs the admin role for the key field, DELETE is
  admin only, and the Otto settings tool drops secret fields from its schema. A new caller of
  `update_workbench_preferences` or `set_secret` must apply that check itself.
- First read writes: a person with no row gets a default row persisted, seeded with
  `claude_model` from the environment.
- A key change is refused while a key is stored (delete first), and always when the
  environment provides `WORKBENCH_ANTHROPIC_API_KEY`, which also wins on read. A submitted key
  containing "..." is treated as the masked preview echoed back and silently ignored; an empty
  key deletes the stored one.
- Stored payloads are rebuilt with `extra="forbid"`: removing or renaming a field of
  `WorkbenchPreferences` breaks every existing row unless a schema migration strips it from
  the JSON (v7 did this for theme_mode).
- A field added to `WorkbenchPreferences` must also be added to `WorkbenchPreferencesUpdate`,
  or nobody can change it; the Otto tool builds its argument schema from the update model.
- Secrets are bound to the context "secret:<name>"; a row copied under another name will not
  unseal.

## Known gaps

- `repository.py` has no file header comment (it starts with the docstring).

## Do not reinvent

A per-user preference store (add a field here rather than a new table), sealing an
app-wide secret (`set_secret` / `get_secret`), masking a key for display (`mask_api_key`), or
"which Claude key do we use" (`get_decrypted_anthropic_api_key`).
