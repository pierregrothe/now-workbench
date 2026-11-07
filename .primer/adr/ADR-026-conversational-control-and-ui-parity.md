# ADR-026: Conversational Control and UI Parity

**Status:** accepted 2026-11-07
**Date:** 2026-11-07
**Builds on:** ADR-020 (impersonation), ADR-023 (prompt caching), ADR-025 (tool set, tiles)

## Context

The owner's requirements (2026-11-07):

1. Otto must understand its role, the tools it has, and the role and permissions of the
   person it talks to.
2. A person must be able to do everything by talking to Otto: no button to press, no form to
   fill. Otto also guides them around the interface.
3. The interface on its own must still let a person do everything, without Otto.

Measured gaps: Otto receives the same prompt and tools whoever is signed in; it cannot move
the interface; it has no tools for the profile, conversations or attachments. The interface
has no screen for a third of the capabilities Otto has: evaluating a demo, installing its
modules, testing its script, the full pipeline, resetting a demo, system properties,
templates, seed history and verification, testing or cleaning up all instances.

## Decision

### 1. Otto knows its audience

Every request carries a second system block, after the cached prefix, describing the person:
name, email, roles, the groups they administer or belong to, and whether an administrator is
viewing as them. It is stable for a conversation, so prompt caching still holds (ADR-023).
Tool definitions are filtered by role: a consultant is not offered administrator tools.
The static prompt describes Otto's role and maps the app's screens.

### 2. Otto drives the interface

- `open_screen` moves the interface: a screen, a Settings section, or the Actions screen with
  an action pre-filled ("let me show you where that is").
- A reply carries these interface commands; the chat applies them when the reply arrives,
  never when old history is reloaded.
- After a reply in which Otto used tools, the interface reloads the shared lists
  (instances, bundles, conversations, profile), so what Otto changed shows everywhere.
- New tools cover the remaining actions: the profile, conversations, and attachments.
  Exceptions, by design: the Claude API key (Otto never handles it), avatar upload and file
  attachments (they come from the person's computer), and impersonation (ADR-025).

### 3. The tool registry is the interface's action catalog

The registry Otto uses becomes the catalog of everything the app can do. `GET /api/actions`
lists it for the signed-in person (filtered by role, like Otto's); `POST /api/actions/{name}`
runs one as that person, under the same rules and the same confirmation step for changes
that remove or decide. An **Actions** screen builds a form from each action's schema and
shows the result as tiles. Every capability Otto has is therefore available by hand, now and
for every tool added later. The dedicated screens stay for the common flows.

## Consequences

- One definition per capability serves Otto, the Actions screen and (through the services)
  the API: they cannot drift apart.
- Two cached tool prefixes exist (administrator, consultant) instead of one.
- The Actions screen is generic by design; frequent flows keep their dedicated screens.
