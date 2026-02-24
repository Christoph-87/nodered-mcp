"""Tests for NodeRedClient."""

from unittest.mock import AsyncMock, patch

import httpx
import pytest

from nodered_mcp.client import NodeRedClient, get_client, reset_client


class TestNodeRedClient:
    def test_init_without_token(self) -> None:
        client = NodeRedClient(base_url="http://localhost:1880", api_version="v1")
        assert client._http.base_url == httpx.URL("http://localhost:1880")
        assert client._http.headers["Node-RED-API-Version"] == "v1"
        assert "Authorization" not in client._http.headers

    def test_init_with_token(self) -> None:
        client = NodeRedClient(
            base_url="http://localhost:1880",
            token="test-token",
            api_version="v1",
        )
        assert client._http.headers["Authorization"] == "Bearer test-token"
        assert client._http.headers["Node-RED-API-Version"] == "v1"

    def test_init_with_custom_api_version(self) -> None:
        client = NodeRedClient(
            base_url="http://localhost:1880",
            api_version="v2",
        )
        assert client._http.headers["Node-RED-API-Version"] == "v2"

    @pytest.mark.asyncio
    async def test_request_success_with_json(self) -> None:
        from unittest.mock import MagicMock

        client = NodeRedClient(base_url="http://localhost:1880")
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"id": "test"}

        with patch.object(client._http, "request", new_callable=AsyncMock, return_value=mock_response):
            result = await client._request("GET", "/flows")
            assert result == {"id": "test"}

    @pytest.mark.asyncio
    async def test_request_204_no_content(self) -> None:
        client = NodeRedClient(base_url="http://localhost:1880")
        mock_response = AsyncMock()
        mock_response.status_code = 204

        with patch.object(client._http, "request", return_value=mock_response):
            result = await client._request("DELETE", "/flow/test")
            assert result is None

    @pytest.mark.asyncio
    async def test_request_400_error(self) -> None:
        client = NodeRedClient(base_url="http://localhost:1880")
        mock_response = AsyncMock()
        mock_response.status_code = 400
        mock_response.text = "Bad Request"

        with patch.object(client._http, "request", return_value=mock_response):
            with pytest.raises(RuntimeError, match="Node-RED API error 400: Bad Request"):
                await client._request("GET", "/flows")

    @pytest.mark.asyncio
    async def test_request_404_error(self) -> None:
        client = NodeRedClient(base_url="http://localhost:1880")
        mock_response = AsyncMock()
        mock_response.status_code = 404
        mock_response.text = "Not Found"

        with patch.object(client._http, "request", return_value=mock_response):
            with pytest.raises(RuntimeError, match="Node-RED API error 404: Not Found"):
                await client._request("GET", "/flow/nonexistent")

    @pytest.mark.asyncio
    async def test_request_500_error(self) -> None:
        client = NodeRedClient(base_url="http://localhost:1880")
        mock_response = AsyncMock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"

        with patch.object(client._http, "request", return_value=mock_response):
            with pytest.raises(RuntimeError, match="Node-RED API error 500"):
                await client._request("POST", "/flows")

    @pytest.mark.asyncio
    async def test_request_with_data(self) -> None:
        from unittest.mock import MagicMock

        client = NodeRedClient(base_url="http://localhost:1880")
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"success": True}

        with patch.object(client._http, "request", new_callable=AsyncMock, return_value=mock_response) as mock_req:
            await client._request("POST", "/flow", data={"label": "Test"})
            mock_req.assert_called_once_with(
                "POST", "/flow", json={"label": "Test"}, headers={}
            )

    @pytest.mark.asyncio
    async def test_request_with_extra_headers(self) -> None:
        from unittest.mock import MagicMock

        client = NodeRedClient(base_url="http://localhost:1880")
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {}

        with patch.object(client._http, "request", new_callable=AsyncMock, return_value=mock_response) as mock_req:
            await client._request(
                "POST", "/flows", data=[], headers={"Node-RED-Deployment-Type": "full"}
            )
            mock_req.assert_called_once_with(
                "POST",
                "/flows",
                json=[],
                headers={"Node-RED-Deployment-Type": "full"},
            )

    @pytest.mark.asyncio
    async def test_update_flows_passes_deployment_type_header(self) -> None:
        client = NodeRedClient(base_url="http://localhost:1880")
        mock_response = AsyncMock()
        mock_response.status_code = 204

        with patch.object(client._http, "request", return_value=mock_response) as mock_req:
            await client.update_flows(flows=[{"id": "test"}], deployment_type="nodes")
            mock_req.assert_called_once()
            call_args = mock_req.call_args
            assert call_args[1]["headers"]["Node-RED-Deployment-Type"] == "nodes"

    @pytest.mark.asyncio
    async def test_close(self) -> None:
        client = NodeRedClient(base_url="http://localhost:1880")
        with patch.object(client._http, "aclose", new_callable=AsyncMock) as mock_close:
            await client.close()
            mock_close.assert_called_once()


class TestGetClient:
    @pytest.mark.asyncio
    async def test_get_client_returns_singleton(self) -> None:
        # Reset to ensure clean state
        await reset_client()
        c1 = get_client()
        c2 = get_client()
        assert c1 is c2

    @pytest.mark.asyncio
    async def test_get_client_returns_noderedclient(self) -> None:
        await reset_client()
        client = get_client()
        assert isinstance(client, NodeRedClient)

    @pytest.mark.asyncio
    async def test_get_client_uses_config(self) -> None:
        with patch("nodered_mcp.client.get_config") as mock_get_config:
            mock_config = AsyncMock()
            mock_config.url = "http://test:1880"
            mock_config.token = "test-token"
            mock_config.api_version = "v1"
            mock_config.auth_method = "token"
            mock_config.auth_username = ""
            mock_config.auth_password = ""
            mock_config.oauth_token_url = ""
            mock_config.oauth_client_id = ""
            mock_get_config.return_value = mock_config

            await reset_client()
            client = get_client()
            assert client._http.base_url == httpx.URL("http://test:1880")
            assert client._http.headers["Authorization"] == "Bearer test-token"


class TestResetClient:
    @pytest.mark.asyncio
    async def test_reset_client_returns_fresh_instance(self) -> None:
        c1 = get_client()
        c2 = await reset_client()
        assert c1 is not c2

    @pytest.mark.asyncio
    async def test_reset_client_closes_old_client(self) -> None:
        client = get_client()
        with patch.object(client, "close", new_callable=AsyncMock) as mock_close:
            await reset_client()
            mock_close.assert_called_once()

    @pytest.mark.asyncio
    async def test_reset_client_returns_noderedclient(self) -> None:
        client = await reset_client()
        assert isinstance(client, NodeRedClient)

    @pytest.mark.asyncio
    async def test_reset_client_updates_singleton(self) -> None:
        await reset_client()
        c1 = get_client()
        c2 = await reset_client()
        c3 = get_client()
        # After reset, get_client should return the new instance
        assert c1 is not c3
        assert c2 is c3


class TestBasicAuth:
    def test_init_basic_auth(self) -> None:
        """Basic auth sets httpx.BasicAuth on the client."""
        client = NodeRedClient(
            base_url="http://localhost:1880",
            auth_method="basic",
            auth_username="user",
            auth_password="secret",
        )
        assert client._auth_method == "basic"
        assert client._http._auth is not None
        # No static Authorization header — BasicAuth sends it per-request
        assert "Authorization" not in client._http.headers

    def test_init_basic_auth_no_token_header(self) -> None:
        """Basic auth mode ignores static token."""
        client = NodeRedClient(
            base_url="http://localhost:1880",
            auth_method="basic",
            auth_username="user",
            auth_password="pass",
            token="should-be-ignored",
        )
        assert "Authorization" not in client._http.headers


class TestOAuthAuth:
    def test_init_oauth_no_initial_auth(self) -> None:
        """OAuth mode has no Authorization header at init."""
        client = NodeRedClient(
            base_url="http://localhost:1880",
            auth_method="oauth",
            auth_username="user",
            auth_password="pass",
            oauth_token_url="https://auth.example.com/application/o/token/",
            oauth_client_id="my-client-id",
        )
        assert client._auth_method == "oauth"
        assert client._oauth_token is None
        assert "Authorization" not in client._http.headers

    @pytest.mark.asyncio
    async def test_oauth_token_fetch(self) -> None:
        """OAuth fetches token on first request."""
        from unittest.mock import MagicMock

        client = NodeRedClient(
            base_url="http://localhost:1880",
            auth_method="oauth",
            auth_username="user",
            auth_password="pass",
            oauth_token_url="https://auth.example.com/token",
            oauth_client_id="client-id",
        )

        # Mock the token endpoint response
        token_response = MagicMock()
        token_response.status_code = 200
        token_response.json.return_value = {
            "access_token": "jwt-token-123",
            "expires_in": 600,
        }

        with patch("nodered_mcp.client.httpx.AsyncClient") as mock_auth_cls:
            mock_auth_client = AsyncMock()
            mock_auth_client.post.return_value = token_response
            mock_auth_client.__aenter__ = AsyncMock(return_value=mock_auth_client)
            mock_auth_client.__aexit__ = AsyncMock(return_value=None)
            mock_auth_cls.return_value = mock_auth_client

            await client._ensure_oauth_token()

        assert client._oauth_token == "jwt-token-123"
        assert client._oauth_expiry > 0
        assert client._http.headers["Authorization"] == "Bearer jwt-token-123"

    @pytest.mark.asyncio
    async def test_oauth_token_cached(self) -> None:
        """OAuth doesn't re-fetch valid token."""
        import time

        client = NodeRedClient(
            base_url="http://localhost:1880",
            auth_method="oauth",
            auth_username="user",
            auth_password="pass",
            oauth_token_url="https://auth.example.com/token",
            oauth_client_id="client-id",
        )
        # Pre-set a valid token
        client._oauth_token = "cached-token"
        client._oauth_expiry = time.time() + 300  # 5 min from now

        with patch("nodered_mcp.client.httpx.AsyncClient") as mock_cls:
            await client._ensure_oauth_token()
            # Should NOT have created a new client (no fetch needed)
            mock_cls.assert_not_called()

        assert client._oauth_token == "cached-token"

    @pytest.mark.asyncio
    async def test_oauth_token_refresh_when_expired(self) -> None:
        """OAuth re-fetches when token is expired."""
        from unittest.mock import MagicMock

        client = NodeRedClient(
            base_url="http://localhost:1880",
            auth_method="oauth",
            auth_username="user",
            auth_password="pass",
            oauth_token_url="https://auth.example.com/token",
            oauth_client_id="client-id",
        )
        # Set an expired token
        client._oauth_token = "old-token"
        client._oauth_expiry = 0.0

        token_response = MagicMock()
        token_response.status_code = 200
        token_response.json.return_value = {
            "access_token": "new-token",
            "expires_in": 600,
        }

        with patch("nodered_mcp.client.httpx.AsyncClient") as mock_auth_cls:
            mock_auth_client = AsyncMock()
            mock_auth_client.post.return_value = token_response
            mock_auth_client.__aenter__ = AsyncMock(return_value=mock_auth_client)
            mock_auth_client.__aexit__ = AsyncMock(return_value=None)
            mock_auth_cls.return_value = mock_auth_client

            await client._ensure_oauth_token()

        assert client._oauth_token == "new-token"

    @pytest.mark.asyncio
    async def test_oauth_token_error(self) -> None:
        """OAuth raises RuntimeError on token endpoint failure."""
        from unittest.mock import MagicMock

        client = NodeRedClient(
            base_url="http://localhost:1880",
            auth_method="oauth",
            auth_username="user",
            auth_password="pass",
            oauth_token_url="https://auth.example.com/token",
            oauth_client_id="client-id",
        )

        error_response = MagicMock()
        error_response.status_code = 401
        error_response.text = "invalid_client"

        with patch("nodered_mcp.client.httpx.AsyncClient") as mock_auth_cls:
            mock_auth_client = AsyncMock()
            mock_auth_client.post.return_value = error_response
            mock_auth_client.__aenter__ = AsyncMock(return_value=mock_auth_client)
            mock_auth_client.__aexit__ = AsyncMock(return_value=None)
            mock_auth_cls.return_value = mock_auth_client

            with pytest.raises(RuntimeError, match="OAuth token error 401"):
                await client._ensure_oauth_token()

    @pytest.mark.asyncio
    async def test_oauth_401_retry(self) -> None:
        """OAuth retries once on 401 from Node-RED."""
        from unittest.mock import MagicMock
        import time

        client = NodeRedClient(
            base_url="http://localhost:1880",
            auth_method="oauth",
            auth_username="user",
            auth_password="pass",
            oauth_token_url="https://auth.example.com/token",
            oauth_client_id="client-id",
        )
        # Pre-set a "valid" but actually revoked token
        client._oauth_token = "revoked-token"
        client._oauth_expiry = time.time() + 300

        # First response: 401, second response: 200
        response_401 = MagicMock()
        response_401.status_code = 401
        response_401.text = "Unauthorized"

        response_200 = MagicMock()
        response_200.status_code = 200
        response_200.json.return_value = {"id": "test"}

        with patch.object(
            client._http, "request", new_callable=AsyncMock,
            side_effect=[response_401, response_200],
        ):
            # Mock the token refresh
            token_response = MagicMock()
            token_response.status_code = 200
            token_response.json.return_value = {
                "access_token": "new-token",
                "expires_in": 600,
            }

            with patch("nodered_mcp.client.httpx.AsyncClient") as mock_auth_cls:
                mock_auth_client = AsyncMock()
                mock_auth_client.post.return_value = token_response
                mock_auth_client.__aenter__ = AsyncMock(return_value=mock_auth_client)
                mock_auth_client.__aexit__ = AsyncMock(return_value=None)
                mock_auth_cls.return_value = mock_auth_client

                result = await client._request("GET", "/flows")

        assert result == {"id": "test"}
        assert client._oauth_token == "new-token"
