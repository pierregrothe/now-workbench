# ADR-017: Container deployment and first-run setup

**Status:** accepted
**Date:** 2026-11-06

## Context

- **Deployment target.** One container on srv01chambly, reached only through Cloudflare at a
  new `workbench` hostname, behind Cloudflare Access (ADR-016).
- **Secrets.** The Claude API key and instance passwords must stay secure without complicating
  deployment. The database must not be readable on its own.
- **First administrator.** The owner asked for a first-run step that creates the admin. A
  first-run password form was considered; the owner asked for the more secure option.

## Decision

- **First admin by setup code, not by first-come password.** When Access is configured and no
  administrator exists, the server generates an 8-character code at startup and writes it only
  to the server log. A forced dialog in the UI asks for it; the Cloudflare-verified person who
  enters it becomes Administrator and Solution Consultant. The code is held hashed in memory,
  compared in constant time, replaced after five misses or on restart, and gone once used.
  Reading the log requires access to the server, which a visitor who merely reaches the page
  does not have; no reusable password is created.
- **Roles live in the database** (`users`, schema v6), managed on the admin-only Team screen.
  The environment email lists of ADR-016 are removed. There is always at least one admin.
- **Secrets enter through the UI only.** The Claude key and instance passwords are typed in the
  UI by an admin and sealed with AES-256-GCM (ADR-012). Neither appears in compose or `.env`;
  the only settings there are the Access team domain and AUD tag, which are not secrets.
- **Key and data are separated.** The master key is generated on first start into its own
  volume (`workbench-keys`); the database lives in `workbench-data`. `workbench backup` streams
  a consistent SQLite snapshot out of the container; the key is backed up separately, once.
- **Hardened container.** Non-root user, `no-new-privileges`, all capabilities dropped, port
  published on 127.0.0.1 only (cloudflared on the host is the way in), a `/healthz` probe that
  answers without sign-in and reveals only `ok`, and compose refuses to start without the
  Access values.

## Consequences

- No container was built or run while writing this (Docker is not installed on the development
  Mac): the first `docker compose up` on srv01chambly is the real test of the image.
- Non-secret data (conversations, team, preferences) is plain SQLite; whole-disk encryption on
  the host is the place to protect it further, not a database cipher.
- A person needs both an Access policy entry (outer gate) and a Team entry (inner gate).
