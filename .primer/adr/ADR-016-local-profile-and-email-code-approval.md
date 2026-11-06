# ADR-016: Local profile with email-code approval

**Status:** accepted
**Date:** 2026-11-06

## Context

- **No SSO.** The workbench cannot sign users in through ServiceNow. The owner wants a
  profile (picture or built-in avatar) and a way to tie it to an active servicenow.com
  mailbox.
- **Single local user.** The app is local and unauthenticated; the profile is an identity
  label and an approval badge, not an access-control system.

## Decision

- **One profile row (schema v5).** `profile` holds name, email, avatar choice and the
  pending code state; `mail_settings` holds SMTP host, port, username, sender and
  STARTTLS. The SMTP password is sealed in `secrets` (ADR-012) and is never returned.
- **Approval by one-time code.** The email must be an exact `@servicenow.com` mailbox.
  A code of 8 characters from an alphabet without 0/O/1/I (about 40 bits) is emailed.
  Only a salted SHA-256 is stored; it is compared in constant time; it expires after
  10 minutes; five wrong attempts discard it; a new code can be requested after 60 seconds.
  Changing the email resets approval. A delivery failure stores no code and is reported.
- **No pretend delivery.** Without SMTP settings the send route answers 409. A mailer
  protocol lets tests inject an in-memory mailer (no network).
- **Avatars.** Twelve built-in SVG avatars (ids shared by backend and web), or an upload.
  Uploads must be PNG, JPEG or WebP by file signature (never SVG), at most 2 MB, stored
  under a fixed name in `data/avatars/`, served with `nosniff`.

## Consequences

- Approval proves control of a servicenow.com mailbox, nothing more; it gates nothing yet.
- Sending needs an SMTP account the owner supplies; none is bundled.
- Adding an avatar means adding its id in `profile/avatars.py` and `profile/avatars.ts`
  (a test fails if they differ).
