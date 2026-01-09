"""Configuration management for the Twitter Reply Agent."""

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass
class Config:
    """Agent configuration loaded from environment variables."""

    # X API credentials
    x_client_id: str
    x_client_secret: str
    x_access_token: str
    x_access_token_secret: str

    # Tavily API
    tavily_api_key: str

    # Codebase path for searching
    product_repo_path: Path

    # Anthropic API (used by Claude Agent SDK)
    anthropic_api_key: str

    # Product name for system prompt
    product_name: str

    @classmethod
    def from_env(cls) -> "Config":
        """Load configuration from environment variables."""
        return cls(
            x_client_id=os.environ["X_CLIENT_ID"],
            x_client_secret=os.environ["X_CLIENT_SECRET"],
            x_access_token=os.environ["X_ACCESS_TOKEN"],
            x_access_token_secret=os.environ["X_ACCESS_TOKEN_SECRET"],
            tavily_api_key=os.environ["TAVILY_API_KEY"],
            product_repo_path=Path(os.environ.get("PRODUCT_REPO_PATH", ".")),
            anthropic_api_key=os.environ["ANTHROPIC_API_KEY"],
            product_name=os.environ.get("PRODUCT_NAME", "our product"),
        )


def _get_config() -> Config:
    """Get the global configuration instance."""
    return Config.from_env()


config = None


def get_config() -> Config:
    """Get or initialize the global configuration."""
    global config
    if config is None:
        config = _get_config()
    return config
