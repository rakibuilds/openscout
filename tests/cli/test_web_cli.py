
"""Tests for the OpenScout web CLI commands."""

import json

from typer.testing import CliRunner

from openscout.cli.app import app
from openscout.core.results import FetchResult
from openscout.web.dns import DNSLookupResult, DNSRecord
from openscout.web.domain import DomainLookupResult
from openscout.web.headers import audit_security_headers
from openscout.web.inspect import InspectionResult, InspectionSection
from openscout.web.tls import TLSInspectionResult

runner = CliRunner()


def _fetch_result() -> FetchResult:
    """Return a reusable HTML response for CLI tests."""
    return FetchResult(
        url="https://example.com",
        status_code=200,
        headers={"content-type": "text/html; charset=utf-8"},
        content=(
            b"<html>"
            b"<head><title>Example Domain</title></head>"
            b"<body>"
            b"<h1>OpenScout Test</h1>"
            b"<p>Web extraction works.</p>"
            b"</body>"
            b"</html>"
        ),
        elapsed_ms=100.0,
    )


def test_web_dns_success(monkeypatch):
    """Test successful DNS lookup."""
    from openscout.cli import web

    result = DNSLookupResult(
        domain="example.com",
        records=[
            DNSRecord(
                record_type="A",
                value="93.184.216.34",
                ttl=300,
            )
        ],
        errors={},
    )

    monkeypatch.setattr(web, "lookup_dns", lambda *args, **kwargs: result)

    response = runner.invoke(app, ["web", "dns", "example.com"])

    assert response.exit_code == 0
    assert "example.com" in response.stdout
    assert "93.184.216.34" in response.stdout


def test_web_domain_success(monkeypatch):
    """Test successful domain registration lookup."""
    from openscout.cli import web

    result = DomainLookupResult(
        domain="example.com",
        registrar="Example Registrar",
        registered="2020-01-01",
        expires="2027-01-01",
        updated="2026-01-01",
        statuses=["active"],
        nameservers=["ns1.example.com"],
        events=[],
        registry="Example Registry",
    )

    monkeypatch.setattr(web, "lookup_domain", lambda *args, **kwargs: result)

    response = runner.invoke(app, ["web", "domain", "example.com"])

    assert response.exit_code == 0
    assert "example.com" in response.stdout
    assert "Example Registrar" in response.stdout


def test_web_fetch_success(monkeypatch):
    """Test successful HTTP fetch."""
    from openscout.cli import web

    result = FetchResult(
        url="https://example.com",
        status_code=200,
        headers={"content-type": "text/html"},
        content=b"<html><body>Hello World</body></html>",
        elapsed_ms=100.0,
    )

    class FakeClient:
        def __init__(self, *args, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def fetch(self, *args, **kwargs):
            return result

    monkeypatch.setattr(web, "WebClient", FakeClient)

    response = runner.invoke(app, ["web", "fetch", "https://example.com"])

    assert response.exit_code == 0
    assert "200" in response.stdout


def test_web_headers_success(monkeypatch):
    """Test successful security-header inspection."""
    from openscout.cli import web

    result = FetchResult(
        url="https://example.com",
        status_code=200,
        headers={
            "content-type": "text/html",
            "strict-transport-security": "max-age=31536000",
            "x-content-type-options": "nosniff",
        },
        content=b"<html><body>Example</body></html>",
        elapsed_ms=100.0,
    )

    class FakeClient:
        def __init__(self, *args, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def fetch(self, *args, **kwargs):
            return result

    monkeypatch.setattr(web, "WebClient", FakeClient)

    response = runner.invoke(app, ["web", "headers", "https://example.com"])

    assert response.exit_code == 0


def test_web_scrape_success(monkeypatch):
    """Test successful page scraping."""
    from openscout.cli import web

    result = FetchResult(
        url="https://example.com",
        status_code=200,
        headers={"content-type": "text/html"},
        content=(
            b"<html><head><title>Example Page</title></head>"
            b"<body><h1>Hello</h1><p>World</p></body></html>"
        ),
        elapsed_ms=100.0,
    )

    class FakeClient:
        def __init__(self, *args, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def fetch(self, *args, **kwargs):
            return result

    monkeypatch.setattr(web, "WebClient", FakeClient)

    response = runner.invoke(app, ["web", "scrape", "https://example.com"])

    assert response.exit_code == 0
    assert "Example Page" in response.stdout
    assert "World" in response.stdout


def _inspection_result():
    """Build a representative successful inspection result."""
    http_result = FetchResult(
        url="https://example.com",
        status_code=200,
        headers={
            "content-type": "text/html",
            "strict-transport-security": "max-age=31536000",
            "x-content-type-options": "nosniff",
        },
        content=b"<html><title>Example</title></html>",
        elapsed_ms=120.0,
    )

    dns_result = DNSLookupResult(
        domain="example.com",
        records=[
            DNSRecord(
                record_type="A",
                value="93.184.216.34",
                ttl=300,
            )
        ],
        errors={},
    )

    registration_result = DomainLookupResult(
        domain="example.com",
        registrar="Example Registrar",
        registered="2020-01-01",
        expires="2027-01-01",
        updated="2026-01-01",
        statuses=["active"],
        nameservers=["ns1.example.com"],
        events=[],
        registry="Example Registry",
    )

    tls_result = TLSInspectionResult(
        domain="example.com",
        port=443,
        subject="CN=example.com",
        issuer="CN=Example CA",
        not_before="2026-01-01T00:00:00",
        not_after="2027-01-01T00:00:00",
        days_remaining=44,
        subject_alt_names=["example.com"],
        tls_version="TLSv1.3",
        cipher="TLS_AES_256_GCM_SHA384",
        verified=True,
    )

    header_result = audit_security_headers(
        http_result.headers,
        http_result.url,
    )

    return InspectionResult(
        domain="example.com",
        dns=InspectionSection(
            status="ok",
            data=dns_result,
        ),
        registration=InspectionSection(
            status="ok",
            data=registration_result,
        ),
        http=InspectionSection(
            status="ok",
            data=http_result,
        ),
        tls=InspectionSection(
            status="ok",
            data=tls_result,
        ),
        security_headers=InspectionSection(
            status="ok",
            data=header_result,
        ),
    )


def test_web_inspect_success(monkeypatch):
    """Test unified inspection with a bare HTTPS URL."""
    from openscout.cli import web

    result = _inspection_result()

    monkeypatch.setattr(
        web,
        "inspect_domain",
        lambda *args, **kwargs: result,
    )

    response = runner.invoke(app, ["web", "inspect", "example.com"])

    assert response.exit_code == 0
    assert "OpenScout Web Inspection" in response.stdout
    assert "example.com" in response.stdout


def test_web_inspect_bare_domain(monkeypatch):
    """Test unified inspection with a bare domain."""
    from openscout.cli import web

    captured = {}

    def fake_inspect_domain(domain, **kwargs):
        captured["domain"] = domain
        captured.update(kwargs)
        return _inspection_result()

    monkeypatch.setattr(web, "inspect_domain", fake_inspect_domain)

    response = runner.invoke(app, ["web", "inspect", "example.com"])

    assert response.exit_code == 0
    assert captured["domain"] == "example.com"
    assert captured["http_url"] is None


def test_web_inspect_http_url(monkeypatch):
    """Test unified inspection preserves an explicitly supplied HTTP URL."""
    from openscout.cli import web

    captured = {}

    def fake_inspect_domain(domain, **kwargs):
        captured["domain"] = domain
        captured.update(kwargs)
        return _inspection_result()

    monkeypatch.setattr(web, "inspect_domain", fake_inspect_domain)

    response = runner.invoke(
        app,
        ["web", "inspect", "http://example.com"],
    )

    assert response.exit_code == 0
    assert captured["domain"] == "example.com"
    assert captured["http_url"] == "http://example.com"


def test_web_inspect_json(monkeypatch):
    """Test JSON output from unified inspection."""
    from openscout.cli import web

    monkeypatch.setattr(
        web,
        "inspect_domain",
        lambda *args, **kwargs: _inspection_result(),
    )

    response = runner.invoke(
        app,
        ["web", "inspect", "example.com", "--json"],
    )

    assert response.exit_code == 0

    payload = json.loads(response.stdout)

    assert payload["domain"] == "example.com"
    assert payload["status"] == "ok"
    assert payload["dns"]["status"] == "ok"
    assert payload["registration"]["status"] == "ok"
    assert payload["http"]["status"] == "ok"
    assert payload["tls"]["status"] == "ok"


def test_web_inspect_writes_json_file(monkeypatch, tmp_path):
    """Test saving unified inspection JSON to a file."""
    from openscout.cli import web

    monkeypatch.setattr(
        web,
        "inspect_domain",
        lambda *args, **kwargs: _inspection_result(),
    )

    output_file = tmp_path / "report.json"

    response = runner.invoke(
        app,
        [
            "web",
            "inspect",
            "example.com",
            "--output",
            str(output_file),
        ],
    )

    assert response.exit_code == 0
    assert output_file.exists()

    payload = json.loads(output_file.read_text(encoding="utf-8"))

    assert payload["domain"] == "example.com"
    assert payload["status"] == "ok"


def test_web_inspect_json_and_output(monkeypatch, tmp_path):
    """Test printing and saving JSON in the same invocation."""
    from openscout.cli import web

    monkeypatch.setattr(
        web,
        "inspect_domain",
        lambda *args, **kwargs: _inspection_result(),
    )

    output_file = tmp_path / "report.json"

    response = runner.invoke(
        app,
        [
            "web",
            "inspect",
            "example.com",
            "--json",
            "--output",
            str(output_file),
        ],
    )

    assert response.exit_code == 0
    assert output_file.exists()

    stdout_payload = json.loads(response.stdout)
    file_payload = json.loads(output_file.read_text(encoding="utf-8"))

    assert stdout_payload["domain"] == "example.com"
    assert file_payload["domain"] == "example.com"


def test_web_inspect_rejects_unsupported_scheme():
    """Test that inspection rejects unsupported URL schemes."""
    response = runner.invoke(
        app,
        ["web", "inspect", "ftp://example.com"],
    )

    assert response.exit_code != 0


def test_web_dns_error(monkeypatch) -> None:
    """Test that DNS lookup errors are displayed."""
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


def test_web_fetch_displays_text_body(monkeypatch) -> None:
    """Test that fetch displays the response body when requested."""
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
    """Test that HTTP fetch errors are displayed."""
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


def test_web_scrape_markdown(monkeypatch) -> None:
    """Test Markdown scraping output."""
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
    assert "Web extraction works." in result.output
    assert "OpenScout Test" not in result.output


def test_web_scrape_rejects_invalid_format(monkeypatch) -> None:
    """Test that unsupported scrape output formats are rejected."""
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
