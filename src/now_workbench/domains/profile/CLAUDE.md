# profile domain context (Claude-only)

## What this domain does

Keeps each signed-in person's own profile: a display name and an avatar that is none, one of
the built-in presets, or an uploaded PNG, JPEG or WebP picture (never SVG). One row per
verified email (ADR-016); the picture bytes live on disk. It also owns `sniff_image`, the
byte-based image type check other uploads reuse. It does NOT decide who someone is or what
roles they hold (`identity`, with the Cloudflare Access middleware in `interfaces/api/`), and
it does not build the `ProfilePublic` view or serve the picture (`interfaces/api/profile.py`).

## Public entry points (all from `now_workbench.domains.profile`)

- `ProfileRepository` -- `get_profile(email)` (creates an empty row on first use),
  `update_profile_name(email, display_name, now)`,
  `set_profile_avatar(email, kind, preset, now)`; each returns `ProfileRecord`.
- Services shared by the API and Otto (ADR-026): `rename(conn, email, display_name)` (trims,
  max 80 via `ProfileUpdate`), `choose_preset_avatar(conn, email, preset)` (raises
  `InvalidInputError` for an unknown preset; deletes any uploaded picture).
- Avatar files: `save_avatar(email, data, content_type)` (replaces the previous picture),
  `load_avatar(email)` -> bytes and content type, or None; `delete_avatar(email)`.
- `sniff_image(data)` -> `image/png`, `image/jpeg`, `image/webp` or None.
- Constants: `PRESET_AVATARS` (preset ids), `MAX_AVATAR_BYTES` (2 MB).
- Models: `ProfileRecord` (stored row), `ProfileUpdate`, `PresetRequest` (request bodies),
  `ProfilePublic`, `AvatarPublic` (UI views).

## Wiring

- Table: profile, keyed by email (`avatar_kind` is CHECKed to none, preset or upload).
  Pictures: `settings.get_data_dir()` / `avatars` / a sha256 stem of the email plus the
  extension, so the email never reaches the file system.
- Imported by `interfaces/api/profile.py` (all routes), `interfaces/ai/tools/account.py`
  (`show_profile`, `update_profile`), `interfaces/ai/audience.py` (display name for the
  prompt), and the `conversations` domain (`sniff_image` only).
- It imports only platform: `Repository`, `settings`, `InvalidInputError`.
- Contracts: `acyclic-domains` -- because `conversations` imports it, this domain must never
  import `conversations`.

## Invariants and gotchas

- Not owner-scoped through `current_owner()`: every function takes the email explicitly.
  Callers pass the authenticated `AuthUser` email (lower-cased by the access middleware),
  never one from a request body; a person can only reach their own profile.
- `get_profile` writes (INSERT OR IGNORE) even when only reading, and the update methods call
  it first, so a profile row always exists after any access.
- Uploading has no domain service: `interfaces/api/profile.py` checks the size, calls
  `sniff_image`, `save_avatar`, then `set_profile_avatar` with kind `upload`. Removing calls
  `delete_avatar` then sets kind `none`. Keep the file and the row in step if you add
  another front door; Otto deliberately offers presets only.
- The upload route reads the whole body before its size check when no Content-Length is
  sent (attachments, by contrast, stream with a cap).
- `PRESET_AVATARS` must match `web/src/profile/avatars.ts`; a test compares them.
- The avatar URL carries `avatar_updated_at` as a cache-buster; set it on every change
  (`set_profile_avatar` does).
- Deleting a user in `identity` does not remove their profile row or picture.

## Do not reinvent

- Trusting bytes, not the declared type, for image uploads (`sniff_image`;
  `conversations` builds its attachment check on it).
- Hashing an email into a safe file name (`_stem` in `avatars.py`) and per-user file storage
  under the data directory.
- A display-name lookup for prompts or tiles: `get_profile(email).display_name`, falling back
  to the email as `interfaces/ai/audience.py` does.
