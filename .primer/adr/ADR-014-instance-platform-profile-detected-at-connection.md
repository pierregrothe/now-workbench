# ADR-014: Instance Platform Profile Detected at Connection

**Status:** accepted
**Date:** 2026-11-06
**Amended:** 2026-11-06 (schema v3: reported facts vs. declared purpose)
**Supersedes:** the 2026-11-06 decision-log entry "Instance release family is detected,
never user-selected" (glide.war-only detection, still stored in `instances.release`)

## Context

- **Release was user input.** The connect form asked for a "release family", with a
  default. The owner's instance runs Australia but was stored as Zurich.
- **First fix was not enough.** It read `glide.war` but still stored the result in a
  settable `release` column, and it still relied on a hardcoded `RELEASE_FAMILIES` list
  to order releases.
- **Release names can't be planned.** Unlike version numbers, ServiceNow release names
  cannot be known in advance (Australia was missing; unknown names were compared
  alphabetically, so the newest release ranked as the oldest).
- **More facts are needed.** The owner also wants the important facts about each
  instance stored: production or not, datacenter, memory, CPU, and so on.

A read-only probe of a live Australia instance (2026-11-06) showed that the standard
Table API exposes all of this:

| Source | Facts |
|--------|-------|
| `sys_properties` | `glide.war` (build), `glide.installation.production`, `instance_name` |
| `sys_cluster_state` | one row per application node: hostname (`app148145.aus101.service-now.com`, so the datacenter is `aus101`), status, `build_name` |
| `sys_cluster_node_stats.stats` | per-node diagnostics XML: `glide.build.name`/`.tag`/`.date`, `instance_type` (prod/dev/...), `jvm.cpu.count`, `system.memory.max`/`.in.use`, `scheduler.memory.pressure.state`, `servlet.uptime`, database product/version, Java version, OS |

Cost: 3 GETs, about 0.7 s and 430 KB for a 4-node instance. `stats.do` is a UI page
and does not accept REST basic auth, so it is not used.

## Decision

1. **The release is never input.**
   - Migration v2 drops `instances.release`.
   - `InstanceCreate`/`InstanceUpdate` have no release field, so the API rejects one
     with 422.
   - The CLI `--release` option, the AI-tool `release` parameter and the UI pickers are
     removed.
   - `InstanceRecord.release` is derived, read-only, from the detected profile
     (`Unknown` until detected).
2. **Profile captured on every successful connection test.**
   - `check_and_record_instance()` is the single test path. After authenticating, it
     calls `collect_instance_profile()` (`now_workbench/instance_profile.py`).
   - Results are stored in `instance_profiles` (1:1) and `instance_nodes` (1:N), both
     cascading from `instances`.
   - The CLI `instance add` now runs the check too.
3. **Best-effort, never invented.**
   - Each source is optional: a non-admin account still gets the release from
     `glide.war`.
   - If nothing at all can be read, the stored profile is kept, not wiped.
   - `fake://` instances are never probed, so no profile is fabricated for them.
   - Changing an instance's URL discards its profile, which described another system.
4. **The release name comes from the platform** (`glide.build.name`, then the cluster
   `build_name`, then the `glide.war` token), not from a list in the code.
5. **Ordering without planning names.**
   - `RELEASE_FAMILIES` is used only to order names that *requirements* mention
     (bundle `min_release`, feature minimums), which are always historical.
   - A detected name not in the list ranks after every entry: the list only holds
     releases that had shipped when it was written. A new ServiceNow release therefore
     works with no code change.
   - An undetected (`Unknown`) release never satisfies a requirement, and the reason
     tells the user to run a connection test.
   - The alphabetical fallback is removed.
6. **UI.** The admin panel shows, for the active instance: environment, datacenter,
   nodes online, CPUs per node, JVM heap used/max across nodes, worst memory pressure
   (amber at OVER/SUSTAINED_OVER), build date, database and Java. Each row shows
   release, environment badge (PROD in red) and datacenter. When no profile exists
   yet, the panel says so instead of showing defaults.

## Consequences

- Facts reflect the live instance as of the last successful check (`captured_at`). There
  is no background polling; the Test buttons, the CLI and Otto's tools refresh it.
- Memory figures are **JVM heap per node** (what the platform reports), not host RAM.
  CPU is the core count visible to each node's JVM.
- Full profiles need read access to `sys_cluster_state` and `sys_cluster_node_stats`
  (admin). With lesser roles the profile is partial, and the UI shows `--` for missing
  facts.
- Tests use an in-memory `httpx.MockTransport` ServiceNow (no network, no mocks).
  Playwright seeds profiles through the real repository code, because `fake://`
  instances are never profiled.

## Amendment: reported facts are not intent

**Finding.** The first version showed a red "PROD" badge for the owner's instance because
`instance_type` is `prod` and `glide.installation.production` is `true`. The instance is
a demo: `glide.installation.name` is "Demo Server", and the host is `demoalecto...`.
ServiceNow provisions standalone demo/trial instances with type `prod`, so the platform
value describes *how the instance was provisioned*, not what the owner uses it for.

**Decision (schema v3).**
1. `instances.purpose` (`demo | development | test | production`, default `demo`) is
   **declared by the owner**, enforced by a `CHECK` constraint and a `Literal` type, and
   settable in the UI, CLI (`--purpose`) and Otto tools. It is the only thing that
   drives warning styling (red badge for `production`).
2. The platform values are renamed to say what they are and are shown labelled
   "(reported)": `environment` becomes `instance_type`, `is_production` becomes
   `production_property`. `installation_name` (`glide.installation.name`) is added.
3. Purpose is never inferred from reported values, and a connection test never changes
   it. Release and platform facts stay detected-only; purpose stays declared-only.

**Consequence.** Guarding destructive operations (seed, deploy, reset) on instances
marked `production` is now possible and reliable. It is not implemented yet.
