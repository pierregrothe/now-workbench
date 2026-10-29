# ── Stage 1: Build Lit Web Components Frontend ──────────────────────────────
FROM node:20-alpine AS frontend-builder
WORKDIR /app/web
COPY web/package*.json ./
RUN npm install
COPY web/ ./
RUN npm run build

# ── Stage 2: Runtime Environment (Python + Node.js + now-sdk) ─────────────────
FROM python:3.12-slim-bookworm

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

WORKDIR /app

# Install Poetry
ENV POETRY_VERSION=1.8.3 \
    POETRY_HOME="/opt/poetry" \
    POETRY_VIRTUALENVS_IN_PROJECT=false \
    POETRY_NO_INTERACTION=1
RUN curl -sSL https://install.python-poetry.org | python3 -
ENV PATH="$POETRY_HOME/bin:$PATH"

# Copy Python dependencies configuration
COPY pyproject.toml poetry.lock* README.md ./
RUN poetry config virtualenvs.create false \
    && poetry install --no-root --no-interaction

# Copy Python source code
COPY src/ ./src/
RUN pip install --no-deps -e .

# Copy pre-built Lit frontend from Stage 1
COPY --from=frontend-builder /app/web/dist ./web/dist

# Default demonstration bundles & workspace storage
COPY bundles/ ./bundles/
RUN mkdir -p /app/workspaces

EXPOSE 8080

# Environment defaults
ENV WORKBENCH_HOST="0.0.0.0" \
    WORKBENCH_PORT="8080" \
    WORKBENCH_STATIC_DIR="/app/web/dist" \
    WORKBENCH_BUNDLES_DIR="/app/bundles" \
    WORKBENCH_WORKSPACE_DIR="/app/workspaces"

ENTRYPOINT ["workbench", "serve", "--host", "0.0.0.0", "--port", "8080"]
