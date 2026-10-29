"""Configuration settings for now-workbench."""

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
    host: str = "0.0.0.0"
    port: int = 8080
    debug: bool = False

    # Directories
    workspace_dir: Path = Field(default_factory=lambda: Path("./workspaces").resolve())
    bundles_dir: Path = Field(default_factory=lambda: Path("./bundles").resolve())
    static_dir: Path = Field(default_factory=lambda: Path("./web/dist").resolve())

    # ServiceNow Instance Profile
    sn_instance_url: str = Field(default="", description="ServiceNow instance URL")
    sn_username: str = Field(default="", description="ServiceNow user")
    sn_password: str = Field(default="", description="ServiceNow password")
    sn_auth_type: str = Field(default="basic", description="Auth type: basic, oauth, or token")

    # Claude / Otto AI
    anthropic_api_key: str = Field(default="", description="Anthropic Claude API key")
    claude_model: str = Field(default="claude-3-7-sonnet-20250219", description="Claude model")

    # Now SDK
    now_sdk_bin: str = Field(default="now-sdk", description="Path or command for now-sdk")
    node_bin: str = Field(default="node", description="Path or command for node")


settings = Settings()
