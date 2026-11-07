# ADR-029: Mutation Gate, Telemetry Retention and S3 Backups

**Status:** accepted 2026-11-07
**Date:** 2026-11-07
**Builds on:** ADR-005 (governance gates), ADR-013 (no fabricated data), ADR-028 (telemetry)

## Context

After ADR-028 the owner asked (2026-11-07) for three things: make mutation testing a standing
gate, put a retention limit on telemetry, and allow backups to go to an S3 bucket.

## Decision

### 1. Mutation gate (pre-push)

`scripts/mutation_gate.py` runs mutmut over the modules listed in `[tool.mutmut]` in
`pyproject.toml` and fails the push if any mutant is not killed (survived, suspicious, no
tests, not checked, or timed out). It is wired as the `mutation-gate` pre-push hook (policy
`mutation-testing`) and takes about 35 seconds.

- **Scope:** the ADR-027, ADR-028 and ADR-029 modules (chart helpers, history and instance
  chart tools, telemetry, instance stats, retention, S3 upload). It does not cover the whole
  codebase; a module joins the gate by being added to `source_paths`, with its tests added to
  the test selection, once its mutants are all killed.
- **Fresh run:** the `mutants/` cache is deleted first, because mutmut keeps a verdict while
  the mutated function is unchanged, so a weakened test would otherwise keep an old "killed".
- **Fork-server mode:** plain fork crashes every mutant on macOS under Python 3.14.
- **Timeouts are re-run once, alone.** In fork-server mode mutmut forks each test process
  from a process that runs a timer thread, and such a fork occasionally deadlocks. Under a
  full parallel run a different mutant timed out on each of three runs, and every one was
  killed when run alone. A real hang still times out when run alone and fails the gate.
  Survivors are never retried.
- **No exclusions.** Equivalent mutants are removed by restructuring the code, as in ADR-028.
  `platform/clock.py` (`utc_now`) is the one place gated modules read the time. Inline
  `datetime.now(UTC)` let the `now(None)` mutant survive whenever local and UTC dates agreed,
  so the gate passed or failed with the time of day.

### 2. Telemetry retention

`WORKBENCH_TELEMETRY_RETENTION_DAYS` (default 365, minimum 60) bounds `usage_events` and
`action_events`. The minimum is the longest chart (60 days): a shorter window would show
purged days as zero, a fabricated value (ADR-013). The server purges once at startup and then
every 24 hours (`interfaces/api/retention.py`). A failed purge is logged as an error, and the
events are kept until the next run.

### 3. Backups to S3

`workbench backup --s3` uploads the same consistent snapshot to
`s3://<bucket>/<prefix>workbench-<UTC time>.db`, configured by `WORKBENCH_BACKUP_S3_BUCKET`,
`_REGION`, `_ENDPOINT` (empty for AWS; set for R2, MinIO, B2), `_PREFIX`, `_ACCESS_KEY_ID`
and `_SECRET_ACCESS_KEY`. The existing file and stdout targets are unchanged.

- **No AWS SDK:** `platform/s3.py` signs one PUT with Signature Version 4 over httpx. Tests
  check it against two signatures produced by botocore. It also matched botocore on 200
  random requests (regions, endpoints, key characters) checked outside the repository.
- **Integrity:** the body's SHA-256 is signed, so the bucket rejects a body altered in
  transit. Endpoints must be HTTPS (one exception below), and bucket names are checked
  against the S3 naming rules before they go into the path.
- **Secrets:** the master key is still never part of a backup. The bucket's credentials live
  only in the server's `.env` (mode 600). For Garage they were piped from the NAS straight
  into it at the owner's request, never displayed.
- **Garage on the NAS (amended 2026-11-07):** the owner's bucket is Garage on syn01chambly,
  which serves plain HTTP. Plain HTTP is therefore accepted, but only to a private or loopback
  IP literal (never a name, so DNS cannot redirect it); everything else must be HTTPS. The
  signature still covers the body. The workbench container is firewalled away from the LAN,
  so `deploy/workbench-backup.sh` uploads from a separate short-lived container on the host
  network, run nightly by cron, with only the `WORKBENCH_BACKUP_S3_*` settings. The firewall
  is unchanged.
- **Retention and scheduling** of the objects belong to the bucket (lifecycle rules) and the
  host (cron). The workbench uploads; it does not delete.

## Consequences

- `git push` takes about 35 seconds longer.
- Telemetry stops growing past a year by default.
- Off-site backups need no extra dependency. Scheduling them is a host cron entry
  (docs/deploy.md).
