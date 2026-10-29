# now-workbench

**now-workbench** is an AI-native, containerized developer and demonstration workbench for the ServiceNow Fluent SDK (`@servicenow/sdk`).

## Key Features

- **ServiceNow Lux UI**: Elegant interface built with Lit Web Components faithful to ServiceNow's modern Next Experience.
- **Otto AI Copilot**: Context-aware assistant powered by Anthropic's Claude API for guided demo navigation, Fluent code explanations, and build troubleshooting.
- **Demo Bundles (`.sn-demo.zip`)**: Portable, versioned archives containing Fluent `.now.ts` source, Table API seed records, system properties, and presenter walkthroughs.
- **Docker-First Runtime**: Single container bundling Python 3.14, Node.js LTS, `@servicenow/sdk`, and the pre-built Lux UI.
- **Troubleshooting CLI**: Command-line tool (`workbench doctor`, `workbench demo`) for headless execution and CI/CD pipelines.

## Quick Start

### Running with Docker

```bash
docker compose up
```

Access the Lux web dashboard at `http://localhost:8080`.

### Local Development

1. **Backend (Python)**:
   ```bash
   poetry install
   poetry run workbench doctor
   poetry run workbench serve
   ```

2. **Frontend (Lit + Vite)**:
   ```bash
   cd web
   npm install
   npm run dev
   ```
