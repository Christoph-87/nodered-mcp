"""Configuration management for Node-RED MCP."""

from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Config(BaseSettings):
    """Node-RED MCP configuration from environment variables.

    Environment variables use NODE_RED_ prefix:
        NODE_RED_URL, NODE_RED_TOKEN, NODE_RED_API_VERSION
    """

    url: str = "http://localhost:1880"
    token: str = ""
    api_version: str = "v1"

    # Auth method: "token" (default), "basic", "oauth"
    auth_method: str = "token"
    # For basic and oauth: username
    auth_username: str = ""
    # For basic and oauth: password (app password)
    auth_password: str = ""
    # For oauth: token endpoint URL
    oauth_token_url: str = ""
    # For oauth: client ID
    oauth_client_id: str = ""

    # MCP server transport. Use "stdio" for local MCP clients or "http" for
    # container/sidecar deployments.
    mcp_transport: Literal["stdio", "http"] = "stdio"
    mcp_host: str = "127.0.0.1"
    mcp_port: int = 8000

    model_config = SettingsConfigDict(
        env_prefix="NODE_RED_",
        case_sensitive=False,
    )


# Global config instance
_config: Config | None = None


def get_config() -> Config:
    """Get the global config instance.

    Returns:
        Singleton Config instance.
    """
    global _config
    if _config is None:
        _config = Config()
    return _config


def reset_config() -> Config:
    """Reset and return a fresh config instance (for testing).

    Returns:
        New Config instance.
    """
    global _config
    _config = Config()
    return _config
