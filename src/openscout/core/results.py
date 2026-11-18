
"""Typed result objects shared by OpenScout modules."""

from dataclasses import dataclass, field


@dataclass(slots=True)
class RedirectHop:
    """One HTTP redirect followed by the client."""

    url: str
    status_code: int
    location: str


@dataclass(slots=True)
class FetchResult:
    """Result of an HTTP fetch operation."""

    url: str
    status_code: int
    headers: dict[str, str]
    content: bytes
    elapsed_ms: float
    redirects: list[RedirectHop] = field(default_factory=list)

    @property
    def content_type(self) -> str:
        """Return the response content type."""
        return self.headers.get("content-type", "")


@dataclass(slots=True)
class ScrapeResult:
    """Readable content extracted from a web page."""

    url: str
    title: str
    content: str
    output_format: str
