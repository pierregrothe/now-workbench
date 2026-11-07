# ADR-025: Otto's Tool Set and Visual Tile Catalog

**Status:** accepted 2026-11-07
**Date:** 2026-11-07
**Builds on:** ADR-011 (Otto agent), ADR-013 (no fabricated data), ADR-015 (layers),
ADR-018 (sharing), ADR-023 (prompt caching), ADR-024 (web components)

## Context

Otto has 40 tools, but whole areas of the product are out of its reach: groups, sharing,
approvals, artifact versions, team roles and conversation limits. Its visuals are a side
effect: a tool returns tiles and every tile of every tool call is shown, so Otto cannot pick
what to show or explain something visually. A `render_ui_tiles` tool definition exists but
was never registered. The web tile renderer re-implements screens instead of reusing the app's
elements, and fills gaps with invented defaults ("Active" when no status was reported).

The permission rules for sharing, groups and the team live inside the API routes, so a tool
cannot apply the same rules without copying them.

## Decision

### 1. One rule set, two front doors

Permission and business rules move from API routes into domain services
(`domains/<name>/service.py`). Services take the connection and the acting `AuthUser`, and
raise domain errors (`NotFoundError`, `ForbiddenError`, `ConflictError`). The API maps them
to HTTP status codes; Otto's tools map them to a failed tool result. Neither front door
re-implements a rule.

### 2. Otto acts as the signed-in person

`ToolContext` carries the effective `AuthUser` (the impersonated person when an
administrator views as someone, ADR-020). Every tool is subject to exactly the checks the UI
is. Tools that change or delete something keep the existing confirmation step.

### 3. Tool coverage (owner's choice 2026-11-07: all administration except impersonation)

New tools cover groups and membership, sharing a bundle and withdrawing a share, the
approval inbox and decisions, artifact versions, team roles, and conversation limits.
Impersonation stays a deliberate action in the UI and has no tool.

### 4. A tile catalog and a `show` tool (owner's choice: entity tiles by id plus generic tiles)

- **Entity tiles** name a record by id (`instance`, `bundle`, `captures`, `runbook`,
  `seed-run`, `shares`, `diagnostics`). The server loads the record for the signed-in person
  when the tile is shown, so Otto cannot misstate it, and a record the person may not see is
  refused like any other access.
- **Generic tiles** carry content Otto writes: `rich-text`, `data-table`, `kpis`, `steps`,
  `comparison`, `callout`. Each has a strict schema; invalid input is returned to Otto as an
  error to correct.
- Every tile may set a `span` of 1, 2 or 3 columns (owner's request 2026-11-07). The reply grid
  has six tracks, so thirds, halves, two thirds and full width all fit; a tile without a span
  follows the reply layout, and screen cards and tables default to the full width. Narrow
  screens stack every tile.
- `show` takes a list of tiles and a layout. When Otto calls it during a reply, the reply shows
  what Otto chose; otherwise it shows the tiles the tools returned, as today.
- The system prompt tells Otto to use tiles as visual aids: a record it talks about, a
  comparison, the steps it is taking or proposing, a warning that needs attention.

### 5. Tiles reuse the app's elements

The web renderer draws entity tiles with the elements the screens use (ADR-024), so a tile
and its screen cannot drift apart. Missing values show as missing, never as a default.

## Consequences

- Adding a capability means a service function, a route and a tool, each a few lines.
- The tool list grows (about 55 tools). The tool definitions sit in the cached prompt prefix
  (ADR-023), so the cost is paid once per hour per conversation.
- Otto's answers become visual where that helps, and every number on an entity tile is the
  server's.
