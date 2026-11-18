
"""Provider interface for web search integrations."""

from typing import Protocol

from openscout.search.providers.models import SearchResponse


class SearchProvider(Protocol):
    """Interface implemented by all web search providers."""

    @property
    def name(self) -> str:
        """Return the provider identifier."""

    def search(
        self,
        query: str,
        *,
        count: int = 10,
        country: str = "IN",
        search_lang: str = "en",
        offset: int = 0,
    ) -> SearchResponse:
        """Execute a web search and return normalized results."""
