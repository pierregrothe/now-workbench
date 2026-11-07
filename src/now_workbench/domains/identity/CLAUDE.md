# identity domain context (Claude-only)

## What this domain does

Says who a person is to the workbench and what they may do: the team roster with roles
(ADR-017), the ambient actor of a request (ADR-025), who may impersonate whom and the
effective user of a request (ADR-020), the first-run setup code, and which owner start-up and
the CLI act as. It does NOT authenticate requests or read Cloudflare Access tokens (that is
`AccessMiddleware` and `AccessValidator` in `interfaces/api/`), hold the ambient owner email
used for row scoping (`current_owner` and `owner_scope` in `platform/owner.py`), or store
groups (groups domain; identity only reads `GroupRepository`).

## Public entry points (all from `now_workbench.domains.identity`)

Models:
- `AuthUser`: frozen; `email`, `roles` (frozenset of `Role`), `mode` ("cloudflare" or "local"),
  and while impersonating `real_email` and `real_roles`. `signed_in` returns the person really
  signed in.
- `Role`: ADMIN, SOLUTION_CONSULTANT. `TeamMember`: a roster row for the Team screen.

Actor context: `current_actor` (raises `NoActorError` outside a scope), `actor_scope` (user).

Team rules (`team.py`, shared by the API and Otto):
- `is_admin` (user) -> bool; `require_admin` (user) raises `ForbiddenError`.
- `normalize_email` (raw): trim, lower-case, validate; raises `InvalidInputError`.
- `list_team`, `set_roles` (conn, actor, email, admin, consultant), `remove_member`: admin only.

Impersonation: `may_impersonate` (conn, real, target), `candidates` (conn, real),
`effective_user` (conn, real) -> the impersonated `AuthUser`, or `real`.

Start-up: `operator_owner` (conn, local_mode) -> the email start-up and the CLI act as.
`SetupCodes` (announce): `issue`, `redeem`, `clear`, `active`; errors `SetupError`,
`WrongCodeError` (carries `remaining`), `TooManyAttemptsError`.

Storage: `UserRepository`.

## Wiring

- `UserRepository` owns the users table (one row per email, is_admin and is_consultant flags,
  at least one set) and the impersonations and impersonation_log tables. `claim_orphans` also
  writes owner_email in instances, chat_threads, seed_operations and artifacts, and moves the
  "" row of user_preferences.
- `interfaces/api/guard.py`: `authenticate` looks up roles per request; local mode builds an
  `AuthUser` for `LOCAL_EMAIL` holding every role. `AccessMiddleware` calls the act-as hook
  (`effective_user`, wired in `interfaces/api/app.py`) for people with a role, then enters
  `owner_scope` and `actor_scope` for the effective user.
- `interfaces/api/app.py` builds `SetupCodes` with a log announcer, calls `operator_owner` at
  start-up, and issues a code when Access is configured and `count_admins` is 0;
  `interfaces/api/setup.py` redeems it and calls `claim_orphans` for the new admin.
- Other callers: Otto tools read `current_actor` (`interfaces/ai/tools/base.py`) and
  `is_admin`; domains sharing, telemetry, conversations (`require_admin`, `is_admin`,
  `list_team`) and instances (`UserRepository` in `bootstrap.py`).
- Imports only the groups domain and platform (`Repository`, errors, `LOCAL_EMAIL`).
- Contracts: `acyclic-domains` -- identity depends on groups, so groups must never import
  identity.

## Invariants and gotchas

- Two ambient scopes, set together by the middleware: the owner email (platform) for row
  scoping and the actor (here) for role rules. Both fail closed when unset. Work outside a
  request (start-up, CLI, background) must open them itself; start-up uses `operator_owner`.
- A person with no role is not on the team: `get_user_roles` returns an empty set, which is
  how membership is tested (`put_group_member` in sharing relies on it).
- The last administrator cannot be demoted or removed (`ConflictError`).
- Impersonation: admins may act as any member; a group admin only as active members of a
  group they administer, never as a workbench admin; nobody as themselves or as a roleless
  email. `effective_user` re-checks on every request and ends a no-longer-allowed
  impersonation (logged 'revoked'). Rights always come from the signed-in person: callers pass
  `user.signed_in` to `may_impersonate`, never the impersonated user.
- `remove_member` deletes only the users row: group memberships stay, and an impersonation of
  that person ends on the next request because the target has no role.
- `operator_owner` returns "" behind Access before the first admin exists; rows created then
  are owned by "" until `claim_orphans` runs. A new owner-scoped table must be added to the
  table list in `claim_orphans`, or its early rows stay orphaned.
- `SetupCodes` keeps only a salted hash in memory; five misses issue a fresh code. A restart
  loses it (start-up issues a new one while no admin exists).
- `normalize_email` validates; `remove_group_member` in sharing only trims and lower-cases.

## Do not reinvent

Admin checks (`is_admin`, `require_admin`), email normalization (`normalize_email`), "who is
acting now" (`current_actor`), "who may this person act as" (`candidates`), first-admin lookup
(`first_admin_email`), or one-time code issuing with attempt limits (`SetupCodes`).
