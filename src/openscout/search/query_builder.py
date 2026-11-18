
"""Build advanced search queries from structured inputs."""

import re
from dataclasses import dataclass
from datetime import date

_FILETYPE_PATTERN = re.compile(r"^[a-zA-Z0-9]{1,12}$")
_DOMAIN_PATTERN = re.compile(
    r"^(?:\*\.)?[a-zA-Z0-9](?:[a-zA-Z0-9.-]*[a-zA-Z0-9])?$"
)


def _clean(value: str, field: str) -> str:
    """Normalize and validate a search value."""

    if not isinstance(value, str):
        raise TypeError(f"{field} must be a string.")

    normalized = value.strip()

    if not normalized:
        raise ValueError(f"{field} cannot be empty.")

    if any(ord(char) < 32 or ord(char) == 127 for char in normalized):
        raise ValueError(f"{field} contains invalid control characters.")

    return normalized


def _format_term(value: str) -> str:
    """Quote multi-word terms when necessary."""

    value = _clean(value, "Search term")

    if '"' in value:
        raise ValueError("Search terms cannot contain double quotes.")

    if any(char.isspace() for char in value):
        return f'"{value}"'

    return value


def _format_phrase(value: str) -> str:
    """Format an exact phrase."""

    value = _clean(value, "Exact phrase")

    if '"' in value:
        raise ValueError("Exact phrases cannot contain double quotes.")

    return f'"{value}"'


@dataclass(frozen=True, slots=True)
class SearchQuery:
    """Structured inputs for an advanced search query."""

    terms: str | None = None
    site: str | None = None
    filetype: str | None = None
    intitle: str | None = None
    inurl: str | None = None
    intext: str | None = None
    before: str | None = None
    after: str | None = None
    exact_phrases: tuple[str, ...] = ()
    exclude: tuple[str, ...] = ()
    any_of: tuple[str, ...] = ()


def build_query(query: SearchQuery) -> str:
    """Build a Google-compatible advanced search query."""

    parts: list[str] = []

    if query.terms:
        parts.append(_format_term(query.terms))

    if query.site:
        site = _clean(query.site, "Site")

        if not _DOMAIN_PATTERN.fullmatch(site):
            raise ValueError("Site must be a valid domain name.")

        parts.append(f"site:{site}")

    if query.filetype:
        filetype = _clean(query.filetype, "File type")

        if not _FILETYPE_PATTERN.fullmatch(filetype):
            raise ValueError("File type must contain only letters and numbers.")

        parts.append(f"filetype:{filetype.lower()}")

    for field, operator in (
        (query.intitle, "intitle"),
        (query.inurl, "inurl"),
        (query.intext, "intext"),
    ):
        if field:
            parts.append(f"{operator}:{_format_term(field)}")

    if query.after:
        after = _clean(query.after, "After date")
        date.fromisoformat(after)
        parts.append(f"after:{after}")

    if query.before:
        before = _clean(query.before, "Before date")
        date.fromisoformat(before)
        parts.append(f"before:{before}")

    for phrase in query.exact_phrases:
        parts.append(_format_phrase(phrase))

    if query.any_of:
        alternatives = " OR ".join(
            _format_term(term) for term in query.any_of
        )

        if len(query.any_of) < 2:
            raise ValueError("any_of requires at least two alternatives.")

        parts.append(f"({alternatives})")

    for excluded in query.exclude:
        parts.append(f"-{_format_term(excluded)}")

    if not parts:
        raise ValueError("At least one search condition is required.")

    return " ".join(parts)
