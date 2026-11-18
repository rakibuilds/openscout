
"""Normalized models for search provider results."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class SearchResult:
    """A normalized web search result."""

    title: str
    url: str
    description: str = ""
    page_age: str | None = None
    language: str | None = None


@dataclass(frozen=True, slots=True)
class SearchResponse:
    """Normalized response returned by a search provider."""

    provider: str
    query: str
    results: tuple[SearchResult, ...]
    more_results_available: bool = False
    offset: int = 0
