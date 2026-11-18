
"""Reference library for advanced web search operators."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class SearchOperator:
    """Describe an advanced search operator."""

    name: str
    syntax: str
    description: str
    example: str
    category: str


OPERATORS: tuple[SearchOperator, ...] = (
    SearchOperator(
        "site",
        "site:domain.com",
        "Restrict results to a domain or website.",
        "site:github.com machine learning",
        "domain",
    ),
    SearchOperator(
        "filetype",
        "filetype:pdf",
        "Find documents with a particular file extension.",
        "AI research filetype:pdf",
        "documents",
    ),
    SearchOperator(
        "intitle",
        "intitle:word",
        "Find pages containing a word in the title.",
        "intitle:documentation Python",
        "content",
    ),
    SearchOperator(
        "allintitle",
        "allintitle:word1 word2",
        "Find pages containing all specified words in the title.",
        "allintitle:open source AI tools",
        "content",
    ),
    SearchOperator(
        "inurl",
        "inurl:word",
        "Find pages with a word in their URL.",
        "inurl:docs API",
        "content",
    ),
    SearchOperator(
        "allinurl",
        "allinurl:word1 word2",
        "Find URLs containing all specified words.",
        "allinurl:developer API reference",
        "content",
    ),
    SearchOperator(
        "intext",
        "intext:word",
        "Find pages containing a word in their text.",
        "intext:transformer architecture",
        "content",
    ),
    SearchOperator(
        "allintext",
        "allintext:word1 word2",
        "Find pages containing all specified words in their text.",
        "allintext:machine learning tutorial",
        "content",
    ),
    SearchOperator(
        "before",
        "before:YYYY-MM-DD",
        "Restrict results to pages published before a date.",
        "AI research before:2025-01-01",
        "date",
    ),
    SearchOperator(
        "after",
        "after:YYYY-MM-DD",
        "Restrict results to pages published after a date.",
        "AI research after:2025-01-01",
        "date",
    ),
    SearchOperator(
        "exact phrase",
        '"exact phrase"',
        "Search for an exact phrase.",
        '"large language models"',
        "text",
    ),
    SearchOperator(
        "OR",
        "term1 OR term2",
        "Find results matching either alternative.",
        "Python OR JavaScript",
        "logic",
    ),
    SearchOperator(
        "exclude",
        "-word",
        "Exclude results containing a word or phrase.",
        "jaguar -car",
        "logic",
    ),
    SearchOperator(
        "wildcard",
        "*",
        "Use a wildcard within an exact-phrase search.",
        '"best * framework"',
        "text",
    ),
    SearchOperator(
        "grouping",
        "(term1 OR term2)",
        "Group alternative search expressions.",
        "(Python OR JavaScript) tutorial",
        "logic",
    ),
    SearchOperator(
        "related",
        "related:domain.com",
        "Find websites Google considers related to a domain.",
        "related:example.com",
        "domain",
    ),
    SearchOperator(
        "define",
        "define:word",
        "Look for a definition of a term.",
        "define:machine learning",
        "reference",
    ),
)


def list_operators(category: str | None = None) -> tuple[SearchOperator, ...]:
    """Return all operators or filter them by category."""

    if category is None:
        return OPERATORS

    normalized = category.strip().lower()

    return tuple(
        operator
        for operator in OPERATORS
        if operator.category == normalized
    )


def get_operator(name: str) -> SearchOperator | None:
    """Find an operator by its name."""

    normalized = name.strip().lower()

    return next(
        (
            operator
            for operator in OPERATORS
            if operator.name.lower() == normalized
        ),
        None,
    )
