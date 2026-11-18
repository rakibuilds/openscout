"""Readable content extraction from HTML pages."""

import trafilatura
from bs4 import BeautifulSoup

from openscout.core.results import ScrapeResult


def extract_content(
    html: str,
    url: str,
    output_format: str = "markdown",
) -> ScrapeResult:
    """Extract the main readable content from an HTML document."""

    if output_format not in {"markdown", "text"}:
        raise ValueError("output_format must be 'markdown' or 'text'.")

    soup = BeautifulSoup(html, "html.parser")
    title = soup.title.get_text(" ", strip=True) if soup.title else ""

    extracted = trafilatura.extract(
        html,
        url=url,
        output_format="markdown" if output_format == "markdown" else "txt",
        include_links=True,
        include_images=False,
        favor_precision=True,
    )

    if not extracted:
        for element in soup(["script", "style", "noscript", "svg"]):
            element.decompose()

        extracted = soup.get_text("\n", strip=True)

    return ScrapeResult(
        url=url,
        title=title,
        content=extracted.strip(),
        output_format=output_format,
    )