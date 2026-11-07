# Review record -- feature/pipeline-nonblocking-plugins

- Head: cf5a1162959dd6da640e142a16b031e1e21f2a1c
- Branch: `feature/pipeline-nonblocking-plugins`
- Date: 2026-11-07
- Scope: EPIC-021 story 04.
  - `run_full_pipeline` runs its three synchronous plugin calls via `asyncio.to_thread`.
  - `ClaudeAgentRunner.stream_run` (the `/ws/otto` path) runs `loop.run_tools` via `asyncio.to_thread`.
  - A slow instance no longer stalls the server's event loop.
- Process: top-tier implementer (red first); one Sonnet adversarial review and one verify round.
  - Round 1: no BLOCKING. 2 MAJOR:
    - the third `to_thread` site was untested (its mutant survived);
    - `/ws/otto` ran every synchronous tool, and every `run_async` handler, on the event loop.
  - MINOR: `check_same_thread` use stays sequential; the default executor is shared with reply keepalives.
  - Round 2 (a6568f0): a deploy-succeeds case covering all 6 query windows, and `stream_run` hopping to a thread. Red-first tests for both. The CHANGELOG and cards now name each path.
  - Verify: no BLOCKING or MAJOR. Both mutants are killed, and every `run_tools`/`execute_tool` caller is off the loop (stream_run, the reply thread, the sync actions route). The load run passed 5 times.

## Verified

- 1,266 tests at 100% coverage; 400 tests across the 23 files that touch these paths.
- Confirmations and usage recording are unchanged, and the owner and actor scope carries into the tool thread (asserted).

## Not done (follow-ups)

- If the ws handler task is cancelled mid-tool, `db_session` could close the connection while the tool thread is still using it (pre-existing, rare).
