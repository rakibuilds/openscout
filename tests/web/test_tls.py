
"""Tests for TLS certificate inspection."""

import socket
import ssl

import pytest

from openscout.web.tls import (
    TLSInspectionError,
    inspect_tls,
)

PUBLIC_ADDRESS = (
    socket.AF_INET,
    socket.SOCK_STREAM,
    socket.IPPROTO_TCP,
    "",
    ("93.184.216.34", 443),
)

CERTIFICATE = {
    "subject": ((("commonName", "example.com"),),),
    "issuer": ((("commonName", "Example CA"),),),
    "notBefore": "Nov 18 00:00:00 2026 GMT",
    "notAfter": "Nov 18 00:00:00 2027 GMT",
    "subjectAltName": (
        ("DNS", "example.com"),
        ("DNS", "www.example.com"),
    ),
}


def test_inspect_tls_returns_verified_certificate(monkeypatch):
    monkeypatch.setattr(
        "openscout.web.tls.socket.getaddrinfo",
        lambda *args, **kwargs: [PUBLIC_ADDRESS],
    )

    def fake_connection(*args, **kwargs):
        assert kwargs["verify"] is True
        return CERTIFICATE, "TLSv1.3", "TLS_AES_128_GCM_SHA256"

    monkeypatch.setattr(
        "openscout.web.tls._open_tls_connection",
        fake_connection,
    )

    result = inspect_tls("EXAMPLE.COM")

    assert result.domain == "example.com"
    assert result.port == 443
    assert result.subject == "commonName=example.com"
    assert result.issuer == "commonName=Example CA"
    assert result.not_before is not None
    assert result.not_after is not None
    assert result.days_remaining is not None
    assert result.subject_alt_names == [
        "example.com",
        "www.example.com",
    ]
    assert result.tls_version == "TLSv1.3"
    assert result.cipher == "TLS_AES_128_GCM_SHA256"
    assert result.verified is True
    assert result.verification_error is None


def test_inspect_tls_reports_unverified_certificate(monkeypatch):
    monkeypatch.setattr(
        "openscout.web.tls.socket.getaddrinfo",
        lambda *args, **kwargs: [PUBLIC_ADDRESS],
    )

    calls = []

    def fake_connection(*args, **kwargs):
        calls.append(kwargs["verify"])

        if kwargs["verify"]:
            raise ssl.SSLCertVerificationError(
                "certificate has expired"
            )

        return CERTIFICATE, "TLSv1.2", "ECDHE-RSA-AES128-GCM-SHA256"

    monkeypatch.setattr(
        "openscout.web.tls._open_tls_connection",
        fake_connection,
    )

    result = inspect_tls("example.com")

    assert calls == [True, False]
    assert result.verified is False
    assert "expired" in result.verification_error


def test_inspect_tls_blocks_private_addresses(monkeypatch):
    private_address = (
        socket.AF_INET,
        socket.SOCK_STREAM,
        socket.IPPROTO_TCP,
        "",
        ("127.0.0.1", 443),
    )

    monkeypatch.setattr(
        "openscout.web.tls.socket.getaddrinfo",
        lambda *args, **kwargs: [private_address],
    )

    with pytest.raises(
        TLSInspectionError,
        match="non-public IP address",
    ):
        inspect_tls("example.com")


def test_inspect_tls_rejects_invalid_port():
    with pytest.raises(ValueError, match="port"):
        inspect_tls("example.com", port=70000)


def test_inspect_tls_rejects_non_positive_timeout():
    with pytest.raises(ValueError, match="timeout"):
        inspect_tls("example.com", timeout=0)


def test_inspect_tls_handles_dns_failure(monkeypatch):
    def fail_resolution(*args, **kwargs):
        raise socket.gaierror("name resolution failed")

    monkeypatch.setattr(
        "openscout.web.tls.socket.getaddrinfo",
        fail_resolution,
    )

    with pytest.raises(
        TLSInspectionError,
        match="Could not resolve hostname",
    ):
        inspect_tls("example.com")

def test_inspect_tls_clears_verification_error_after_later_verified_address(
    monkeypatch,
):
    second_address = (
        socket.AF_INET,
        socket.SOCK_STREAM,
        socket.IPPROTO_TCP,
        "",
        ("1.1.1.1", 443),
    )

    monkeypatch.setattr(
        "openscout.web.tls.socket.getaddrinfo",
        lambda *args, **kwargs: [PUBLIC_ADDRESS, second_address],
    )

    calls = []

    def fake_connection(address_info, *args, **kwargs):
        address = address_info[4][0]
        verify = kwargs["verify"]
        calls.append((address, verify))

        if address == "93.184.216.34" and verify:
            raise ssl.SSLCertVerificationError(
                "certificate verification failed"
            )

        if address == "93.184.216.34":
            raise OSError("unverified fallback connection failed")

        return CERTIFICATE, "TLSv1.3", "TLS_AES_128_GCM_SHA256"

    monkeypatch.setattr(
        "openscout.web.tls._open_tls_connection",
        fake_connection,
    )

    result = inspect_tls("example.com")

    assert calls == [
        ("93.184.216.34", True),
        ("93.184.216.34", False),
        ("1.1.1.1", True),
    ]
    assert result.verified is True
    assert result.verification_error is None