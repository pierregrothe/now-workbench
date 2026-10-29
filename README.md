# now-workbench

**now-workbench** is an AI-native developer and demonstration workbench for the ServiceNow Fluent SDK (`@servicenow/sdk`).

## Key Features

- **ServiceNow Lux UI**: Elegant interface built with Lit Web Components faithful to ServiceNow's modern Next Experience.
- **Otto AI Copilot**: Context-aware assistant powered by Anthropic's Claude API for guided demo navigation, Fluent code explanations, and build troubleshooting.
- **Demo Bundles (`.sn-demo.zip`)**: Portable, versioned archives containing Fluent `.now.ts` source, Table API seed records, system properties, and presenter walkthroughs.
- **Docker-First Runtime**: Single container bundling Python 3.14, Node.js LTS, `@servicenow/sdk`, and the pre-built Lux UI.
- **Fast uv Package Management**: Migrated to `uv` + `hatchling` (PEP 621) matching the `market-data-services` stack.
- **Troubleshooting CLI**: Command-line tool (`workbench doctor`, `workbench demo`) for headless execution and CI/CD pipelines.

## Quick Start

### Local Development

1. **Backend (Python 3.14 + uv)**:
   ```bash
   uv sync
   uv run workbench doctor
   uv run workbench demo list
   uv run workbench serve --host 127.0.0.1 --port 8080
   ```

2. **Frontend (Lit + Vite)**:
   ```bash
   cd web
   npm install
   npm run dev
   ```

### Running with Docker

```bash
docker compose up
```

Access the Lux web dashboard at `http://localhost:8080`.
