
"""Ready-made templates for advanced web searches."""

from dataclasses import dataclass, replace

from openscout.search.query_builder import SearchQuery, build_query


@dataclass(frozen=True, slots=True)
class SearchTemplate:
    """A reusable advanced search template."""

    id: str
    name: str
    description: str
    query: SearchQuery


_TEMPLATES: tuple[SearchTemplate, ...] = (
    SearchTemplate(
        id="research-papers",
        name="Research papers",
        description="Find publicly available research papers and academic PDFs.",
        query=SearchQuery(filetype="pdf"),
    ),
    SearchTemplate(
        id="github-projects",
        name="GitHub projects",
        description="Discover public GitHub repositories and projects.",
        query=SearchQuery(site="github.com"),
    ),
    SearchTemplate(
        id="api-documentation",
        name="API documentation",
        description="Find API documentation and developer references.",
        query=SearchQuery(
            any_of=("API documentation", "developer reference"),
        ),
    ),
    SearchTemplate(
        id="public-datasets",
        name="Public datasets",
        description="Discover public datasets and open data resources.",
        query=SearchQuery(
            any_of=("dataset", "open data"),
        ),
    ),
    SearchTemplate(
        id="public-documents",
        name="Public documents",
        description="Find publicly indexed PDF documents.",
        query=SearchQuery(filetype="pdf"),
    ),
    SearchTemplate(
        id="technology-research",
        name="Technology research",
        description="Research public technology stacks and implementation approaches.",
        query=SearchQuery(
            any_of=("technology stack", "built with"),
        ),
    ),
)


def list_templates() -> tuple[SearchTemplate, ...]:
    """Return all available search templates."""

    return _TEMPLATES


def get_template(template_id: str) -> SearchTemplate:
    """Find a template by its ID."""

    normalized = template_id.strip().lower()

    for template in _TEMPLATES:
        if template.id == normalized:
            return template

    raise ValueError(f"Unknown search template: {template_id}")


def build_template_query(
    template_id: str,
    topic: str | None = None,
) -> str:
    """Build a query from a template and an optional research topic."""

    template = get_template(template_id)

    query = replace(
        template.query,
        terms=topic if topic is not None else template.query.terms,
    )

    return build_query(query)
