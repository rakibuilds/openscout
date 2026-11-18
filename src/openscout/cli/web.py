
"""Web intelligence commands for OpenScout."""

import json
from collections.abc import Sequence
from pathlib import Path
from typing import Annotated
from urllib.parse import urlsplit

import typer
from rich.console import Console
from rich.table import Table

from openscout.core.exceptions import OpenScoutError
from openscout.core.results import FetchResult
from openscout.web.client import WebClient
from openscout.web.dns import (
    SUPPORTED_RECORD_TYPES,
    lookup_dns,
)
from openscout.web.domain import lookup_domain
from openscout.web.headers import audit_security_headers
from openscout.web.inspect import InspectionResult, inspect_domain
from openscout.web.scraper import extract_content

DNS_RECORD_TYPES_OPTION = typer.Option(
    None,
    "--type",
    "-t",
    help="DNS record type. Repeat to request multiple types.",
)

DNS_TIMEOUT_OPTION = typer.Option(
    3.0,
    "--timeout",
    min=0.1,
    help="DNS lookup timeout in seconds.",
)

app = typer.Typer(
    name="web",
    help="Web intelligence, inspection, and data extraction.",
    no_args_is_help=True,
)

console = Console()


def _fetch(url: str) -> FetchResult:
    """Fetch a URL using the shared OpenScout HTTP client."""

    with WebClient() as client:
        return client.fetch(url)


def _decode_content(result: FetchResult) -> str:
    """Decode a fetched response as readable text."""

    return result.content.decode("utf-8", errors="replace")


def _show_response_summary(result: FetchResult) -> None:
    """Display common HTTP response information."""

    console.print(f"[bold]URL:[/bold] {result.url}")
    console.print(f"[bold]Status:[/bold] {result.status_code}")
    console.print(
        f"[bold]Content type:[/bold] {result.content_type or 'Unknown'}"
    )
    console.print(f"[bold]Size:[/bold] {len(result.content):,} bytes")
    console.print(f"[bold]Duration:[/bold] {result.elapsed_ms:.2f} ms")


def _show_header_findings(url: str, headers: dict[str, str]) -> None:
    """Display security-header observations."""

    findings = audit_security_headers(headers, url)

    table = Table(title="HTTP Security Header Audit")
    table.add_column("Header", style="cyan")
    table.add_column("Status")
    table.add_column("Value")
    table.add_column("Recommendation")

    styles = {
        "present": "green",
        "missing": "yellow",
        "not_applicable": "dim",
    }

    for finding in findings:
        status_style = styles.get(finding.status, "white")

        table.add_row(
            finding.name,
            f"[{status_style}]{finding.status}[/{status_style}]",
            finding.value or "—",
            finding.recommendation,
        )

    console.print(table)


def _inspection_target(value: str) -> tuple[str, str | None]:
    """Separate a domain from an optional HTTP(S) URL."""

    if "://" not in value:
        return value, None

    parsed = urlsplit(value)

    if parsed.scheme.lower() not in {"http", "https"}:
        raise ValueError("Inspection supports only HTTP and HTTPS URLs.")

    if not parsed.hostname:
        raise ValueError("The supplied URL does not contain a valid hostname.")

    return parsed.hostname, value


def _show_section_status(result: InspectionResult) -> None:
    """Display the status of each inspection subsystem."""

    table = Table(title="Inspection Overview")
    table.add_column("Subsystem", style="cyan")
    table.add_column("Status")
    table.add_column("Details")

    sections = [
        ("DNS", result.dns),
        ("RDAP Registration", result.registration),
        ("HTTP", result.http),
        ("TLS", result.tls),
        ("Security Headers", result.security_headers),
    ]

    styles = {
        "ok": "green",
        "partial": "yellow",
        "error": "red",
        "skipped": "dim",
    }

    for name, section in sections:
        style = styles.get(section.status, "white")
        table.add_row(
            name,
            f"[{style}]{section.status}[/{style}]",
            section.error or "—",
        )

    console.print(table)


def _show_dns_section(result: InspectionResult) -> None:
    """Display DNS inspection results."""

    if result.dns.data is None:
        return

    dns_result = result.dns.data

    if not dns_result.records:
        console.print("[yellow]No DNS records returned.[/yellow]")
        return

    table = Table(title="DNS Records")
    table.add_column("Type", style="cyan")
    table.add_column("Value")
    table.add_column("TTL", justify="right")

    for record in dns_result.records:
        table.add_row(
            record.record_type,
            record.value,
            str(record.ttl) if record.ttl is not None else "—",
        )

    console.print(table)


def _show_registration_section(result: InspectionResult) -> None:
    """Display RDAP registration information."""

    if result.registration.data is None:
        return

    data = result.registration.data

    table = Table(title="RDAP Registration Information")
    table.add_column("Field", style="cyan")
    table.add_column("Value")

    fields = [
        ("Domain", data.domain),
        ("Registrar", data.registrar),
        ("Registered", data.registered),
        ("Expires", data.expires),
        ("Last updated", data.updated),
        ("Registry", data.registry),
        ("Status", ", ".join(data.statuses)),
        ("Nameservers", ", ".join(data.nameservers)),
    ]

    for name, value in fields:
        table.add_row(name, value or "—")

    console.print(table)


def _show_http_section(result: InspectionResult) -> None:
    """Display HTTP inspection information."""

    if result.http.data is None:
        return

    console.print("\n[bold]HTTP Response[/bold]")
    _show_response_summary(result.http.data)

    redirects = result.http.data.redirects

    if redirects:
        table = Table(title="Redirect History")
        table.add_column("Status", justify="right")
        table.add_column("From")
        table.add_column("To")

        for redirect in redirects:
            table.add_row(
                str(redirect.status_code),
                redirect.url,
                redirect.location,
            )

        console.print(table)


def _show_tls_section(result: InspectionResult) -> None:
    """Display TLS certificate information."""

    if result.tls.data is None:
        return

    data = result.tls.data

    table = Table(title="TLS Certificate Information")
    table.add_column("Field", style="cyan")
    table.add_column("Value")

    fields = [
        ("Domain", data.domain),
        ("Port", str(data.port)),
        ("Subject", data.subject),
        ("Issuer", data.issuer),
        ("Valid from", data.not_before),
        ("Valid until", data.not_after),
        (
            "Days remaining",
            str(data.days_remaining)
            if data.days_remaining is not None
            else None,
        ),
        ("TLS version", data.tls_version),
        ("Cipher", data.cipher),
        ("Verified", str(data.verified)),
        ("Subject alternative names", ", ".join(data.subject_alt_names)),
    ]

    for name, value in fields:
        table.add_row(name, value or "—")

    console.print(table)


def _show_inspection(result: InspectionResult) -> None:
    """Display the complete unified inspection report."""

    overall_styles = {
        "ok": "green",
        "partial": "yellow",
        "error": "red",
    }
    style = overall_styles.get(result.status, "white")

    console.print(
        "\n[bold green]OpenScout Web Inspection[/bold green]\n"
    )
    console.print(f"[bold]Domain:[/bold] {result.domain}")
    console.print(
        f"[bold]Overall status:[/bold] [{style}]{result.status}[/{style}]\n"
    )

    _show_section_status(result)
    console.print()

    _show_dns_section(result)
    console.print()

    _show_registration_section(result)
    console.print()

    _show_http_section(result)
    console.print()

    _show_tls_section(result)
    console.print()

    if result.http.data is not None:
        _show_header_findings(
            result.http.data.url,
            result.http.data.headers,
        )


@app.command("dns")
def web_dns(
    domain: str = typer.Argument(..., help="Domain name to inspect."),
    record_types: list[str] = DNS_RECORD_TYPES_OPTION,
    timeout: float = DNS_TIMEOUT_OPTION,
) -> None:
    """Look up public DNS records for a domain."""

    try:
        requested_types: Sequence[str] = (
            tuple(record_types)
            if record_types
            else SUPPORTED_RECORD_TYPES
        )

        result = lookup_dns(
            domain,
            timeout=timeout,
            record_types=tuple(requested_types),
        )

    except (OpenScoutError, ValueError) as exc:
        console.print(f"[red]DNS error:[/red] {exc}")
        raise typer.Exit(code=2) from exc

    console.print(f"\n[bold green]DNS lookup: {result.domain}[/bold green]")

    if result.records:
        table = Table(title="DNS Records")
        table.add_column("Type", style="cyan")
        table.add_column("Value")
        table.add_column("TTL", justify="right")

        for record in result.records:
            table.add_row(
                record.record_type,
                record.value,
                str(record.ttl) if record.ttl is not None else "—",
            )

        console.print(table)
    else:
        console.print("[yellow]No DNS records returned.[/yellow]")

    if result.errors:
        console.print("\n[bold yellow]Lookup notices[/bold yellow]")

        for record_type, message in result.errors.items():
            console.print(f"{record_type}: {message}")


@app.command("domain")
def web_domain(
    domain: str = typer.Argument(
        ...,
        help="Domain name to inspect.",
    ),
    timeout: float = typer.Option(
        5.0,
        "--timeout",
        min=0.1,
        help="RDAP request timeout in seconds.",
    ),
) -> None:
    """Retrieve domain registration information through RDAP."""

    try:
        result = lookup_domain(domain, timeout=timeout)

    except (OpenScoutError, ValueError) as exc:
        console.print(f"[red]Domain lookup error:[/red] {exc}")
        raise typer.Exit(code=2) from exc

    console.print(
        f"\n[bold green]Domain registration: {result.domain}[/bold green]"
    )

    table = Table(title="RDAP Registration Information")
    table.add_column("Field", style="cyan")
    table.add_column("Value")

    fields = [
        ("Domain", result.domain),
        ("Registrar", result.registrar),
        ("Registered", result.registered),
        ("Expires", result.expires),
        ("Last updated", result.updated),
        ("Registry", result.registry),
        ("Status", ", ".join(result.statuses)),
        ("Nameservers", ", ".join(result.nameservers)),
    ]

    for name, value in fields:
        table.add_row(name, value or "—")

    console.print(table)

    if result.events:
        event_table = Table(title="Registration Events")
        event_table.add_column("Event", style="cyan")
        event_table.add_column("Date")

        for event in result.events:
            event_table.add_row(event.action, event.date)

        console.print(event_table)


@app.command("headers")
def web_headers(
    url: str = typer.Argument(..., help="HTTP or HTTPS URL to inspect."),
) -> None:
    """Inspect HTTP security headers on a public web page."""

    try:
        result = _fetch(url)
    except (OpenScoutError, ValueError) as exc:
        console.print(f"[red]Fetch error:[/red] {exc}")
        raise typer.Exit(code=2) from exc

    console.print("\n[bold green]HTTP Header Inspection[/bold green]")
    _show_response_summary(result)
    console.print()
    _show_header_findings(result.url, result.headers)


@app.command("fetch")
def web_fetch(
    url: str = typer.Argument(..., help="URL to fetch."),
    show_body: bool = typer.Option(
        False,
        "--show-body",
        help="Print the response body when it is text-based.",
    ),
) -> None:
    """Fetch a public URL and display response information."""

    try:
        result = _fetch(url)
    except (OpenScoutError, ValueError) as exc:
        console.print(f"[red]Fetch error:[/red] {exc}")
        raise typer.Exit(code=2) from exc

    console.print("\n[bold green]HTTP Fetch Result[/bold green]")
    _show_response_summary(result)

    if show_body:
        content_type = result.content_type.lower()

        readable = (
            content_type.startswith("text/")
            or "json" in content_type
            or "xml" in content_type
            or "javascript" in content_type
        )

        if not readable:
            console.print(
                "\n[yellow]Body display skipped: "
                "response does not appear to be text-based.[/yellow]"
            )
            return

        console.print("\n[bold]Response body[/bold]")
        console.print(_decode_content(result), soft_wrap=True)


@app.command("scrape")
def web_scrape(
    url: str = typer.Argument(..., help="Public web page URL."),
    output_format: str = typer.Option(
        "markdown",
        "--format",
        case_sensitive=False,
        help="Extraction format: markdown or text.",
    ),
) -> None:
    """Extract readable content from a public web page."""

    try:
        fetched = _fetch(url)

        content_type = fetched.content_type.lower()
        if content_type and not (
            "html" in content_type
            or "xhtml" in content_type
        ):
            console.print(
                f"[yellow]Warning: expected HTML, received "
                f"{content_type}.[/yellow]"
            )

        result = extract_content(
            html=_decode_content(fetched),
            url=fetched.url,
            output_format=output_format.lower(),
        )

    except (OpenScoutError, ValueError) as exc:
        console.print(f"[red]Scraping error:[/red] {exc}")
        raise typer.Exit(code=2) from exc

    console.print(
        f"\n[bold green]{result.title or 'Extracted content'}[/bold green]"
    )
    console.print(f"[dim]{result.url}[/dim]\n")
    console.print(result.content, soft_wrap=True)



@app.command("inspect")
def web_inspect(
    target: str = typer.Argument(
        ...,
        help="Domain name or HTTP(S) URL to inspect.",
    ),
    json_output: bool = typer.Option(
        False,
        "--json",
        help="Print the inspection report as JSON.",
    ),
    output: Annotated[
        Path | None,
        typer.Option(
            "--output",
            "-o",
            help="Write the JSON inspection report to a file.",
        ),
    ] = None,
) -> None:
    """Inspect DNS, RDAP, HTTP, TLS, and security headers."""

    try:
        domain, http_url = _inspection_target(target)

        result = inspect_domain(
            domain,
            http_url=http_url,
        )

        payload = json.dumps(
            result.to_dict(),
            indent=2,
            ensure_ascii=False,
        )

        if output is not None:
            output.write_text(
                payload + "\n",
                encoding="utf-8",
            )

        if json_output:
            typer.echo(payload)
        elif output is not None:
            console.print(
                f"[green]Inspection report saved to:[/green] {output}"
            )
        else:
            _show_inspection(result)

    except (OpenScoutError, ValueError, OSError) as exc:
        console.print(f"[red]Inspection error:[/red] {exc}")
        raise typer.Exit(code=2) from exc
