
"""TLS certificate inspection for public domains."""

import ipaddress
import socket
import ssl
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import certifi

from openscout.core.exceptions import OpenScoutError
from openscout.web.dns import normalize_domain


class TLSInspectionError(OpenScoutError):
    """Raised when a TLS connection or certificate inspection fails."""


@dataclass(slots=True)
class TLSInspectionResult:
    """Information collected from a TLS server certificate."""

    domain: str
    port: int
    subject: str | None
    issuer: str | None
    not_before: str | None
    not_after: str | None
    days_remaining: int | None
    subject_alt_names: list[str]
    tls_version: str | None
    cipher: str | None
    verified: bool
    verification_error: str | None = None


def _format_distinguished_name(
    name: tuple[tuple[tuple[str, str], ...], ...],
) -> str | None:
    """Format a certificate distinguished name."""

    values = [
        f"{key}={value}"
        for group in name
        for key, value in group
    ]

    return ", ".join(values) or None


def _certificate_datetime(
    certificate: dict[str, object],
    field: str,
) -> datetime | None:
    """Parse a certificate validity timestamp."""

    value = certificate.get(field)

    if not isinstance(value, str):
        return None

    try:
        timestamp = ssl.cert_time_to_seconds(value)
    except (ValueError, TypeError):
        return None

    return datetime(1970, 1, 1, tzinfo=UTC) + timedelta(
        seconds=timestamp
    )


def _open_tls_connection(
    address_info: tuple,
    domain: str,
    port: int,
    timeout: float,
    *,
    verify: bool,
) -> tuple[dict[str, object], str | None, str | None]:
    """Connect to one resolved address and inspect its TLS certificate."""

    family, socktype, protocol, _, sockaddr = address_info

    if verify:
        context = ssl.create_default_context(
            cafile=certifi.where(),
        )
    else:
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE

    raw_socket = socket.socket(family, socktype, protocol)
    raw_socket.settimeout(timeout)

    try:
        raw_socket.connect(sockaddr)

        with context.wrap_socket(
            raw_socket,
            server_hostname=domain,
        ) as tls_socket:
            certificate = tls_socket.getpeercert()

            if verify and not certificate:
                raise TLSInspectionError(
                    "The server did not provide a verifiable certificate."
                )

            cipher_info = tls_socket.cipher()
            cipher = (
                cipher_info[0]
                if cipher_info is not None
                else None
            )

            return (
                certificate,
                tls_socket.version(),
                cipher,
            )

    except Exception:
        raw_socket.close()
        raise



def inspect_tls(
    value: str,
    *,
    port: int = 443,
    timeout: float = 5.0,
) -> TLSInspectionResult:
    """Inspect a public domain's TLS certificate.

    Certificate verification uses the Certifi CA bundle.

    If verification fails, a second connection may collect TLS
    connection details without trusting the certificate. The result
    explicitly reports failed verification.
    """

    domain = normalize_domain(value)

    if not 1 <= port <= 65535:
        raise ValueError("port must be between 1 and 65535.")

    if timeout <= 0:
        raise ValueError("timeout must be greater than zero.")

    try:
        addresses = socket.getaddrinfo(
            domain,
            port,
            type=socket.SOCK_STREAM,
        )
    except socket.gaierror as exc:
        raise TLSInspectionError(
            f"Could not resolve hostname {domain}: {exc}"
        ) from exc

    if not addresses:
        raise TLSInspectionError(
            f"Hostname {domain} did not resolve to an address."
        )

    resolved_addresses = {
        ipaddress.ip_address(address_info[4][0])
        for address_info in addresses
    }

    for address in resolved_addresses:
        if not address.is_global:
            raise TLSInspectionError(
                f"Access to non-public IP address {address} is blocked."
            )

    verification_error: str | None = None
    certificate: dict[str, object] | None = None
    tls_version: str | None = None
    cipher: str | None = None
    last_error: Exception | None = None

    for address_info in addresses:
        try:
            certificate, tls_version, cipher = _open_tls_connection(
                address_info,
                domain,
                port,
                timeout,
                verify=True,
            )
            verification_error = None
            break

        except ssl.SSLCertVerificationError as exc:
            verification_error = str(exc)

            try:
                certificate, tls_version, cipher = _open_tls_connection(
                    address_info,
                    domain,
                    port,
                    timeout,
                    verify=False,
                )
                break
            except (OSError, ssl.SSLError, TLSInspectionError) as fallback_exc:
                last_error = fallback_exc

        except (OSError, ssl.SSLError, TLSInspectionError) as exc:
            last_error = exc

    if certificate is None:
        detail = str(
            last_error or verification_error or "Unknown TLS error"
        )
        raise TLSInspectionError(
            f"Could not inspect TLS certificate for {domain}: {detail}"
        ) from last_error

    not_before = _certificate_datetime(
        certificate,
        "notBefore",
    )
    not_after = _certificate_datetime(
        certificate,
        "notAfter",
    )

    now = datetime.now(UTC)

    days_remaining = (
        (not_after - now).days
        if not_after is not None
        else None
    )

    subject_alt_names = [
        value
        for name_type, value in certificate.get(
            "subjectAltName",
            (),
        )
        if name_type in {"DNS", "IP Address"}
    ]

    subject = _format_distinguished_name(
        certificate.get("subject", ())
    )
    issuer = _format_distinguished_name(
        certificate.get("issuer", ())
    )

    return TLSInspectionResult(
        domain=domain,
        port=port,
        subject=subject,
        issuer=issuer,
        not_before=not_before.isoformat() if not_before else None,
        not_after=not_after.isoformat() if not_after else None,
        days_remaining=days_remaining,
        subject_alt_names=subject_alt_names,
        tls_version=tls_version,
        cipher=cipher,
        verified=verification_error is None,
        verification_error=verification_error,
    )
