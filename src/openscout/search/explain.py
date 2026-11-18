
"""Explain advanced search queries."""

import re
from dataclasses import dataclass

_OPERATOR_DESCRIPTIONS = {
    "site": "Restricts results to the specified website or domain.",
    "filetype": "Restricts results to a particular file extension.",
    "intitle": "Searches for a term in page titles.",
    "allintitle": "Requires all specified terms in page titles.",
    "inurl": "Searches for a term in page URLs.",
    "allinurl": "Requires all specified terms in page URLs.",
    "intext": "Searches for a term in page content.",
    "allintext": "Requires all specified terms in page content.",
    "before": "Restricts results to pages before the specified date.",
    "after": "Restricts results to pages after the specified date.",
    "related": "Finds websites Google considers related to a domain.",
    "define": "Searches for a definition of a term.",
}

_TOKEN_PATTERN = re.compile(
    r'"[^"]*"'
    r'|\b(?:site|filetype|intitle|allintitle|inurl|allinurl|'
    r'intext|allintext|before|after|related|define):\S+'
    r'|\bOR\b'
    r'|(?<!\S)-\S+'
    r'|\*'
)


@dataclass(frozen=True, slots=True)
class QueryExplanation:
    """A query and its human-readable explanation."""

    query: str
    components: tuple[str, ...]


def explain_query(query: str) -> QueryExplanation:
    """Explain the recognized operators and expressions in a query."""

    if not isinstance(query, str) or not query.strip():
        raise ValueError("Query cannot be empty.")

    if any(ord(char) < 32 or ord(char) == 127 for char in query):
        raise ValueError("Query contains invalid control characters.")

    components: list[str] = []
    tokens = _TOKEN_PATTERN.findall(query)

    if not tokens:
        components.append(
            "No recognized advanced operators. "
            "This appears to be a standard keyword search."
        )

    for token in tokens:
        if token.startswith('"') and token.endswith('"'):
            components.append(
                f"{token}: searches for this exact phrase."
            )
            continue

        if token == "OR":
            components.append(
                "OR: allows results matching either alternative."
            )
            continue

        if token.startswith("-"):
            components.append(
                f"{token}: excludes results containing this term."
            )
            continue

        if token == "*":
            components.append(
                "*: acts as a wildcard in supported phrase searches."
            )
            continue

        if ":" in token:
            operator, value = token.split(":", 1)
            description = _OPERATOR_DESCRIPTIONS.get(operator)

            if description:
                components.append(
                    f"{operator}:{value}: {description}"
                )

    if "(" in query or ")" in query:
        components.append(
            "Parentheses: group parts of the search expression."
        )

    return QueryExplanation(
        query=query.strip(),
        components=tuple(components),
    )
