
"""Tests for search provider integrations."""

import httpx
import pytest

from openscout.search.providers import (
    BraveSearchProvider,
    SearchProviderError,
)


def mock_transport(
    handler: httpx.MockTransport,
) -> httpx.MockTransport:
    return handler


def test_brave_search_normalizes_results() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.params["q"] == "AI agents"
        assert request.headers["X-Subscription-Token"] == "test-key"
        assert request.url.params["country"] == "IN"

        return httpx.Response(
            200,
            json={
                "query": {"more_results_available": True},
                "web": {
                    "results": [
                        {
                            "title": "Example AI Agents",
                            "url": "https://example.com/agents",
                            "description": "An example description.",
                            "page_age": "2026-01-01",
                            "language": "en",
                        }
                    ]
                },
            },
        )

    provider = BraveSearchProvider(
        "test-key",
        transport=mock_transport(httpx.MockTransport(handler)),
    )

    response = provider.search("AI agents")

    assert response.provider == "brave"
    assert response.query == "AI agents"
    assert response.more_results_available is True
    assert len(response.results) == 1
    assert response.results[0].title == "Example AI Agents"
    assert response.results[0].url == "https://example.com/agents"
    assert response.results[0].description == "An example description."


def test_brave_search_uses_pagination_options() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.params["count"] == "5"
        assert request.url.params["offset"] == "2"

        return httpx.Response(
            200,
            json={"web": {"results": []}},
        )

    provider = BraveSearchProvider(
        "test-key",
        transport=httpx.MockTransport(handler),
    )

    response = provider.search(
        "Python",
        count=5,
        offset=2,
    )

    assert response.offset == 2
    assert response.results == ()


def test_brave_search_requires_api_key() -> None:
    with pytest.raises(SearchProviderError, match="API key is missing"):
        BraveSearchProvider(api_key="")


@pytest.mark.parametrize(
    ("query", "error"),
    [
        ("", "query cannot be empty"),
        ("   ", "query cannot be empty"),
        ("x" * 601, "600 characters"),
        ("invalid\nquery", "control characters"),
    ],
)
def test_brave_search_rejects_invalid_query(
    query: str,
    error: str,
) -> None:
    provider = BraveSearchProvider("test-key")

    with pytest.raises(ValueError, match=error):
        provider.search(query)


@pytest.mark.parametrize(
    ("count", "offset"),
    [
        (0, 0),
        (21, 0),
        (10, -1),
        (10, 10),
    ],
)
def test_brave_search_rejects_invalid_pagination(
    count: int,
    offset: int,
) -> None:
    provider = BraveSearchProvider("test-key")

    with pytest.raises(ValueError):
        provider.search(
            "Python",
            count=count,
            offset=offset,
        )


def test_brave_search_handles_authentication_error() -> None:
    transport = httpx.MockTransport(
        lambda request: httpx.Response(401)
    )

    provider = BraveSearchProvider(
        "invalid-key",
        transport=transport,
    )

    with pytest.raises(
        SearchProviderError,
        match="authentication failed",
    ):
        provider.search("Python")


def test_brave_search_handles_rate_limit() -> None:
    transport = httpx.MockTransport(
        lambda request: httpx.Response(429)
    )

    provider = BraveSearchProvider(
        "test-key",
        transport=transport,
    )

    with pytest.raises(
        SearchProviderError,
        match="rate limit or quota exceeded",
    ):
        provider.search("Python")


def test_brave_search_handles_invalid_json() -> None:
    transport = httpx.MockTransport(
        lambda request: httpx.Response(
            200,
            content=b"not-json",
        )
    )

    provider = BraveSearchProvider(
        "test-key",
        transport=transport,
    )

    with pytest.raises(
        SearchProviderError,
        match="invalid JSON",
    ):
        provider.search("Python")


def test_brave_search_skips_malformed_results() -> None:
    transport = httpx.MockTransport(
        lambda request: httpx.Response(
            200,
            json={
                "web": {
                    "results": [
                        {
                            "title": "Valid",
                            "url": "https://example.com",
                        },
                        {
                            "title": "Invalid URL",
                            "url": "javascript:alert(1)",
                        },
                        {"title": "Missing URL"},
                        "invalid-result",
                    ]
                }
            },
        )
    )

    provider = BraveSearchProvider(
        "test-key",
        transport=transport,
    )

    response = provider.search("Python")

    assert len(response.results) == 1
    assert response.results[0].title == "Valid"
