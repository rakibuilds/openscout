
"""OpenScout command-line application."""

from dataclasses import asdict

import typer
from rich.console import Console
from rich.table import Table
from rich.text import Text

from openscout import __version__
from openscout.cli.web import app as web_app
from openscout.search.explain import explain_query
from openscout.search.operators import list_operators
from openscout.search.providers import (
    BraveSearchProvider,
    SearchProviderError,
)
from openscout.search.query_builder import SearchQuery, build_query
from openscout.search.templates import get_template, list_templates

app = typer.Typer(
    name="openscout",
    help="Explore. Extract. Process. Automate.",
    no_args_is_help=True,
)

search_app = typer.Typer(
    name="search",
    help="Build and execute advanced web searches.",
    no_args_is_help=True,
)

app.add_typer(search_app, name="search")
app.add_typer(web_app, name="web")

console = Console()

EXACT_OPTION = typer.Option(
    [],
    "--exact",
    help="Require an exact phrase. Can be repeated.",
)

EXCLUDE_OPTION = typer.Option(
    [],
    "--exclude",
    help="Exclude a word or phrase. Can be repeated.",
)

ANY_OF_OPTION = typer.Option(
    [],
    "--any-of",
    help="Include an alternative search term. Can be repeated.",
)


@app.command()
def version() -> None:
    """Show the installed OpenScout version."""
    console.print(f"OpenScout [bold cyan]{__version__}[/bold cyan]")


@search_app.command("operators")
def search_operators(
    category: str | None = typer.Option(
        None,
        "--category",
        "-c",
        help="Filter operators by category.",
    ),
) -> None:
    """List supported advanced search operators."""
    operators = list_operators(category=category)

    if not operators:
        console.print("[yellow]No matching search operators found.[/yellow]")
        return

    table = Table(title="Advanced search operators")
    table.add_column("Operator", style="cyan")
    table.add_column("Syntax", style="green")
    table.add_column("Category")
    table.add_column("Description")
    table.add_column("Example")

    for operator in operators:
        table.add_row(
            operator.name,
            operator.syntax,
            operator.category,
            operator.description,
            operator.example,
        )

    console.print(table)


@search_app.command("templates")
def search_templates() -> None:
    """List available search query templates."""
    templates = list_templates()

    if not templates:
        console.print("[yellow]No search templates available.[/yellow]")
        return

    table = Table(title="Search query templates")
    table.add_column("ID", style="cyan")
    table.add_column("Name", style="green")
    table.add_column("Description")

    for template in templates:
        table.add_row(
            template.id,
            template.name,
            template.description,
        )

    console.print(table)


@search_app.command("build")
def search_build(
    topic: str = typer.Argument(
        ...,
        help="Topic or keywords to search for.",
    ),
    template: str | None = typer.Option(
        None,
        "--template",
        "-t",
        help="Optional search template ID.",
    ),
    site: str | None = typer.Option(
        None,
        "--site",
        help="Restrict results to a domain.",
    ),
    filetype: str | None = typer.Option(
        None,
        "--filetype",
        help="Restrict results to a file extension.",
    ),
    intitle: str | None = typer.Option(
        None,
        "--intitle",
        help="Require words in the page title.",
    ),
    inurl: str | None = typer.Option(
        None,
        "--inurl",
        help="Require words in the page URL.",
    ),
    intext: str | None = typer.Option(
        None,
        "--intext",
        help="Require words in the page text.",
    ),
    before: str | None = typer.Option(
        None,
        "--before",
        help="Restrict results before YYYY-MM-DD.",
    ),
    after: str | None = typer.Option(
        None,
        "--after",
        help="Restrict results after YYYY-MM-DD.",
    ),
    exact: list[str] = EXACT_OPTION,
    exclude: list[str] = EXCLUDE_OPTION,
    any_of: list[str] = ANY_OF_OPTION,
) -> None:
    """Build an advanced search query."""
    try:
        if template:
            base = get_template(template).query

            query = SearchQuery(
                terms=topic,
                site=site or base.site,
                filetype=filetype or base.filetype,
                intitle=intitle or base.intitle,
                inurl=inurl or base.inurl,
                intext=intext or base.intext,
                before=before or base.before,
                after=after or base.after,
                exact_phrases=tuple(exact) or base.exact_phrases,
                exclude=tuple(exclude) or base.exclude,
                any_of=tuple(any_of) or base.any_of,
            )
        else:
            query = SearchQuery(
                terms=topic,
                site=site,
                filetype=filetype,
                intitle=intitle,
                inurl=inurl,
                intext=intext,
                before=before,
                after=after,
                exact_phrases=tuple(exact),
                exclude=tuple(exclude),
                any_of=tuple(any_of),
            )

        generated = build_query(query)

        console.print("[bold green]Generated search query[/bold green]")
        console.print(generated)

    except (ValueError, TypeError) as exc:
        console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(code=2) from exc


@search_app.command("run")
def search_run(
    query: str = typer.Argument(
        ...,
        help="Search query. Supports advanced search operators.",
    ),
    provider: str = typer.Option(
        "brave",
        "--provider",
        "-p",
        help="Search provider.",
    ),
    limit: int = typer.Option(
        10,
        "--limit",
        "-n",
        min=1,
        max=20,
        help="Maximum number of results (1-20).",
    ),
    country: str = typer.Option(
        "IN",
        "--country",
        help="Two-letter country code.",
    ),
    language: str = typer.Option(
        "en",
        "--language",
        help="Search language code.",
    ),
    offset: int = typer.Option(
        0,
        "--offset",
        min=0,
        max=9,
        help="Pagination offset (0-9).",
    ),
) -> None:
    """Execute a web search using a configured provider."""
    provider = provider.strip().lower()

    if provider != "brave":
        console.print(
            f"[red]Error:[/red] Unsupported provider: {provider}. "
            "Currently supported: brave."
        )
        raise typer.Exit(code=2)

    try:
        search_provider = BraveSearchProvider()

        response = search_provider.search(
            query,
            count=limit,
            country=country,
            search_lang=language,
            offset=offset,
        )

    except (SearchProviderError, ValueError, TypeError) as exc:
        console.print(f"[red]Search error:[/red] {exc}")
        raise typer.Exit(code=2) from exc

    console.print()
    console.print("[bold green]OpenScout Search Results[/bold green]")
    console.print(f"Provider: {response.provider}")
    console.print(f"Query: {response.query}")
    console.print(f"Results: {len(response.results)}")
    console.print()

    if not response.results:
        console.print("[yellow]No search results found.[/yellow]")
        return

    table = Table(title="Web search results")
    table.add_column("#", style="dim", width=4)
    table.add_column("Title", style="cyan", min_width=20)
    table.add_column("Description", min_width=30)

    for index, result in enumerate(response.results, start=1):
        table.add_row(
            str(index),
            Text(result.title),
            Text(result.description or "No description available."),
        )

    console.print(table)

    console.print("\n[bold]Result URLs[/bold]")

    for index, result in enumerate(response.results, start=1):
        console.print(
            Text(f"{index}. {result.url}", no_wrap=True),
            soft_wrap=True,
        )

    if response.more_results_available:
        console.print(
            "\n[dim]More results may be available. "
            "Use --offset to retrieve another page.[/dim]"
        )


@search_app.command("explain")
def search_explain(
    query: str = typer.Argument(
        ...,
        help="Search query to explain.",
    ),
) -> None:
    """Explain the operators and structure of a search query."""
    try:
        explanation = explain_query(query)
    except ValueError as exc:
        console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(code=2) from exc

    table = Table(title="Search query explanation")
    table.add_column("Property", style="cyan")
    table.add_column("Explanation")

    for key, value in asdict(explanation).items():
        table.add_row(
            key.replace("_", " ").title(),
            str(value),
        )

    console.print(table)


if __name__ == "__main__":
    app()
