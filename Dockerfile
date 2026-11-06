# -- Stage 1: Build Lit Web Components Frontend -------------------------------
FROM node:20-alpine AS frontend-builder
WORKDIR /app/web
COPY web/package*.json ./
RUN npm install
COPY web/ ./
RUN npm run build

# -- Stage 2: Runtime Environment (Python + Node.js + now-sdk + uv) ------------
FROM python:3.14-slim-bookworm

# Install Node.js 20 LTS, git, and curl
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    git \
    ca-certificates \
    gnupg \
    && mkdir -p /etc/apt/keyrings \
    && curl -fsSL https://deb.nodesource.com/gpgkey/nodesource-repo.gpg.key | gpg --dearmor -o /etc/apt/keyrings/nodesource.gpg \
    && echo "deb [signed-by=/etc/apt/keyrings/nodesource.gpg] https://deb.nodesource.com/node_20.x nodistro main" | tee /etc/apt/sources.list.d/nodesource.list \
    && apt-get update && apt-get install -y nodejs \
    && npm install -g @servicenow/sdk \
    && rm -rf /var/lib/apt/lists/*

# Install uv from official binary image
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

# Copy Python project configuration & sync dependencies
COPY pyproject.toml uv.lock* README.md ./
RUN uv sync --frozen --no-dev --no-install-project

# Copy Python source code and install project
COPY src/ ./src/
RUN uv sync --frozen --no-dev

# Copy pre-built Lit frontend from Stage 1
COPY --from=frontend-builder /app/web/dist ./web/dist

# Default demonstration bundles & workspace storage
COPY bundles/ ./bundles/

# Run as an unprivileged user (ADR-017). The writable paths are owned by it; Docker copies this
# ownership into the named volumes the first time they are created.
RUN groupadd --system --gid 10001 workbench \
    && useradd --system --uid 10001 --gid workbench --home-dir /tmp --shell /usr/sbin/nologin workbench \
    && mkdir -p /app/workspaces /app/data /run/workbench-keys \
    && chown -R workbench:workbench /app/workspaces /app/data /app/bundles /run/workbench-keys \
    && chmod 700 /run/workbench-keys

EXPOSE 8080

# Environment defaults
ENV WORKBENCH_HOST="0.0.0.0" \
    WORKBENCH_PORT="8080" \
    WORKBENCH_STATIC_DIR="/app/web/dist" \
    WORKBENCH_BUNDLES_DIR="/app/bundles" \
    WORKBENCH_WORKSPACE_DIR="/app/workspaces" \
    WORKBENCH_CLAUDE_MODEL="claude-sonnet-5-5" \
    WORKBENCH_KEY_FILE="/run/workbench-keys/master.key" \
    HOME="/tmp" \
    PATH="/app/.venv/bin:$PATH"

USER workbench

# /healthz answers without sign-in and says only "ok" (ADR-017).
HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
    CMD python -c "import sys, urllib.request; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8080/healthz', timeout=4).status == 200 else 1)"

ENTRYPOINT ["workbench", "serve", "--host", "0.0.0.0", "--port", "8080"]
