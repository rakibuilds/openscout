
"""Tests for OpenScout web CLI commands."""

from typer.testing import CliRunner

from openscout.cli.app import app
from openscout.core.results import FetchResult
from openscout.web.dns import DNSLookupResult, DNSRecord

runner = CliRunner()


def _fetch_result() -> FetchResult:
    return FetchResult(
        url="https://example.com/",
        status_code=200,
        headers={
            "content-type": "text/html; charset=utf-8",
            "content-security-policy": "default-src 'self'",
        },
        content=(
            b"<html><head><title>Example Domain</title></head>"
            b"<body><main><h1>OpenScout Test</h1>"
            b"<p>Web extraction works.</p></main></body></html>"
        ),
        elapsed_ms=125.5,
    )


def test_web_dns_success(monkeypatch) -> None:
    def fake_lookup(domain, timeout, record_types):
        assert domain == "example.com"
        assert timeout == 3.0
        assert record_types == ("A", "MX")

        return DNSLookupResult(
            domain="example.com",
            records=[
                DNSRecord("A", "93.184.216.34", 300),
                DNSRecord("MX", "10 mail.example.com.", 300),
            ],
            errors={},
        )

    monkeypatch.setattr(
        "openscout.cli.web.lookup_dns",
        fake_lookup,
    )

    result = runner.invoke(
        app,
        ["web", "dns", "example.com", "--type", "A", "--type", "MX"],
    )

    assert result.exit_code == 0
    assert "DNS lookup: example.com" in result.output
    assert "93.184.216.34" in result.output
    assert "mail.example.com" in result.output


def test_web_dns_error(monkeypatch) -> None:
    def fake_lookup(*args, **kwargs):
        raise ValueError("Unsupported DNS record type.")

    monkeypatch.setattr(
        "openscout.cli.web.lookup_dns",
        fake_lookup,
    )

    result = runner.invoke(
        app,
        ["web", "dns", "example.com"],
    )

    assert result.exit_code == 2
    assert "DNS error" in result.output


def test_web_fetch_success(monkeypatch) -> None:
    class FakeWebClient:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return None

        def fetch(self, url):
            assert url == "https://example.com"
            return _fetch_result()

    monkeypatch.setattr(
        "openscout.cli.web.WebClient",
        FakeWebClient,
    )

    result = runner.invoke(
        app,
        ["web", "fetch", "https://example.com"],
    )

    assert result.exit_code == 0
    assert "HTTP Fetch Result" in result.output
    assert "Status: 200" in result.output
    assert "Response body" not in result.output


def test_web_fetch_displays_text_body(monkeypatch) -> None:
    class FakeWebClient:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return None

        def fetch(self, url):
            return _fetch_result()

    monkeypatch.setattr(
        "openscout.cli.web.WebClient",
        FakeWebClient,
    )

    result = runner.invoke(
        app,
        [
            "web",
            "fetch",
            "https://example.com",
            "--show-body",
        ],
    )

    assert result.exit_code == 0
    assert "OpenScout Test" in result.output


def test_web_fetch_error(monkeypatch) -> None:
    from openscout.core.exceptions import FetchError

    class FakeWebClient:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return None

        def fetch(self, url):
            raise FetchError("Connection failed.")

    monkeypatch.setattr(
        "openscout.cli.web.WebClient",
        FakeWebClient,
    )

    result = runner.invoke(
        app,
        ["web", "fetch", "https://example.com"],
    )

    assert result.exit_code == 2
    assert "Fetch error" in result.output


def test_web_headers_success(monkeypatch) -> None:
    class FakeWebClient:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return None

        def fetch(self, url):
            return _fetch_result()

    monkeypatch.setattr(
        "openscout.cli.web.WebClient",
        FakeWebClient,
    )

    result = runner.invoke(
        app,
        ["web", "headers", "https://example.com"],
    )

    assert result.exit_code == 0
    assert "HTTP Security Header Audit" in result.output
    assert "present" in result.output


def test_web_scrape_markdown(monkeypatch) -> None:
    class FakeWebClient:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return None

        def fetch(self, url):
            return _fetch_result()

    monkeypatch.setattr(
        "openscout.cli.web.WebClient",
        FakeWebClient,
    )

    result = runner.invoke(
        app,
        ["web", "scrape", "https://example.com"],
    )

    assert result.exit_code == 0
    assert "Example Domain" in result.output
    assert "OpenScout Test" in result.output
    assert "Web extraction works." in result.output


def test_web_scrape_rejects_invalid_format(monkeypatch) -> None:
    class FakeWebClient:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return None

        def fetch(self, url):
            return _fetch_result()

    monkeypatch.setattr(
        "openscout.cli.web.WebClient",
        FakeWebClient,
    )

    result = runner.invoke(
        app,
        [
            "web",
            "scrape",
            "https://example.com",
            "--format",
            "pdf",
        ],
    )

    assert result.exit_code == 2
    assert "output_format" in result.output


def test_web_inspect_success(monkeypatch) -> None:
    class FakeWebClient:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return None

        def fetch(self, url):
            return _fetch_result()

    monkeypatch.setattr(
        "openscout.cli.web.WebClient",
        FakeWebClient,
    )

    result = runner.invoke(
        app,
        ["web", "inspect", "https://example.com"],
    )

    assert result.exit_code == 0
    assert "OpenScout Web Inspection" in result.output
    assert "HTTP Security Header Audit" in result.output
