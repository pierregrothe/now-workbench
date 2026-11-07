# Review record -- docs/prd-otto-memory

- Head: b5dd59a0b2281e485542b622a4788ca1e741a436
- Branch: `docs/prd-otto-memory`
- Date: 2026-11-07
- Scope: documentation, plus one test-isolation fix found by this branch's gate. PRD-004 (Otto memory per person, accepted), ADR-034, EPIC-022 with three stories, and the ADR catalog row. No code.
- Process: the owner decided the three product questions (extraction, control, visibility) and accepted the two open questions (10 quiet minutes; 50 items / 4,000 characters). The controller checked the ADR against the current code:
  - Prompt caching: interfaces/ai/client.py builds one cached system block and a breakpoint on the second-to-last message, so a second system block with its own breakpoint keeps the prefix stable.
  - The SDK policy: anthropic may be imported only in interfaces/ai/{agent,client}.py, so the extraction call goes through interfaces/ai.
  - The schema: v14 on main, and the feedback row takes v15.

## Verified

- `primer-reconcile` is clean, and the ADR catalog count is updated.

- Test fix: the templates API test wrote into ./workspaces, so coverage of the 'target exists' branch depended on leftovers. Fresh worktrees failed the floor at 99.99%. The conftest now isolates `settings.workspace_dir`, and a direct test covers the branch.

## Not done (follow-ups)

- Implementation is EPIC-022 (three stories), after the feedback row lands.
