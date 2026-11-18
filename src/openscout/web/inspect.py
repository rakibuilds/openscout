
"""Unified domain inspection across DNS, RDAP, HTTP, TLS, and headers."""

from dataclasses import asdict, dataclass

from openscout.core.config import OpenScoutConfig
from openscout.core.exceptions import OpenScoutError
from openscout.core.results import FetchResult
from openscout.web.client import WebClient
from openscout.web.dns import DNSLookupResult, lookup_dns, normalize_domain
from openscout.web.domain import DomainLookupResult, lookup_domain
from openscout.web.headers import HeaderFinding, audit_security_headers
from openscout.web.tls import TLSInspectionResult, inspect_tls


@dataclass(slots=True)
class InspectionSection[T]:
    """Status and data for one inspection subsystem."""

    status: str
    data: T | None = None
    error: str | None = None


@dataclass(slots=True)
class InspectionResult:
    """Combined result of a domain inspection."""

    domain: str
    dns: InspectionSection[DNSLookupResult]
    registration: InspectionSection[DomainLookupResult]
    http: InspectionSection[FetchResult]
    tls: InspectionSection[TLSInspectionResult]
    security_headers: InspectionSection[list[HeaderFinding]]

    @property
    def status(self) -> str:
        """Return the overall inspection status."""

        sections = (
            self.dns,
            self.registration,
            self.http,
            self.tls,
        )

        if all(section.status == "ok" for section in sections):
            return "ok"

        if any(
            section.status in {"ok", "partial"}
            for section in sections
        ):
            return "partial"

        return "error"

    def to_dict(self) -> dict:
        """Convert the inspection result into JSON-compatible data."""

        payload = asdict(self)
        payload["status"] = self.status

        http_data = payload["http"]["data"]

        if http_data is not None:
            http_data["content_size"] = len(
                http_data.pop("content", b"")
            )

        return payload


def _error_section(error: Exception) -> InspectionSection:
    """Build a failed section from an exception."""

    return InspectionSection(
        status="error",
        error=str(error),
    )


def inspect_domain(
    value: str,
    *,
    http_url: str | None = None,
    config: OpenScoutConfig | None = None,
    dns_timeout: float = 3.0,
    rdap_timeout: float = 5.0,
    tls_timeout: float = 5.0,
) -> InspectionResult:
    """Inspect a domain and preserve successful results when a section fails."""

    domain = normalize_domain(value)
    settings = config or OpenScoutConfig()

    # DNS inspection
    try:
        dns_result = lookup_dns(domain, timeout=dns_timeout)

        if dns_result.errors and dns_result.records:
            dns_section = InspectionSection(
                status="partial",
                data=dns_result,
                error="Some DNS record lookups failed.",
            )
        elif dns_result.errors:
            dns_section = InspectionSection(
                status="error",
                data=dns_result,
                error="; ".join(
                    f"{record_type}: {message}"
                    for record_type, message in dns_result.errors.items()
                ),
            )
        else:
            dns_section = InspectionSection(
                status="ok",
                data=dns_result,
            )

    except (OpenScoutError, ValueError, OSError) as exc:
        dns_section = _error_section(exc)

    # RDAP registration inspection
    try:
        registration_result = lookup_domain(
            domain,
            timeout=rdap_timeout,
        )

        registration_section = InspectionSection(
            status="ok",
            data=registration_result,
        )

    except (OpenScoutError, ValueError, OSError) as exc:
        registration_section = _error_section(exc)

    # HTTP inspection
    http_target = http_url or f"https://{domain}"

    try:
        with WebClient(settings) as client:
            http_result = client.fetch(
                http_target,
                raise_for_status=False,
            )

        http_section = InspectionSection(
            status="ok",
            data=http_result,
        )

    except (OpenScoutError, ValueError, OSError) as exc:
        http_section = _error_section(exc)

    # TLS inspection
    try:
        tls_result = inspect_tls(
            domain,
            timeout=tls_timeout,
        )

        if tls_result.verified:
            tls_section = InspectionSection(
                status="ok",
                data=tls_result,
            )
        else:
            tls_section = InspectionSection(
                status="partial",
                data=tls_result,
                error=(
                    tls_result.verification_error
                    or "TLS certificate verification failed."
                ),
            )

    except (OpenScoutError, ValueError, OSError) as exc:
        tls_section = _error_section(exc)

    # Security headers require an HTTP response.
    if http_section.data is not None:
        header_findings = audit_security_headers(
            http_section.data.headers,
            http_section.data.url,
        )

        headers_section = InspectionSection(
            status="ok",
            data=header_findings,
        )
    else:
        headers_section = InspectionSection(
            status="skipped",
            error="HTTP inspection did not return a response.",
        )

    return InspectionResult(
        domain=domain,
        dns=dns_section,
        registration=registration_section,
        http=http_section,
        tls=tls_section,
        security_headers=headers_section,
    )
