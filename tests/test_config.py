"""Tests for configuration management."""

import os

from nodered_mcp.config import Config, get_config, reset_config


class TestConfig:
    def test_defaults(self) -> None:
        """Test default values without env vars."""
        old_url = os.environ.pop("NODE_RED_URL", None)
        old_token = os.environ.pop("NODE_RED_TOKEN", None)
        old_version = os.environ.pop("NODE_RED_API_VERSION", None)

        try:
            cfg = Config()
            assert cfg.url == "http://localhost:1880"
            assert cfg.token == ""
            assert cfg.api_version == "v1"
        finally:
            if old_url:
                os.environ["NODE_RED_URL"] = old_url
            if old_token:
                os.environ["NODE_RED_TOKEN"] = old_token
            if old_version:
                os.environ["NODE_RED_API_VERSION"] = old_version

    def test_env_var_override_url(self, monkeypatch) -> None:
        """Test that Config reads NODE_RED_URL from environment."""
        monkeypatch.setenv("NODE_RED_URL", "http://example.com:1880")
        cfg = Config(_env_file=None)
        assert cfg.url == "http://example.com:1880"

    def test_env_var_override_token(self, monkeypatch) -> None:
        """Test that Config reads NODE_RED_TOKEN from environment."""
        monkeypatch.setenv("NODE_RED_TOKEN", "test-token-123")
        cfg = Config(_env_file=None)
        assert cfg.token == "test-token-123"

    def test_env_var_override_api_version(self, monkeypatch) -> None:
        """Test that Config reads NODE_RED_API_VERSION from environment."""
        monkeypatch.setenv("NODE_RED_API_VERSION", "v2")
        cfg = Config(_env_file=None)
        assert cfg.api_version == "v2"

    def test_env_var_override_all(self, monkeypatch) -> None:
        """Test that Config reads all env vars."""
        monkeypatch.setenv("NODE_RED_URL", "http://custom:8080")
        monkeypatch.setenv("NODE_RED_TOKEN", "custom-token")
        monkeypatch.setenv("NODE_RED_API_VERSION", "v2")
        cfg = Config(_env_file=None)
        assert cfg.url == "http://custom:8080"
        assert cfg.token == "custom-token"
        assert cfg.api_version == "v2"

    def test_env_prefix_case_insensitive(self, monkeypatch) -> None:
        """Verify case_sensitive=False setting works."""
        monkeypatch.setenv("node_red_url", "http://lowercase:1880")
        cfg = Config(_env_file=None)
        assert cfg.url == "http://lowercase:1880"


class TestGetConfig:
    def test_get_config_returns_singleton(self) -> None:
        cfg1 = get_config()
        cfg2 = get_config()
        assert cfg1 is cfg2

    def test_get_config_returns_config_instance(self) -> None:
        cfg = get_config()
        assert isinstance(cfg, Config)

    def test_get_config_with_env_vars(self, monkeypatch) -> None:
        """Test get_config returns instance that respects env vars."""
        monkeypatch.setenv("NODE_RED_URL", "http://singleton-test:1880")
        reset_config()
        cfg = get_config()
        assert cfg.url == "http://singleton-test:1880"


class TestResetConfig:
    def test_reset_config_returns_fresh_instance(self) -> None:
        cfg1 = get_config()
        cfg2 = reset_config()
        assert cfg1 is not cfg2

    def test_reset_config_returns_config_instance(self) -> None:
        cfg = reset_config()
        assert isinstance(cfg, Config)

    def test_reset_config_updates_singleton(self) -> None:
        reset_config()
        cfg1 = get_config()
        reset_config()
        cfg2 = get_config()
        # After reset, get_config should return the new instance
        assert cfg1 is not cfg2

    def test_reset_config_applies_new_env_vars(self, monkeypatch) -> None:
        """Test reset_config picks up changed env vars."""
        monkeypatch.setenv("NODE_RED_URL", "http://first:1880")
        reset_config()
        cfg1 = get_config()
        assert cfg1.url == "http://first:1880"

        monkeypatch.setenv("NODE_RED_URL", "http://second:1880")
        cfg2 = reset_config()
        assert cfg2.url == "http://second:1880"


class TestAuthConfig:
    def test_auth_defaults(self) -> None:
        """Auth fields default to token mode with empty credentials."""
        cfg = Config(_env_file=None)
        assert cfg.auth_method == "token"
        assert cfg.auth_username == ""
        assert cfg.auth_password == ""
        assert cfg.oauth_token_url == ""
        assert cfg.oauth_client_id == ""

    def test_mcp_transport_defaults(self) -> None:
        """MCP server defaults to stdio for local MCP clients."""
        cfg = Config(_env_file=None)
        assert cfg.mcp_transport == "stdio"
        assert cfg.mcp_host == "127.0.0.1"
        assert cfg.mcp_port == 8000

    def test_mcp_transport_http(self, monkeypatch) -> None:
        """MCP server can be configured for HTTP sidecar deployments."""
        monkeypatch.setenv("NODE_RED_MCP_TRANSPORT", "http")
        monkeypatch.setenv("NODE_RED_MCP_HOST", "0.0.0.0")
        monkeypatch.setenv("NODE_RED_MCP_PORT", "9000")
        cfg = Config(_env_file=None)
        assert cfg.mcp_transport == "http"
        assert cfg.mcp_host == "0.0.0.0"
        assert cfg.mcp_port == 9000

    def test_auth_method_basic(self, monkeypatch) -> None:
        monkeypatch.setenv("NODE_RED_AUTH_METHOD", "basic")
        monkeypatch.setenv("NODE_RED_AUTH_USERNAME", "admin")
        monkeypatch.setenv("NODE_RED_AUTH_PASSWORD", "app-password-123")
        cfg = Config(_env_file=None)
        assert cfg.auth_method == "basic"
        assert cfg.auth_username == "admin"
        assert cfg.auth_password == "app-password-123"

    def test_auth_method_oauth(self, monkeypatch) -> None:
        monkeypatch.setenv("NODE_RED_AUTH_METHOD", "oauth")
        monkeypatch.setenv("NODE_RED_AUTH_USERNAME", "svc-account")
        monkeypatch.setenv("NODE_RED_AUTH_PASSWORD", "svc-password")
        monkeypatch.setenv("NODE_RED_OAUTH_TOKEN_URL", "https://auth.example.com/application/o/token/")
        monkeypatch.setenv("NODE_RED_OAUTH_CLIENT_ID", "my-client-id")
        cfg = Config(_env_file=None)
        assert cfg.auth_method == "oauth"
        assert cfg.auth_username == "svc-account"
        assert cfg.auth_password == "svc-password"
        assert cfg.oauth_token_url == "https://auth.example.com/application/o/token/"
        assert cfg.oauth_client_id == "my-client-id"
