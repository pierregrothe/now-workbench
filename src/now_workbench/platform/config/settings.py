"""Configuration settings for now-workbench."""

import os
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings with environment variable overrides."""

    model_config = SettingsConfigDict(
        env_prefix="WORKBENCH_",
        env_file=".env",
        extra="ignore",
    )

    app_name: str = "now-workbench"
    # Loopback by default: the API is unauthenticated and holds instance credentials.
    # Containers opt in explicitly (WORKBENCH_HOST=0.0.0.0 in the Dockerfile/compose).
    host: str = "127.0.0.1"
    port: int = 8080
    # Browser origins allowed by CORS and the WebSocket Origin check (full match).
    cors_origin_regex: str = r"https?://(localhost|127\.0\.0\.1|\[::1\])(:\d+)?"
    debug: bool = False

    # Sign-in (ADR-016, ADR-017). Cloudflare Access authenticates the person (Apple or Google)
    # and attaches a signed token; roles live in the database. With Access unconfigured the
    # server only runs on loopback, as a single local user with both roles.
    access_team_domain: str = Field(default="", description="Access team domain")
    access_audience: str = Field(default="", description="Access application AUD tag")

    # Directories
    workspace_dir: Path = Field(default_factory=lambda: Path("./workspaces").resolve())
    bundles_dir: Path = Field(default_factory=lambda: Path("./bundles").resolve())
    static_dir: Path = Field(default_factory=lambda: Path("./web/dist").resolve())
    data_dir: Path = Field(default_factory=lambda: Path("./data").resolve())

    # ServiceNow Instance Profile
    sn_instance_url: str = Field(default="", description="ServiceNow instance URL")
    sn_username: str = Field(default="", description="ServiceNow user")
    sn_password: str = Field(default="", description="ServiceNow password")
    sn_auth_type: str = Field(default="basic", description="Auth type: basic, oauth, or token")

    # Claude / Otto AI
    anthropic_api_key: str = Field(default="", description="Anthropic Claude API key")
    claude_model: str = Field(default="claude-sonnet-5-5", description="Claude model")

    # Now SDK
    now_sdk_bin: str = Field(default="now-sdk", description="Path or command for now-sdk")
    node_bin: str = Field(default="node", description="Path or command for node")

    # Telemetry (ADR-029): events older than this are purged; at least the longest chart.
    telemetry_retention_days: int = Field(default=365, ge=60, description="Telemetry kept")

    # Backups to an S3-compatible bucket (ADR-029); `workbench backup --s3` uses them.
    backup_s3_bucket: str = Field(default="", description="Bucket name")
    backup_s3_region: str = Field(default="us-east-1", description="Signing region")
    backup_s3_endpoint: str = Field(default="", description="Endpoint; empty means AWS")
    backup_s3_prefix: str = Field(default="now-workbench/", description="Key prefix")
    backup_s3_access_key_id: str = Field(default="", description="Access key id")
    backup_s3_secret_access_key: str = Field(default="", description="Secret access key")

    def get_data_dir(self) -> Path:
        """Return resolved data directory respecting a runtime WORKBENCH_DATA_DIR override.

        ``data_dir`` is captured once at import; reading the environment here lets tests
        and multi-workspace runs redirect storage after the settings object exists.
        """
        env_dir = os.environ.get("WORKBENCH_DATA_DIR")
        if env_dir:
            return Path(env_dir).resolve()
        return self.data_dir

    def get_host(self) -> str:
        """Return the bind host, reading WORKBENCH_HOST at call time (the CLI sets it)."""
        return os.environ.get("WORKBENCH_HOST", self.host)

    def _env_or(self, name: str, fallback: str) -> str:
        return os.environ.get(f"WORKBENCH_{name}", fallback)

    def get_access_team_domain(self) -> str:
        """Return the Access team domain, reading the environment at call time."""
        return self._env_or("ACCESS_TEAM_DOMAIN", self.access_team_domain)

    def get_access_audience(self) -> str:
        """Return the Access application AUD tag, reading the environment at call time."""
        return self._env_or("ACCESS_AUDIENCE", self.access_audience)

    def get_bundles_dir(self) -> Path:
        """Return resolved bundles directory respecting WORKBENCH_BUNDLES_DIR env override."""
        env_dir = os.environ.get("WORKBENCH_BUNDLES_DIR")
        if env_dir:
            return Path(env_dir).resolve()
        return self.bundles_dir


settings = Settings()
