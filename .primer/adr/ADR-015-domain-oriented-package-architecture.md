# ADR-015: Domain-Oriented Package Architecture with Enforced Layers

**Status:** accepted 2026-11-07 (open questions answered by the owner; see "Resolved
questions")
**Date:** 2026-11-06
**Amends (once accepted):** ADR-005 (size and complexity limits), ADR-006 (repository
composition)
**Reference:** the alphaseeker project (`services/<domain>/` template, import-linter
contracts, tiered size limits), scaled down to this project's size.

## Context

`now_workbench` is 82 Python files in 20 flat top-level modules. Measured 2026-11-06:

- **Tangled dependencies.** `db` is imported by 16 other packages and `config` by 12.
  There are two import cycles: `config` <-> `db` and `db` <-> `plugins`.
- **Domains are smeared.** The instances domain lives in 8 places: models and SQL in
  `db/`, `connectivity.py` and `instance_profile.py` at the package root, its CLI in
  `instances/`, routes in `api/`, tools in `ai/tools/`, plus overlapping logic in
  `ai/actions.py` and `api/threads.py`. The profile collector had to leave `instances/`
  to avoid a cycle.
- **No public surface.** Any module may import any other module's internals. Only
  absolute imports are enforced.
- **Limits are loose or unenforced.** `src/` allows 800 lines (4 files exceed 500, none
  exceed 800). The web limit is 500, yet 8 components exceed it (largest 1,559) and the
  gate still passes. Complexity uses a home-made counter at 10.

The project is expected to grow, so the structure should make new domains cheap to add
and make wrong dependencies fail the commit.

## Decision

### 1. Three layers under `src/now_workbench/`

```
platform/     no domain knowledge: config (settings, crypto), db (connection, migrations),
              sdk (now-sdk runner), remediation
domains/      one folder per business domain; may import platform and (via public roots)
              other domains
interfaces/   delivery: api/ (FastAPI), cli/ (Typer), ai/ (Otto); may import domains and
              platform; imported by nothing
```

Dependency direction is `interfaces -> domains -> platform`, never upward.

### 2. Target mapping

| Today | Destination |
|-------|-------------|
| `config/settings.py`, `config/crypto.py` | `platform/config/` |
| `db/session.py`, `db/schema.py` | `platform/db/` (connection, pragmas, ordered migrations) |
| `sdk/`, `remediation.py` | `platform/sdk/`, `platform/remediation.py` |
| `db/models.py` (instance entities), `db/repos/instances.py`, `connectivity.py`, `instance_profile.py` | `domains/instances/` |
| `plugins/`, plugin methods of `db/repos/instances.py` | `domains/plugins/` (depends on `instances`; `instances` does not know plugins) |
| `releases/` and `UNKNOWN_RELEASE` | `domains/releases/` (`instances` depends on `releases`) |
| `db/repos/preferences.py`, preference and secret models | `domains/settings/` |
| `db/repos/threads.py`, thread and message models, thread logic from `api/threads.py` | `domains/conversations/` |
| `db/repos/templates.py`, `templates/` | `domains/templates/` |
| `db/repos/seeds.py`, `seed/` | `domains/seed/` |
| `bundles/` (manager, models) | `domains/bundles/` |
| `bundles/pipeline.py` (orchestrates instances, plugins, runbooks, seed, capture) | `domains/demos/` (**open question 2**) |
| `capture/`, `properties/`, `runbooks/`, `fluent/`, `synthesizer/` | `domains/<same name>/` |
| `api/*` | `interfaces/api/` (routers stay thin) |
| `cli.py` and every `*/cli.py` and `bundles/pipeline_cli.py` | `interfaces/cli/<domain>.py` |
| `ai/` (client, agent, tiles, tools) | `interfaces/ai/` (`ai/actions.py` is a deletion candidate; **open question 3**) |

### 3. Domain template (lean, not mandatory boilerplate)

Each `domains/<name>/` has a curated `__init__.py` with `__all__` (its **public root**)
and, as needed, `models.py`, `repository.py`, `service.py` or `engine.py`, `errors.py`, and
a private `_internal/`. `protocols.py` is used only where a domain has several
implementations (real vs. fake runner), not as ceremony. Tests mirror the layout:
`tests/platform/`, `tests/domains/<name>/`, `tests/interfaces/`.

### 4. Enforced with import-linter (new dev dependency)

1. **Layers:** `interfaces > domains > platform`, upward imports forbidden.
2. **Public roots:** other domains import `now_workbench.domains.<name>`, never a submodule.
   Same-domain code is exempt.
3. **`_internal` privacy:** private to the package that owns it.
4. **Acyclic domains:** a declared dependency order (e.g. `releases` before `instances`
   before `plugins`) with cycles forbidden.

Contracts start in report-only mode with the current violations baselined, then tighten
to hard failures when the restructure finishes (the ratchet principle of ADR-005).

### 5. Limits (amends ADR-005)

- `src/`: **500** lines by default; `_internal/` 800; `models`, `config`, `enums`,
  `protocols`, `constants` 1,000 (alphaseeker's tiers). Tests keep 1,000 (largest is 823).
- Web components: keep the 500 limit but make it actually block, with the 8 existing
  offenders grandfathered in a baseline that can only shrink.
- Complexity: **ruff C901 at 10 and max 6 arguments**, replacing the home-made counter
  (`.ratchet/count_complexity.py`). A cognitive-complexity threshold (alphaseeker: 15)
  is optional and deferred.

### 6. Migration plan (no backward-compat shims)

One checkpoint commit per package move, each with `git mv`, a grep-first update of every
import and test path, and green pytest, mypy, ruff, ratchets and Playwright:

1. Add import-linter and the contracts in report-only mode.
2. `platform/` (config, db connection and migrations, sdk, remediation).
3. Leaf domains: `releases`, `settings`, `conversations`, `templates`.
4. `instances`, then `plugins`, `seed`, `bundles`, `demos`.
5. `capture`, `properties`, `runbooks`, `fluent`, `synthesizer`.
6. `interfaces/` (api, cli, ai), including entry points: `pyproject.toml`
   (`workbench` script), `cli.py serve` (uvicorn target) and the `Dockerfile`.
7. Tighten the contracts to hard failures; apply the new size and complexity gates;
   update CLAUDE.md, governance and the policy registry.

## Packages added after the first draft

| Today | Destination |
|-------|-------------|
| `procs.py` (bounded child processes) | `platform/procs.py` |
| `config/paths.py`, `config/origins.py` | `platform/config/` |
| `auth/owner.py` (ambient owner, `LOCAL_EMAIL`) | `platform/owner.py` (every repository scopes by it) |
| `auth/models.py`, `auth/impersonation.py`, `auth/setup.py`, users and groups repositories | `domains/identity/` |
| `auth/access.py`, `auth/guard.py` (Cloudflare Access, FastAPI dependencies) | `interfaces/api/` |
| `profile/`, profile repository | `domains/profile/` |
| `chat/`, chat and thread repositories | `domains/conversations/` |
| `sharing/`, artifacts repository | `domains/sharing/` |

## Resolved questions (owner, 2026-11-07)

1. **Repository composition: per-domain repositories, no bundle.** Each domain owns
   `<Name>Repository(conn)`; `platform/db` provides only the connection (`db_session()`
   yields a `sqlite3.Connection`) and migrations. A caller constructs the repositories it
   needs, so a function's dependencies are visible in its signature. `DatabaseRepository`
   is deleted.
2. **Orchestration: `domains/demos`.** The pipeline sits at the top of the domain order, so
   `bundles` stays a leaf.
3. **`ai/actions.py`: deleted.** The agent answers these requests with real tools; the
   keyword path ran in front of it, could answer wrongly and bypassed token accounting.
   Without a Claude key the tile resolver remains the fallback.
4. **Web: later, in its own ADR.** The 500-line limit is made blocking with the current
   offenders baselined.

## Consequences (if accepted)

- Wrong-direction imports fail the commit instead of surviving review.
- A new domain is one folder with a known shape; its public surface is explicit.
- The restructure touches nearly every file and every test import path. It is done in
  small green steps, before more features or more tests are built on the current shape.
- Test coverage work follows the restructure, so tests are written once, against the
  final layout.
