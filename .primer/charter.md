# now-workbench -- Charter

## 1. Vision & Purpose
`now-workbench` is an AI-native developer and demonstration workbench designed as the
next-generation evolution and replacement for ServiceNow's internal DemoHub. It empowers
Solution Consultants (SCs), Advisory SCs, and Platform Developers to:
1. Declaratively build, stage, customize, and tear down full-stack ServiceNow demonstrations.
2. Compile and package ServiceNow Fluent SDK (`@servicenow/sdk`, `*.now.ts`) applications.
3. Automatically synthesize customer demo narratives, multi-table seed datasets, and branding
   from natural language using Claude AI (Otto Copilot).
4. Deliver compelling customer demonstrations with an interactive Presenter HUD, dynamic date
   wizard, and automated instance screenshot/video media capture.
5. Provide 1-click transactional teardown and rollback, restoring demo instances to baseline
   clean states or instantly swapping configurations between prospective customer meetings.

## 2. Core Architectural Pillars (DemoHub Parity & Beyond)
- **Declarative Demo Packages**: Self-contained `.sn-demo.zip` bundles containing Fluent
  TypeScript schemas, relational Table API seed data, system property snapshots, and walkthroughs.
- **Dynamic Date Wizard**: Automatic resolution of relative dates (`{{TODAY - 2h}}`, `{{TODAY - 3d}}`)
  at seed time so demo incidents, telemetry, and approvals always reflect current timestamps.
- **Duplicate-Before-Customizing**: 1-click bundle cloning allowing SCs to branch baseline packages
  into customer-specific variants without mutating reference content.
- **Safe Harbor & Content Governance**: Integrated Safe Harbor disclaimers and release family
  compliance gates within the Presenter HUD and runbook generators.
- **Secure Encrypted Storage**: Authenticated encryption at rest (PBKDF2-HMAC-SHA256) for
  credentials and API keys, strictly masked validation previews, and live verification gates.
- **Zero-Mocks Enforcement**: 100% test suite reliability backed by deterministic in-memory fakes.
