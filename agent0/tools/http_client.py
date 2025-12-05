#!/usr/bin/env python3
"""
Agent0 HTTP Client Tool.

Provides HTTP capabilities for agents:
- GET/POST/PUT/DELETE requests
- JSON and form data handling
- Authentication support
- Response parsing
- Rate limiting

Usage:
    from agent0.tools.http_client import http_get, http_post, HTTPClient

    # Simple requests
    result = http_get("https://api.example.com/data")
    result = http_post("https://api.example.com/submit", data={"key": "value"})

    # Advanced usage
    client = HTTPClient(base_url="https://api.example.com")
    client.set_auth("Bearer", "token123")
    result = client.get("/users")
"""
from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Union
from urllib.parse import urljoin

logger = logging.getLogger(__name__)


@dataclass
class HTTPResponse:
    """Structured HTTP response."""
    status_code: int
    body: Union[str, Dict[str, Any], List[Any]]
    headers: Dict[str, str]
    latency_ms: float
    url: str
    success: bool
    error: Optional[str] = None

    def json(self) -> Optional[Dict[str, Any]]:
        """Get body as JSON dict."""
        if isinstance(self.body, dict):
            return self.body
        if isinstance(self.body, str):
            try:
                return json.loads(self.body)
            except json.JSONDecodeError:
                return None
        return None

    def text(self) -> str:
        """Get body as text."""
        if isinstance(self.body, str):
            return self.body
        return json.dumps(self.body)


class RateLimiter:
    """Simple rate limiter for HTTP requests."""

    def __init__(self, requests_per_second: float = 10.0):
        self.min_interval = 1.0 / requests_per_second
        self.last_request = 0.0

    def wait(self) -> None:
        """Wait if necessary to respect rate limit."""
        now = time.time()
        elapsed = now - self.last_request
        if elapsed < self.min_interval:
            time.sleep(self.min_interval - elapsed)
        self.last_request = time.time()


class HTTPClient:
    """
    Full-featured HTTP client for agent use.

    Features:
    - Base URL support
    - Authentication (Bearer, Basic, API Key)
    - Rate limiting
    - Timeout handling
    - Response parsing
    """

    def __init__(
        self,
        base_url: str = "",
        timeout: int = 30,
        rate_limit: float = 10.0,
        default_headers: Dict[str, str] = None,
    ):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.rate_limiter = RateLimiter(rate_limit)
        self.headers = {
            "User-Agent": "Agent0/0.2.0",
            "Accept": "application/json",
        }
        if default_headers:
            self.headers.update(default_headers)

        self._auth_type = None
        self._auth_value = None

    def set_auth(self, auth_type: str, value: str) -> None:
        """
        Set authentication.

        Args:
            auth_type: "bearer", "basic", "api_key", or header name
            value: Token, credentials, or API key
        """
        self._auth_type = auth_type.lower()
        self._auth_value = value

        if self._auth_type == "bearer":
            self.headers["Authorization"] = f"Bearer {value}"
        elif self._auth_type == "basic":
            import base64
            encoded = base64.b64encode(value.encode()).decode()
            self.headers["Authorization"] = f"Basic {encoded}"
        elif self._auth_type == "api_key":
            self.headers["X-API-Key"] = value
        else:
            # Custom header
            self.headers[auth_type] = value

    def _build_url(self, path: str) -> str:
        """Build full URL from path."""
        if path.startswith("http"):
            return path
        return urljoin(self.base_url + "/", path.lstrip("/"))

    def _make_request(
        self,
        method: str,
        url: str,
        data: Any = None,
        params: Dict[str, str] = None,
        headers: Dict[str, str] = None,
    ) -> HTTPResponse:
        """Make HTTP request."""
        try:
            import requests
        except ImportError:
            return HTTPResponse(
                status_code=0,
                body="",
                headers={},
                latency_ms=0,
                url=url,
                success=False,
                error="requests library not installed"
            )

        full_url = self._build_url(url)
        req_headers = {**self.headers}
        if headers:
            req_headers.update(headers)

        # Rate limiting
        self.rate_limiter.wait()

        start_time = time.time()

        try:
            # Prepare request kwargs
            kwargs = {
                "timeout": self.timeout,
                "headers": req_headers,
            }

            if params:
                kwargs["params"] = params

            if data:
                if isinstance(data, dict):
                    kwargs["json"] = data
                else:
                    kwargs["data"] = data

            # Make request
            response = requests.request(method, full_url, **kwargs)
            latency_ms = (time.time() - start_time) * 1000

            # Parse body
            try:
                body = response.json()
            except (json.JSONDecodeError, ValueError):
                body = response.text

            return HTTPResponse(
                status_code=response.status_code,
                body=body,
                headers=dict(response.headers),
                latency_ms=latency_ms,
                url=full_url,
                success=200 <= response.status_code < 300,
            )

        except requests.exceptions.Timeout:
            latency_ms = (time.time() - start_time) * 1000
            return HTTPResponse(
                status_code=0,
                body="",
                headers={},
                latency_ms=latency_ms,
                url=full_url,
                success=False,
                error="Request timed out"
            )

        except requests.exceptions.ConnectionError as e:
            latency_ms = (time.time() - start_time) * 1000
            return HTTPResponse(
                status_code=0,
                body="",
                headers={},
                latency_ms=latency_ms,
                url=full_url,
                success=False,
                error=f"Connection error: {e}"
            )

        except Exception as e:
            latency_ms = (time.time() - start_time) * 1000
            return HTTPResponse(
                status_code=0,
                body="",
                headers={},
                latency_ms=latency_ms,
                url=full_url,
                success=False,
                error=str(e)
            )

    def get(
        self,
        url: str,
        params: Dict[str, str] = None,
        headers: Dict[str, str] = None,
    ) -> HTTPResponse:
        """HTTP GET request."""
        return self._make_request("GET", url, params=params, headers=headers)

    def post(
        self,
        url: str,
        data: Any = None,
        headers: Dict[str, str] = None,
    ) -> HTTPResponse:
        """HTTP POST request."""
        return self._make_request("POST", url, data=data, headers=headers)

    def put(
        self,
        url: str,
        data: Any = None,
        headers: Dict[str, str] = None,
    ) -> HTTPResponse:
        """HTTP PUT request."""
        return self._make_request("PUT", url, data=data, headers=headers)

    def delete(
        self,
        url: str,
        headers: Dict[str, str] = None,
    ) -> HTTPResponse:
        """HTTP DELETE request."""
        return self._make_request("DELETE", url, headers=headers)

    def patch(
        self,
        url: str,
        data: Any = None,
        headers: Dict[str, str] = None,
    ) -> HTTPResponse:
        """HTTP PATCH request."""
        return self._make_request("PATCH", url, data=data, headers=headers)


# Simple function wrappers for direct use
_default_client = HTTPClient()


def http_get(
    url: str,
    params: Dict[str, str] = None,
    headers: Dict[str, str] = None,
    timeout: int = 30,
) -> Dict[str, Any]:
    """
    Simple HTTP GET request.

    Returns dict with status, body, headers, etc.
    """
    client = HTTPClient(timeout=timeout)
    response = client.get(url, params=params, headers=headers)

    return {
        "status": "ok" if response.success else "error",
        "status_code": response.status_code,
        "body": response.body,
        "headers": response.headers,
        "latency_ms": response.latency_ms,
        "error": response.error,
    }


def http_post(
    url: str,
    data: Any = None,
    headers: Dict[str, str] = None,
    timeout: int = 30,
) -> Dict[str, Any]:
    """
    Simple HTTP POST request.

    Returns dict with status, body, headers, etc.
    """
    client = HTTPClient(timeout=timeout)
    response = client.post(url, data=data, headers=headers)

    return {
        "status": "ok" if response.success else "error",
        "status_code": response.status_code,
        "body": response.body,
        "headers": response.headers,
        "latency_ms": response.latency_ms,
        "error": response.error,
    }


def fetch_json(url: str, timeout: int = 30) -> Dict[str, Any]:
    """Fetch JSON from URL."""
    result = http_get(url, timeout=timeout)
    if result["status"] == "ok" and isinstance(result["body"], dict):
        return result["body"]
    return {"error": result.get("error", "Failed to fetch JSON")}


def fetch_text(url: str, timeout: int = 30) -> str:
    """Fetch text content from URL."""
    result = http_get(url, timeout=timeout)
    if result["status"] == "ok":
        body = result["body"]
        return body if isinstance(body, str) else json.dumps(body)
    return f"Error: {result.get('error', 'Unknown error')}"
