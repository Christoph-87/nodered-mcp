"""Node-RED HTTP API client."""

import time
from typing import Any

import httpx

from nodered_mcp.config import get_config


class NodeRedClient:
    """Async HTTP client for Node-RED Admin HTTP API.

    Supports three authentication methods:
        - token: Static bearer token (default)
        - basic: HTTP Basic auth (for forward auth proxies)
        - oauth: OAuth2 client credentials grant with auto-refresh
    """

    def __init__(
        self,
        base_url: str,
        api_version: str = "v1",
        auth_method: str = "token",
        token: str = "",
        auth_username: str = "",
        auth_password: str = "",
        oauth_token_url: str = "",
        oauth_client_id: str = "",
    ) -> None:
        """Initialize the Node-RED client.

        Args:
            base_url: Base URL of the Node-RED instance (e.g. http://localhost:1880)
            api_version: API version header value (default: v1)
            auth_method: Authentication method - "token", "basic", or "oauth"
            token: Bearer token for auth_method="token"
            auth_username: Username for auth_method="basic" or "oauth"
            auth_password: Password/app password for auth_method="basic" or "oauth"
            oauth_token_url: OAuth2 token endpoint URL for auth_method="oauth"
            oauth_client_id: OAuth2 client ID for auth_method="oauth"
        """
        self._auth_method = auth_method
        headers: dict[str, str] = {"Node-RED-API-Version": api_version}
        auth: httpx.BasicAuth | None = None

        if auth_method == "token" and token:
            headers["Authorization"] = f"Bearer {token}"
        elif auth_method == "basic":
            auth = httpx.BasicAuth(auth_username, auth_password)
        elif auth_method == "oauth":
            self._oauth_token_url = oauth_token_url
            self._oauth_client_id = oauth_client_id
            self._auth_username = auth_username
            self._auth_password = auth_password
            self._oauth_token: str | None = None
            self._oauth_expiry: float = 0.0

        self._http = httpx.AsyncClient(
            base_url=base_url,
            headers=headers,
            auth=auth,
            timeout=30.0,
        )

    async def _ensure_oauth_token(self) -> None:
        """Fetch or refresh OAuth2 token via client credentials grant."""
        if self._oauth_token and time.time() < self._oauth_expiry - 30:
            return

        async with httpx.AsyncClient(timeout=10.0) as auth_client:
            resp = await auth_client.post(
                self._oauth_token_url,
                data={
                    "grant_type": "client_credentials",
                    "client_id": self._oauth_client_id,
                    "username": self._auth_username,
                    "password": self._auth_password,
                },
            )

        if resp.status_code != 200:
            raise RuntimeError(
                f"OAuth token error {resp.status_code}: {resp.text}"
            )

        token_data = resp.json()
        self._oauth_token = token_data["access_token"]
        self._oauth_expiry = time.time() + token_data.get("expires_in", 600)
        self._http.headers["Authorization"] = f"Bearer {self._oauth_token}"

    async def _request(
        self,
        method: str,
        path: str,
        data: Any = None,
        headers: dict[str, str] | None = None,
    ) -> Any:
        """Centralized HTTP request handler.

        Args:
            method: HTTP method (GET, POST, PUT, DELETE)
            path: API path (e.g. /flows)
            data: Optional request body (will be JSON-encoded)
            headers: Optional per-request headers to merge

        Returns:
            Parsed JSON response, or None for 204 No Content

        Raises:
            RuntimeError: On HTTP error status
        """
        if self._auth_method == "oauth":
            await self._ensure_oauth_token()

        request_headers = headers or {}
        response = await self._http.request(
            method,
            path,
            json=data,
            headers=request_headers,
        )

        # OAuth 401 retry: token may have been revoked server-side
        if response.status_code == 401 and self._auth_method == "oauth":
            self._oauth_token = None
            await self._ensure_oauth_token()
            response = await self._http.request(
                method,
                path,
                json=data,
                headers=request_headers,
            )

        if response.status_code == 204:
            return None

        if response.status_code >= 400:
            raise RuntimeError(
                f"Node-RED API error {response.status_code}: {response.text}"
            )

        return response.json()

    async def close(self) -> None:
        """Close the HTTP client."""
        await self._http.aclose()

    # Flow endpoints
    async def get_flows(self) -> list[dict]:
        """Get all flows (flat array of tabs/subflows/nodes).

        Returns:
            List of flow objects (heterogeneous: tabs, subflows, nodes)
        """
        return await self._request("GET", "/flows")

    async def update_flows(
        self, flows: list[dict], deployment_type: str = "full"
    ) -> None:
        """Update all flows with deployment type.

        Args:
            flows: Full flow configuration
            deployment_type: Deployment type (full, nodes, flows, reload)
        """
        headers = {"Node-RED-Deployment-Type": deployment_type}
        await self._request("POST", "/flows", data=flows, headers=headers)

    async def get_flow(self, flow_id: str) -> dict:
        """Get a single flow by ID.

        Args:
            flow_id: Flow ID

        Returns:
            Flow object with nodes, configs, subflows
        """
        return await self._request("GET", f"/flow/{flow_id}")

    async def update_flow(self, flow_id: str, flow: dict) -> None:
        """Update a single flow.

        Args:
            flow_id: Flow ID
            flow: Flow configuration
        """
        await self._request("PUT", f"/flow/{flow_id}", data=flow)

    async def create_flow(self, flow: dict) -> dict:
        """Create a new flow.

        Args:
            flow: Flow configuration

        Returns:
            Created flow with id field
        """
        return await self._request("POST", "/flow", data=flow)

    async def delete_flow(self, flow_id: str) -> None:
        """Delete a flow.

        Args:
            flow_id: Flow ID
        """
        await self._request("DELETE", f"/flow/{flow_id}")

    async def get_flows_state(self) -> dict:
        """Get the current flows runtime state.

        Returns:
            State object with state field
        """
        return await self._request("GET", "/flows/state")

    async def set_flows_state(self, state: str) -> dict:
        """Set the flows runtime state.

        Args:
            state: Target state (start, stop)

        Returns:
            New state object
        """
        return await self._request("POST", "/flows/state", data={"state": state})

    # Node endpoints
    async def get_nodes(self) -> list[dict]:
        """Get list of installed node modules.

        Returns:
            List of NodeSet objects
        """
        return await self._request("GET", "/nodes")

    async def get_node_info(self, module: str) -> dict:
        """Get info about a specific node module.

        Args:
            module: Module name

        Returns:
            NodeModule object
        """
        return await self._request("GET", f"/nodes/{module}")

    async def toggle_node_module(self, module: str, enabled: bool) -> dict:
        """Enable or disable a node module.

        Args:
            module: Module name
            enabled: True to enable, False to disable

        Returns:
            Updated NodeModule object
        """
        return await self._request("PUT", f"/nodes/{module}", data={"enabled": enabled})

    async def inject(self, node_id: str) -> None:
        """Trigger an inject node.

        Args:
            node_id: Node ID to inject
        """
        await self._request("POST", f"/inject/{node_id}")

    # Settings endpoints
    async def get_settings(self) -> dict:
        """Get Node-RED runtime settings.

        Returns:
            Settings object
        """
        return await self._request("GET", "/settings")

    async def get_diagnostics(self) -> dict:
        """Get Node-RED diagnostics information.

        Returns:
            Diagnostics object (structure varies)
        """
        return await self._request("GET", "/diagnostics")


def _build_client(config: Any) -> NodeRedClient:
    """Build a NodeRedClient from a config instance."""
    return NodeRedClient(
        base_url=config.url,
        api_version=config.api_version,
        auth_method=config.auth_method,
        token=config.token,
        auth_username=config.auth_username,
        auth_password=config.auth_password,
        oauth_token_url=config.oauth_token_url,
        oauth_client_id=config.oauth_client_id,
    )


# Global client instance
_client: NodeRedClient | None = None


def get_client() -> NodeRedClient:
    """Get the global NodeRedClient instance.

    Returns:
        Singleton NodeRedClient instance.
    """
    global _client
    if _client is None:
        _client = _build_client(get_config())
    return _client


async def reset_client() -> NodeRedClient:
    """Reset and return a fresh client instance (for testing).

    Closes the old client if it exists to prevent connection leaks.

    Returns:
        New NodeRedClient instance.
    """
    global _client
    if _client is not None:
        await _client.close()

    _client = _build_client(get_config())
    return _client


def initialize_client(config: Any) -> NodeRedClient:
    """Explicit client initialization with a config instance.

    Args:
        config: Config instance with url, token, api_version, auth fields

    Returns:
        Initialized NodeRedClient instance.
    """
    global _client
    _client = _build_client(config)
    return _client
