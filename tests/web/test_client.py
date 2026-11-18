
"""Tests for HTTP fetching and network security."""

import socket

import httpx
import pytest

from openscout.core.config import OpenScoutConfig
from openscout.core.exceptions import (
    FetchError,
    NetworkAccessError,
    ResponseTooLargeError,
)
from openscout.web.client import WebClient


def _dns_result(address: str) -> tuple:
    """Build a socket.getaddrinfo-compatible result."""

    family = socket.AF_INET6 if ":" in address else socket.AF_INET

    port = 443

    return (
        family,
        socket.SOCK_STREAM,
        socket.IPPROTO_TCP,
        "",
        (address, port),
    )


def _make_client(
    monkeypatch: pytest.MonkeyPatch,
    handler,
    *,
    config: OpenScoutConfig | None = None,
    dns_addresses: tuple[str, ...] = ("93.184.216.34",),
) -> WebClient:
    """Create a WebClient using mocked HTTP and DNS."""

    client = WebClient(config=config)
    client.close()

    client._client = httpx.Client(
        transport=httpx.MockTransport(handler),
        follow_redirects=False,
        trust_env=False,
    )

    dns_results = tuple(
        _dns_result(address) for address in dns_addresses
    )

    monkeypatch.setattr(
        "openscout.web.client.socket.getaddrinfo",
        lambda *args, **kwargs: dns_results,
    )

    return client


def test_fetch_successful_response(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Fetch a successful public HTTP response."""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            text="OpenScout test response",
            headers={"content-type": "text/plain"},
            request=request,
        )

    with _make_client(monkeypatch, handler) as client:
        result = client.fetch("https://example.com")

    assert result.status_code == 200
    assert result.content == b"OpenScout test response"
    assert result.url == "https://example.com/"


def test_blocks_redirect_to_localhost(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Reject redirects to localhost before making another request."""

    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)

        return httpx.Response(
            302,
            headers={"location": "http://127.0.0.1"},
            request=request,
        )

    with (
        _make_client(monkeypatch, handler) as client,
        pytest.raises(NetworkAccessError, match="non-public"),
    ):
        client.fetch("https://example.com")

    assert len(requests) == 1


def test_enforces_redirect_limit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Stop following redirects after the configured limit."""

    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)

        return httpx.Response(
            302,
            headers={"location": "/redirect"},
            request=request,
        )

    config = OpenScoutConfig(max_redirects=1)

    with (
        _make_client(
            monkeypatch,
            handler,
            config=config,
        ) as client,
        pytest.raises(FetchError, match="maximum number of redirects"),
    ):
        client.fetch("https://example.com")

    assert len(requests) == 2


def test_blocks_mixed_public_and_private_dns_results(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Reject a hostname if any DNS result is non-public."""

    request_count = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal request_count
        request_count += 1

        return httpx.Response(200, request=request)

    with (
        _make_client(
            monkeypatch,
            handler,
            dns_addresses=("93.184.216.34", "127.0.0.1"),
        ) as client,
        pytest.raises(NetworkAccessError, match="non-public"),
    ):
        client.fetch("https://example.com")

    assert request_count == 0


def test_handles_dns_resolution_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Convert DNS resolution failures into OpenScout errors."""

    def fail_dns(*args, **kwargs):
        raise socket.gaierror("DNS resolution failed")

    monkeypatch.setattr(
        "openscout.web.client.socket.getaddrinfo",
        fail_dns,
    )

    with (
        WebClient() as client,
        pytest.raises(NetworkAccessError, match="Could not resolve"),
    ):
        client.fetch("https://example.com")


def test_rejects_declared_oversized_response(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Reject responses whose declared size exceeds the limit."""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            content=b"12345",
            request=request,
        )

    config = OpenScoutConfig(max_response_bytes=4)

    with (
        _make_client(
            monkeypatch,
            handler,
            config=config,
        ) as client,
        pytest.raises(ResponseTooLargeError),
    ):
        client.fetch("https://example.com")


def test_rejects_oversized_stream_without_content_length(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Enforce the size limit while streaming without Content-Length."""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            stream=httpx.ByteStream(b"12345"),
            request=request,
        )

    config = OpenScoutConfig(max_response_bytes=4)

    with (
        _make_client(
            monkeypatch,
            handler,
            config=config,
        ) as client,
        pytest.raises(ResponseTooLargeError),
    ):
        client.fetch("https://example.com")


@pytest.mark.parametrize(
    "address",
    [
        "127.0.0.1",
        "::1",
        "10.0.0.1",
        "192.168.1.1",
        "169.254.1.1",
        "fc00::1",
        "fe80::1",
    ],
)
def test_blocks_non_public_ip_addresses(
    address: str,
) -> None:
    """Reject private, loopback and link-local IP addresses."""

    with (
        WebClient() as client,
        pytest.raises(NetworkAccessError, match="non-public"),
    ):
        client.fetch(
            f"http://[{address}]"
            if ":" in address
            else f"http://{address}"
        )


def test_private_network_can_be_explicitly_enabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Allow private destinations only with explicit configuration."""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            text="Local development response",
            request=request,
        )

    config = OpenScoutConfig(allow_private_network=True)

    with _make_client(
        monkeypatch,
        handler,
        config=config,
    ) as client:
        result = client.fetch("http://127.0.0.1")

    assert result.status_code == 200
    assert result.content == b"Local development response"
