# .ratchet/

Net-increase ratchet enforcement for `now-workbench`. Violations can decrease
but never increase. Pre-existing violations are baselined in `baselines.json`;
new violations block the commit.

## Source of Truth

`ratchet_check.py`'s `VALIDATORS` registry is the authoritative list of
checks. `baselines.json` stores current per-check violation counts.

```bash
uv run python .ratchet/ratchet_check.py all            # run all validators in parallel pool
uv run python .ratchet/ratchet_check.py <name>         # run a single validator
uv run python .ratchet/ratchet_check.py tighten        # persist improved baselines
uv run python .ratchet/ratchet_check.py tighten <name> # persist one validator's improvement
uv run python .ratchet/ratchet_check.py --init         # initialize baselines from code
```

## Active Validators (ADR-005)

- `no-mocks`: Strictly bans `unittest.mock`, `pytest-mock`, `patch` in tests. Only deterministic in-memory fakes permitted.
- `file-size`: Enforces file-size caps (src <= 500 tiered per ADR-015, tests <= 1000, web <= 500 lines).
- `type-ignores`: Burndown ratchet for `# type: ignore` occurrences in `src/`.
- `absolute-imports`: Strictly bans relative imports in `src/now_workbench/`.

The governance view of these checks is the `gates-ratchet` table in
`.primer/governance.md`, linked to `.primer/policies/registry.yaml`.
