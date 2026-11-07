# Changelog

One line per change, newest first: `### Added`, `### Changed`, `### Fixed`, `### Removed`, `### Security`.
The story behind a change is in its pull request (the number in brackets) and in `git log`.
Releases are cut when an epic closes. Months below were condensed from pull-request titles:
internal chores, docs, tests and CI are omitted, and the long-form entries are in git history at 947a337.

## [Unreleased]

### Fixed
- demos: One exported is_simulated rule everywhere; a simulated instance never gets a real SDK deploy, seed call or capture; seed and deploy APIs honour sdk_fake_mode

## [2026.11.1] - 2026-11-07

### Added
- governance: domain cards: a ratchet on names a card gives that src lacks, and a pre-push freshness nudge (ADR-033)
- docs: a CLAUDE.md card in each of the 19 domains: entry points, wiring, invariants, what not to reinvent (ADR-033)
- dev-tools: find_capability.py: does it already exist? lexical search over public symbols, plus a TypeSafe Jev pass (ADR-033)

### Changed
- governance: main is protected by a GitHub ruleset (PRs only, no bypass); the release bot lands its bump as a PR (ADR-032)

## [2026.11.0] - 2026-11-07

### Added
- governance: work lands through a stamped, reviewed PR; a release is cut when a merge closes an epic (ADR-032)

## [2026.11]

_Condensed from pull-request titles._

### Added
- settings: per-person usage allowances and own usage on Profile (ADR-031)
- otto: monthly Claude usage allowance per person, admins exempt (ADR-031)
- web: open the command palette by touch (ADR-030)
- ops: nightly backups to the Garage bucket on the NAS (ADR-029)
- web: phone and tablet layouts with a navigation drawer (ADR-030)
- ops: mutation gate at pre-push, telemetry retention, S3 backup target (ADR-029)
- web: render Otto's text as HTML through a safe markdown subset (ADR-028)
- telemetry: record every action run and Claude call, and chart them (ADR-028)
- otto: chart tiles and history tools (ADR-027)
- otto: conversational control of the whole app, and an Actions screen for every capability (ADR-026)
- otto: tiles span one, two or three columns (ADR-025)
- web: render Otto's catalog tiles with the app's own elements (ADR-025)
- otto: sharing and admin tools, and a show tool for visual tiles (ADR-025)
- otto: cache conversations byte for byte; compaction; token budgets per conversation
- pipeline: deploy a demo's Fluent app into the instance's vendor scope
- otto: read property values live from the instance
- otto: verify seeded records on the instance; failed seeds keep their reason
- otto: check its own work; tools can show Claude images; room to fix and verify
- chat: attach files for Otto to read; admin-set conversation limits
- ui: drag the sidebar edge to resize it, like EmployeeWorks
- auth: administrators can view as someone (impersonation)
- ui: versions and sharing in the Artifact library; Groups and Approvals settings
- sharing: groups, versioned artifacts and approved shares
- ui: Otto-style Learn more pill; everyone manages their own instances in Settings
- deploy: the Claude key can come from the server .env
- ownership: every instance, conversation, seed run and setting belongs to one person
- ui: light-only Otto look; sidebar Recent header; Otto-style bottom prompt
- deploy: isolate the workbench with its own tunnel, network and egress firewall
- deploy: first-run setup code, team roles in the database, hardened container
- auth: Cloudflare Access sign-in with admin and consultant roles; Otto-style icons
- profile: profile picture, built-in avatars and servicenow.com email-code approval
- ui: settings left menu, detail side panel, live home tiles, shared tile chrome
- ui: align chat, tiles and areas to the observed Otto look and feel
- instances: declare instance purpose; label platform-reported type as reported
- instances: detect full platform profile at connection; release is never input
- instances: detect release family from glide.war instead of asking
- db: versioned schema, AES-256-GCM sealed credentials, and isolated test storage
- ui: display minimum release requirement in catalog cards and modal
- releases: add minimum platform version validation and workspace evolution resolver
- capture: enable natural video duration and respect playbook wait pacing
- capture: remove cursor label badge and record clean pointer demo
- doctor: inspect database credentials and record Otto live pipeline proof

### Changed
- domains: sharing, group and team rules move into domain services (ADR-025)
- web: one InstanceData type; PrefsSection base for preference sections
- web: shell keeps navigation only; every web file under 500 lines (ADR-024)
- web: clone and deploy dialogs leave the demo catalog (ADR-024)
- web: settings sections as elements; settings load and reset report failures (ADR-024)
- web: component styles beside their components; split the admin panel (ADR-024)
- web: StoreController and a shared workspace bar; delete the dead Otto drawer (ADR-024)
- ai: one tool loop for the async runner and the sync path
- ADR-015 limits -- 500-line modules, ruff complexity and argument caps
- interfaces: split the largest modules along their seams
- instances: one resolve() for 'the named instance or the default'
- platform, domains and interfaces layers with import contracts (ADR-015)
- db: per-domain repositories over one connection; delete the facade
- ai: delete the keyword action fallback; accept ADR-015
- settings: remove the default release preference

### Fixed
- web: the bundle list and the welcome guide report failures instead of hiding them
- otto: a confirmed action is replayed as what Otto ran, not a bare result
- capture: verify instance TLS certificates and name a refused one
- cli: refuse bundle, template and capture ids that escape their folder
- otto: chart requests Otto gets right the first time
- otto: the agent runner takes the whole question, so tools know the conversation
- sdk: relink a project whose shared toolchain moved or was removed
- bounded subprocesses, shared Claude client, export cleanup, slimmer image, container limits
- ui: conversation counters show questions asked against the admin limit
- chat: long Otto replies no longer hit Cloudflare's 100-second limit (HTTP 524)
- pipeline: SDK deploy uses the SDK's CI credentials; skip deploy without a project
- otto: one rolling prompt-cache breakpoint, so long tool chains do not fail
- capture: sign in via login.do before a screenshot; fail on a signed-out page
- capture: real screenshots in the container; failures are reported, never faked
- otto: readiness scorecard shows the instance's release, not the bundle's
- plugins: read plugin state from the instance; real plugin ids in demos
- deploy: public DNS for the isolated network; block the host from it too
- deploy: exclude the workbench from watchtower; start without the tunnel token
- chat: wire Confirm and Cancel on tool confirmation tiles; format message times
- chat: start a conversation when the first Home message has no active thread
- chat: bundle delete and instance add are previews, never executed from chat
- ui: show synthesis and load errors instead of failing silently
- synthesizer: take the release from the target instance, not a typed field
- wave 2 (9 findings: API origin/deploy security, ratchet fail-closed, shell and HUD honesty)
- wave 1 (14 findings + sec-104 completion: bundle paths, seed truthfulness, UI honesty)
- wave 0 (13 findings: wiring, pipeline truthfulness, template paths, plugins, capture)
- e2e: build the test UI into .e2e/dist instead of overwriting web/dist
- ui: render the real instance registry and add Playwright e2e suite
- capture: pass instance credentials to Node capture scripts via stdin
- db: keep instance password encrypted on non-credential updates
- hooks: use relative Antigravity hook paths and wire unwired Claude hooks

## [2026.10]

_Condensed from pull-request titles._

### Added
- capture: authenticate and execute live demonstration recording against ServiceNow
- capture: enable video proof deployment and capture media purge controls
- ai: unified async ClaudeAgentRunner, real-time event streaming, and domain modularization (EPIC-016)
- frontend: decompose monolithic workspace into Lit 3 Reactive Controllers, Context store, and modular sub-500 LOC views (EPIC-015)
- playbook: implement declarative demo playbooks and native Playwright proof driver (EPIC-014)
- complete now-workbench interactive demo runner and lux ui
- initial scaffold of now-workbench with Lit Lux UI, Otto copilot, and Primer

### Fixed
- ai: pass instance credentials to capture_media tool in Otto
- capture: eliminate silent mockup fallback in live mode and purge media artifacts
