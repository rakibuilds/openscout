
"""Tests for live search CLI integration."""

import pytest
from typer.testing import CliRunner

from openscout.cli.app import app
from openscout.search.providers import (
    SearchProviderError,
    SearchResponse,
    SearchResult,
)

runner = CliRunner()


def test_search_run_with_mocked_provider(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FakeBraveProvider:
        def search(
            self,
            query: str,
            *,
            count: int = 10,
            country: str = "IN",
            search_lang: str = "en",
            offset: int = 0,
        ) -> SearchResponse:
            assert query == "AI web agents"
            assert count == 5
            assert country == "IN"
            assert search_lang == "en"
            assert offset == 0

            return SearchResponse(
                provider="brave",
                query=query,
                results=(
                    SearchResult(
                        title="Example AI Agents",
                        url="https://example.com/agents",
                        description="An example search result.",
                    ),
                ),
            )

    monkeypatch.setattr(
        "openscout.cli.app.BraveSearchProvider",
        FakeBraveProvider,
    )

    result = runner.invoke(
        app,
        [
            "search",
            "run",
            "AI web agents",
            "--provider",
            "brave",
            "--limit",
            "5",
        ],
    )

    assert result.exit_code == 0
    assert "OpenScout Search Results" in result.output
    assert "Example AI Agents" in result.output
    assert "https://example.com/agents" in result.output


def test_search_run_missing_api_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("BRAVE_SEARCH_API_KEY", raising=False)

    result = runner.invoke(
        app,
        ["search", "run", "Python"],
    )

    assert result.exit_code == 2
    assert "API key is missing" in result.output


def test_search_run_rejects_unknown_provider() -> None:
    result = runner.invoke(
        app,
        [
            "search",
            "run",
            "Python",
            "--provider",
            "unknown",
        ],
    )

    assert result.exit_code == 2
    assert "Unsupported provider" in result.output


def test_search_run_handles_provider_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FailingProvider:
        def __init__(self) -> None:
            pass

        def search(
            self,
            *args: object,
            **kwargs: object,
        ) -> SearchResponse:
            raise SearchProviderError("Simulated provider failure.")

    monkeypatch.setattr(
        "openscout.cli.app.BraveSearchProvider",
        FailingProvider,
    )

    result = runner.invoke(
        app,
        ["search", "run", "Python"],
    )

    assert result.exit_code == 2
    assert "Simulated provider failure" in result.output


def test_search_run_handles_empty_results(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class EmptyProvider:
        def search(
            self,
            *args: object,
            **kwargs: object,
        ) -> SearchResponse:
            return SearchResponse(
                provider="brave",
                query="unknown topic",
                results=(),
            )

    monkeypatch.setattr(
        "openscout.cli.app.BraveSearchProvider",
        EmptyProvider,
    )

    result = runner.invoke(
        app,
        ["search", "run", "unknown topic"],
    )

    assert result.exit_code == 0
    assert "No search results found" in result.output
