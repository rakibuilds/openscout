
"""Tests for RDAP domain registration lookup."""

import httpx
import pytest

from openscout.web.dns import InvalidDomainError
from openscout.web.domain import (
    DomainLookupError,
    DomainNotFoundError,
    _get_rdap_base_url,
    _parse_domain_response,
    lookup_domain,
)

BOOTSTRAP = {
    "services": [
        [
            ["com", "net"],
            ["https://rdap.verisign.com/com/v1/"],
        ],
        [
            ["org"],
            ["https://rdap.publicinterestregistry.org/rdap/"],
        ],
    ]
}

RDAP_DATA = {
    "objectClassName": "domain",
    "ldhName": "example.com",
    "status": ["active"],
    "entities": [
        {
            "handle": "EXAMPLE-REGISTRAR",
            "roles": ["registrar"],
            "vcardArray": [
                "vcard",
                [
                    ["version", {}, "text", "4.0"],
                    ["fn", {}, "text", "Example Registrar"],
                ],
            ],
        }
    ],
    "nameservers": [
        {"ldhName": "NS1.EXAMPLE.COM"},
        {"ldhName": "NS2.EXAMPLE.COM"},
    ],
    "events": [
        {
            "eventAction": "registration",
            "eventDate": "2020-01-01T00:00:00Z",
        },
        {
            "eventAction": "expiration",
            "eventDate": "2027-01-01T00:00:00Z",
        },
        {
            "eventAction": "last changed",
            "eventDate": "2026-01-01T00:00:00Z",
        },
    ],
}


def make_client(domain_status=200):
    """Create a mocked RDAP HTTP client."""

    def handler(request):
        if request.url.host == "data.iana.org":
            return httpx.Response(200, json=BOOTSTRAP)

        if request.url.path == "/com/v1/domain/example.com":
            return httpx.Response(domain_status, json=RDAP_DATA)

        return httpx.Response(404)

    return httpx.Client(
        transport=httpx.MockTransport(handler),
        follow_redirects=True,
    )


def test_lookup_domain_returns_registration_information():
    with make_client() as client:
        result = lookup_domain("EXAMPLE.COM", client=client)

    assert result.domain == "example.com"
    assert result.registrar == "Example Registrar"
    assert result.registered == "2020-01-01T00:00:00Z"
    assert result.expires == "2027-01-01T00:00:00Z"
    assert result.updated == "2026-01-01T00:00:00Z"
    assert result.statuses == ["active"]
    assert result.nameservers == [
        "ns1.example.com",
        "ns2.example.com",
    ]
    assert result.registry == "rdap.verisign.com"


def test_lookup_domain_rejects_invalid_timeout():
    with pytest.raises(ValueError):
        lookup_domain("example.com", timeout=0)


def test_lookup_domain_rejects_invalid_domain():
    with pytest.raises(InvalidDomainError):
        lookup_domain("https://example.com")


def test_lookup_domain_handles_missing_registration():
    with (
        make_client(domain_status=404) as client,
        pytest.raises(DomainNotFoundError),
    ):
        lookup_domain("example.com", client=client)


def test_rdap_bootstrap_selects_correct_tld():
    result = _get_rdap_base_url("example.org", BOOTSTRAP)

    assert result == "https://rdap.publicinterestregistry.org/rdap"


def test_rdap_bootstrap_rejects_unknown_tld():
    with pytest.raises(DomainLookupError):
        _get_rdap_base_url("example.unknown", BOOTSTRAP)


def test_rdap_bootstrap_selects_longest_suffix():
    bootstrap = {
        "services": [
            [["com"], ["https://generic.example/"]],
            [["example.com"], ["https://specific.example/"]],
        ]
    }

    result = _get_rdap_base_url("test.example.com", bootstrap)

    assert result == "https://specific.example"


def test_lookup_domain_handles_missing_registrar():
    data = {
        "objectClassName": "domain",
        "entities": [],
        "status": [],
        "nameservers": [],
        "events": [],
    }

    result = _parse_domain_response(
        domain="example.com",
        data=data,
        registry="rdap.example",
    )

    assert result.registrar is None
    assert result.nameservers == []
    assert result.events == []
