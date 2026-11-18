
"""Brave Search API integration."""

import os
import re
from typing import Any

import httpx

from openscout.search.providers.models import SearchResponse, SearchResult

BRAVE_SEARCH_URL = "https://api.search.brave.com/res/v1/web/search"


class SearchProviderError(Exception):
    """Raised when a search provider cannot complete a request."""


class BraveSearchProvider:
    """Search the web through the Brave Search API."""

    name = "brave"

    def __init__(
        self,
        api_key: str | None = None,
        *,
        timeout: float = 15.0,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self.api_key = (
            api_key or os.getenv("BRAVE_SEARCH_API_KEY", "")
        ).strip()
        self.timeout = timeout
        self.transport = transport

        if not self.api_key:
            raise SearchProviderError(
                "Brave API key is missing. Set BRAVE_SEARCH_API_KEY."
            )

        if timeout <= 0:
            raise ValueError("timeout must be greater than zero.")

    def search(
        self,
        query: str,
        *,
        count: int = 10,
        country: str = "IN",
        search_lang: str = "en",
        offset: int = 0,
    ) -> SearchResponse:
        """Execute a Brave web search."""

        query = self._validate_query(query)
        self._validate_options(count, country, search_lang, offset)

        headers = {
            "Accept": "application/json",
            "Accept-Encoding": "gzip",
            "X-Subscription-Token": self.api_key,
        }

        params = {
            "q": query,
            "count": count,
            "country": country.upper(),
            "search_lang": search_lang.lower(),
            "offset": offset,
            "safesearch": "moderate",
        }

        try:
            with httpx.Client(
                timeout=self.timeout,
                transport=self.transport,
            ) as client:
                response = client.get(
                    BRAVE_SEARCH_URL,
                    headers=headers,
                    params=params,
                )
                response.raise_for_status()

        except httpx.TimeoutException as exc:
            raise SearchProviderError(
                "Brave Search request timed out."
            ) from exc

        except httpx.HTTPStatusError as exc:
            status = exc.response.status_code

            if status in (401, 403):
                message = "Brave Search authentication failed. Check your API key."
            elif status == 429:
                message = "Brave Search rate limit or quota exceeded."
            else:
                message = f"Brave Search returned HTTP {status}."

            raise SearchProviderError(message) from exc

        except httpx.RequestError as exc:
            raise SearchProviderError(
                f"Could not connect to Brave Search: {exc}"
            ) from exc

        try:
            payload = response.json()
        except ValueError as exc:
            raise SearchProviderError(
                "Brave Search returned invalid JSON."
            ) from exc

        return self._normalize_response(
            payload,
            query=query,
            offset=offset,
        )

    @staticmethod
    def _validate_query(query: str) -> str:
        if not isinstance(query, str):
            raise TypeError("query must be a string.")

        query = query.strip()

        if not query:
            raise ValueError("query cannot be empty.")

        if len(query) > 600:
            raise ValueError("query cannot exceed 600 characters.")

        if len(query.split()) > 75:
            raise ValueError("query cannot exceed 75 words.")

        if any(ord(char) < 32 or ord(char) == 127 for char in query):
            raise ValueError("query contains invalid control characters.")

        return query

    @staticmethod
    def _validate_options(
        count: int,
        country: str,
        search_lang: str,
        offset: int,
    ) -> None:
        if isinstance(count, bool) or not isinstance(count, int):
            raise TypeError("count must be an integer.")

        if not 1 <= count <= 20:
            raise ValueError("count must be between 1 and 20.")

        if isinstance(offset, bool) or not isinstance(offset, int):
            raise TypeError("offset must be an integer.")

        if not 0 <= offset <= 9:
            raise ValueError("offset must be between 0 and 9.")

        if not isinstance(country, str) or not re.fullmatch(
            r"[A-Za-z]{2}", country
        ):
            raise ValueError("country must be a two-letter country code.")

        if not isinstance(search_lang, str) or not re.fullmatch(
            r"[A-Za-z]{2,3}", search_lang
        ):
            raise ValueError("search_lang must be a valid language code.")

    @staticmethod
    def _normalize_response(
        payload: Any,
        *,
        query: str,
        offset: int,
    ) -> SearchResponse:
        if not isinstance(payload, dict):
            raise SearchProviderError(
                "Brave Search returned an unexpected response."
            )

        web_data = payload.get("web") or {}

        if not isinstance(web_data, dict):
            raise SearchProviderError(
                "Brave Search returned an invalid web results section."
            )

        raw_results = web_data.get("results") or []

        if not isinstance(raw_results, list):
            raise SearchProviderError(
                "Brave Search returned an invalid results collection."
            )

        results: list[SearchResult] = []

        for item in raw_results:
            if not isinstance(item, dict):
                continue

            title = item.get("title")
            url = item.get("url")

            if not isinstance(title, str) or not isinstance(url, str):
                continue

            if not url.startswith(("https://", "http://")):
                continue

            description = item.get("description") or ""
            page_age = item.get("page_age")
            language = item.get("language")

            results.append(
                SearchResult(
                    title=title,
                    url=url,
                    description=(
                        description if isinstance(description, str) else ""
                    ),
                    page_age=(
                        page_age if isinstance(page_age, str) else None
                    ),
                    language=(
                        language if isinstance(language, str) else None
                    ),
                )
            )

        query_data = payload.get("query") or {}

        if not isinstance(query_data, dict):
            query_data = {}

        return SearchResponse(
            provider="brave",
            query=query,
            results=tuple(results),
            more_results_available=bool(
                query_data.get("more_results_available", False)
            ),
            offset=offset,
        )
