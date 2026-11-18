
"""Tests for advanced search query building."""

import pytest

from openscout.search.explain import explain_query
from openscout.search.operators import get_operator, list_operators
from openscout.search.query_builder import SearchQuery, build_query
from openscout.search.templates import (
    build_template_query,
    get_template,
    list_templates,
)


def test_builds_basic_query() -> None:
    query = build_query(SearchQuery(terms="machine learning"))

    assert query == '"machine learning"'


def test_builds_combined_query() -> None:
    query = build_query(
        SearchQuery(
            terms="machine learning",
            site="github.com",
            filetype="pdf",
            after="2025-01-01",
        )
    )

    assert query == (
        '"machine learning" site:github.com '
        "filetype:pdf after:2025-01-01"
    )


def test_builds_exact_phrase() -> None:
    query = build_query(
        SearchQuery(exact_phrases=("large language models",))
    )

    assert query == '"large language models"'


def test_builds_or_expression() -> None:
    query = build_query(
        SearchQuery(any_of=("Python", "JavaScript"))
    )

    assert query == "(Python OR JavaScript)"


def test_builds_exclusions() -> None:
    query = build_query(
        SearchQuery(
            terms="jaguar",
            exclude=("car", "vehicle"),
        )
    )

    assert query == "jaguar -car -vehicle"


def test_builds_content_operators() -> None:
    query = build_query(
        SearchQuery(
            terms="developer tools",
            intitle="documentation",
            inurl="api",
            intext="authentication",
        )
    )

    assert query == (
        '"developer tools" '
        'intitle:documentation '
        "inurl:api "
        "intext:authentication"
    )


@pytest.mark.parametrize(
    "query",
    [
        SearchQuery(),
        SearchQuery(terms="   "),
        SearchQuery(site=""),
        SearchQuery(filetype="pdf/"),
        SearchQuery(site="https://example.com"),
        SearchQuery(terms='invalid " quote'),
        SearchQuery(before="not-a-date"),
        SearchQuery(any_of=("Python",)),
    ],
)
def test_rejects_invalid_query_inputs(query: SearchQuery) -> None:
    with pytest.raises(ValueError):
        build_query(query)


def test_rejects_control_characters() -> None:
    with pytest.raises(ValueError, match="control characters"):
        build_query(SearchQuery(terms="hello\nworld"))


def test_rejects_empty_any_of() -> None:
    with pytest.raises(ValueError):
        build_query(SearchQuery(any_of=("Python",)))


def test_lists_operators() -> None:
    operators = list_operators()

    assert len(operators) >= 10
    assert any(operator.name == "site" for operator in operators)


def test_filters_operators_by_category() -> None:
    operators = list_operators("domain")

    assert operators
    assert all(operator.category == "domain" for operator in operators)


def test_get_operator() -> None:
    operator = get_operator("site")

    assert operator is not None
    assert operator.syntax == "site:domain.com"


def test_unknown_operator() -> None:
    assert get_operator("unknown") is None


def test_lists_templates() -> None:
    templates = list_templates()

    assert len(templates) >= 5


def test_get_template() -> None:
    template = get_template("github-projects")

    assert template.name == "GitHub projects"


def test_unknown_template() -> None:
    with pytest.raises(ValueError, match="Unknown search template"):
        get_template("unknown")


def test_build_research_template() -> None:
    query = build_template_query(
        "research-papers",
        "Assamese speech recognition",
    )

    assert query == '"Assamese speech recognition" filetype:pdf'


def test_build_github_template() -> None:
    query = build_template_query(
        "github-projects",
        "local LLM",
    )

    assert query == '"local LLM" site:github.com'


def test_explains_advanced_query() -> None:
    result = explain_query(
        'site:github.com "machine learning" filetype:pdf'
    )

    assert result.query.startswith("site:github.com")
    assert any("website or domain" in item for item in result.components)
    assert any("exact phrase" in item for item in result.components)
    assert any("file extension" in item for item in result.components)


def test_explains_plain_query() -> None:
    result = explain_query("machine learning")

    assert len(result.components) == 1
    assert "standard keyword search" in result.components[0]


def test_rejects_empty_explanation_query() -> None:
    with pytest.raises(ValueError, match="Query cannot be empty"):
        explain_query("")


def test_rejects_control_characters_in_explanation() -> None:
    with pytest.raises(ValueError, match="control characters"):
        explain_query("machine\nlearning")
