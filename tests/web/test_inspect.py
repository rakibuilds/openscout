
"""Tests for unified domain inspection."""

from openscout.core.exceptions import OpenScoutError
from openscout.core.results import FetchResult
from openscout.web.dns import DNSLookupResult, DNSRecord
from openscout.web.domain import DomainLookupResult
from openscout.web.inspect import inspect_domain
from openscout.web.tls import TLSInspectionResult


def test_inspect_domain_collects_all_sections(monkeypatch):
    dns_result = DNSLookupResult(
        domain="example.com",
        records=[DNSRecord("A", "93.184.216.34", 300)],
        errors={},
    )

    registration_result = DomainLookupResult(
        domain="example.com",
        registrar="Example Registrar",
        registered="2020-01-01T00:00:00Z",
    )

    http_result = FetchResult(
        url="https://example.com/",
        status_code=200,
        headers={
            "content-type": "text/html",
            "strict-transport-security": "max-age=31536000",
        },
        content=b"<html></html>",
        elapsed_ms=100,
    )

    tls_result = TLSInspectionResult(
        domain="example.com",
        port=443,
        subject="commonName=example.com",
        issuer="commonName=Example CA",
        not_before="2026-11-18T00:00:00+00:00",
        not_after="2027-11-18T00:00:00+00:00",
        days_remaining=365,
        subject_alt_names=["example.com"],
        tls_version="TLSv1.3",
        cipher="TLS_AES_128_GCM_SHA256",
        verified=True,
    )

    monkeypatch.setattr(
        "openscout.web.inspect.lookup_dns",
        lambda *args, **kwargs: dns_result,
    )
    monkeypatch.setattr(
        "openscout.web.inspect.lookup_domain",
        lambda *args, **kwargs: registration_result,
    )
    monkeypatch.setattr(
        "openscout.web.inspect.inspect_tls",
        lambda *args, **kwargs: tls_result,
    )

    class FakeWebClient:
        def __init__(self, config):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return None

        def fetch(self, url, *, raise_for_status=True):
            assert url == "https://example.com"
            assert raise_for_status is False
            return http_result

    monkeypatch.setattr(
        "openscout.web.inspect.WebClient",
        FakeWebClient,
    )

    result = inspect_domain("EXAMPLE.COM")

    assert result.domain == "example.com"
    assert result.status == "ok"
    assert result.dns.status == "ok"
    assert result.registration.status == "ok"
    assert result.http.status == "ok"
    assert result.tls.status == "ok"
    assert result.security_headers.status == "ok"
    assert result.dns.data.records[0].value == "93.184.216.34"
    assert result.registration.data.registrar == "Example Registrar"
    assert result.http.data.status_code == 200
    assert result.tls.data.verified is True


def test_inspect_domain_preserves_partial_results(monkeypatch):
    dns_result = DNSLookupResult(
        domain="example.com",
        records=[DNSRecord("A", "93.184.216.34", 300)],
        errors={},
    )

    monkeypatch.setattr(
        "openscout.web.inspect.lookup_dns",
        lambda *args, **kwargs: dns_result,
    )

    def fail_registration(*args, **kwargs):
        raise OpenScoutError("RDAP unavailable")

    monkeypatch.setattr(
        "openscout.web.inspect.lookup_domain",
        fail_registration,
    )

    def fail_tls(*args, **kwargs):
        raise OpenScoutError("TLS unavailable")

    monkeypatch.setattr(
        "openscout.web.inspect.inspect_tls",
        fail_tls,
    )

    class FakeWebClient:
        def __init__(self, config):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return None

        def fetch(self, *args, **kwargs):
            raise OpenScoutError("HTTP unavailable")

    monkeypatch.setattr(
        "openscout.web.inspect.WebClient",
        FakeWebClient,
    )

    result = inspect_domain("example.com")

    assert result.status == "partial"
    assert result.dns.status == "ok"
    assert result.registration.status == "error"
    assert result.http.status == "error"
    assert result.tls.status == "error"
    assert result.security_headers.status == "skipped"
    assert result.dns.data.records[0].value == "93.184.216.34"


def test_inspection_result_is_json_compatible(monkeypatch):
    dns_result = DNSLookupResult(
        domain="example.com",
        records=[],
        errors={},
    )

    monkeypatch.setattr(
        "openscout.web.inspect.lookup_dns",
        lambda *args, **kwargs: dns_result,
    )
    monkeypatch.setattr(
        "openscout.web.inspect.lookup_domain",
        lambda *args, **kwargs: DomainLookupResult(
            domain="example.com"
        ),
    )
    monkeypatch.setattr(
        "openscout.web.inspect.inspect_tls",
        lambda *args, **kwargs: TLSInspectionResult(
            domain="example.com",
            port=443,
            subject=None,
            issuer=None,
            not_before=None,
            not_after=None,
            days_remaining=None,
            subject_alt_names=[],
            tls_version="TLSv1.3",
            cipher="TLS_AES_128_GCM_SHA256",
            verified=True,
        ),
    )

    class FakeWebClient:
        def __init__(self, config):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return None

        def fetch(self, *args, **kwargs):
            return FetchResult(
                url="https://example.com/",
                status_code=200,
                headers={},
                content=b"",
                elapsed_ms=10,
            )

    monkeypatch.setattr(
        "openscout.web.inspect.WebClient",
        FakeWebClient,
    )

    result = inspect_domain("example.com")
    payload = result.to_dict()

    assert payload["domain"] == "example.com"
    assert payload["status"] == "ok"
    assert payload["dns"]["status"] == "ok"
    assert payload["http"]["data"]["status_code"] == 200
    assert payload["http"]["data"]["content_size"] == 0
    assert "content" not in payload["http"]["data"]
    assert payload["tls"]["data"]["verified"] is True
