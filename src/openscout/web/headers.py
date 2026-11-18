
"""HTTP response-header inspection."""

from dataclasses import dataclass
from urllib.parse import urlsplit


@dataclass(slots=True)
class HeaderFinding:
    """A single security-header observation."""

    name: str
    status: str
    value: str | None
    recommendation: str


SECURITY_HEADERS = {
    "strict-transport-security": (
        "Use HSTS on HTTPS sites to instruct browsers to use secure connections."
    ),
    "content-security-policy": (
        "Define a Content Security Policy appropriate for the application."
    ),
    "x-content-type-options": (
        "Set this header to nosniff to prevent MIME-type sniffing."
    ),
    "referrer-policy": (
        "Set a Referrer Policy that limits unnecessary referrer information."
    ),
    "permissions-policy": (
        "Explicitly control access to browser features where appropriate."
    ),
}


def audit_security_headers(
    headers: dict[str, str],
    url: str,
) -> list[HeaderFinding]:
    """Inspect common HTTP security headers.

    Missing headers are observations, not proof of a vulnerability.
    """

    normalized = {
        key.lower(): value.strip()
        for key, value in headers.items()
    }

    findings: list[HeaderFinding] = []
    scheme = urlsplit(url).scheme.lower()

    for name, recommendation in SECURITY_HEADERS.items():
        if name == "strict-transport-security" and scheme != "https":
            findings.append(
                HeaderFinding(
                    name=name,
                    status="not_applicable",
                    value=normalized.get(name),
                    recommendation="HSTS is relevant to HTTPS responses.",
                )
            )
            continue

        value = normalized.get(name)

        findings.append(
            HeaderFinding(
                name=name,
                status="present" if value else "missing",
                value=value or None,
                recommendation=recommendation,
            )
        )

    csp = normalized.get("content-security-policy", "").lower()
    frame_header = normalized.get("x-frame-options")

    if frame_header or "frame-ancestors" in csp:
        status = "present"
        value = frame_header or "Covered by CSP frame-ancestors directive."
    else:
        status = "missing"
        value = None

    findings.append(
        HeaderFinding(
            name="frame protection",
            status=status,
            value=value,
            recommendation=(
                "Use X-Frame-Options or CSP frame-ancestors to control framing."
            ),
        )
    )

    return findings
