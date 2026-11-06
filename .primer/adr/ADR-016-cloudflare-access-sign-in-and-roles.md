# ADR-016: Cloudflare Access sign-in and roles

**Status:** accepted
**Date:** 2026-11-06
**Amended:** 2026-11-06 by ADR-017 (roles moved from environment lists to the database)

## Context

- **No SSO from ServiceNow.** The workbench cannot sign people in through ServiceNow.
- **Cloudflare already fronts our servers.** srv01chambly runs a Cloudflare proxy, and the
  rivian gateway already validates Cloudflare Access tokens (PyJWT, `Cf-Access-Jwt-Assertion`).
  Cloudflare Access can sign people in with Apple and Google.
- **An earlier design was dropped.** Emailing a one-time code to a servicenow.com address
  needed our own SMTP account and gave no real authorization; it was removed before release.
- **Two roles are needed.** An administrator and a Solution Consultant; the owner is both.

## Decision

- **Cloudflare authenticates, the server verifies.** Access signs the person in (Apple or
  Google) and attaches a JWT. The server validates it with PyJWT: RS256 only, team issuer,
  application audience (AUD tag), required `exp`/`iat`/`aud`/`iss`, and an `email` claim.
  Anything else (missing, expired, wrong audience or issuer, service tokens) is refused.
- **Roles come from configuration, not from Cloudflare.** `WORKBENCH_ADMIN_EMAILS` and
  `WORKBENCH_CONSULTANT_EMAILS` list verified emails; an address on both lists holds both
  roles. A valid identity on neither list gets 403.
- **What each role may do.** `admin`: register, edit and delete instances (they hold
  credentials), change or delete the Claude API key, reset settings. `solution_consultant`:
  everything else, including chat, synthesis, capture, deploying to registered instances and
  non-secret preferences. Enforcement is on the server; the UI only hides what a role cannot use.
- **Every request is checked.** An ASGI middleware authenticates HTTP and WebSocket requests
  before any route runs (the CORS preflight is answered first).
- **Fail closed.** With Access unconfigured the server runs only on loopback, as one local
  user holding both roles. It refuses to start when bound beyond loopback without Access
  (`workbench serve` and app startup), and it refuses requests carrying Cloudflare headers
  when Access is not configured (a tunnel in front of an unconfigured server).
- **Profiles are per verified email** (schema v5): display name and avatar (12 built-in SVG
  avatars or an upload: PNG, JPEG or WebP by file signature, at most 2 MB, never SVG, stored
  under a hash of the email, served with `nosniff`).

## Setting it up on srv01chambly

1. Zero Trust, Settings, Authentication: add Google and Apple as login methods.
2. Access, Applications: add a self-hosted application for the workbench hostname with a
   policy that allows only the owner's and consultants' emails. Copy the **AUD tag**; the team
   domain is `<team>.cloudflareaccess.com`.
3. In the existing cloudflared configuration add a public hostname that points to
   `http://localhost:8080` (or run the optional `tunnel` compose profile).
4. In the compose `.env`: `WORKBENCH_ACCESS_TEAM_DOMAIN`, `WORKBENCH_ACCESS_AUDIENCE`,
   `WORKBENCH_ADMIN_EMAILS` and `WORKBENCH_CONSULTANT_EMAILS` (put the owner's email in both).
   The email must be the one Apple or Google returns to Cloudflare.

## Consequences

- New dependency: `pyjwt[crypto]`.
- Access policy is the outer gate, the email lists the inner one: removing someone from
  either list revokes their role immediately, without touching Cloudflare.
- Apple "Hide My Email" returns a relay address; the owner must list the address Cloudflare
  actually reports.

## Amendment (2026-11-06): roles in the database

`WORKBENCH_ADMIN_EMAILS` and `WORKBENCH_CONSULTANT_EMAILS` are removed. Roles are stored in
the `users` table and managed on the Team screen; the first administrator is created by the
first-run setup code (ADR-017). Steps 4 and the role lists above are superseded by
`docs/deploy.md`.
