
"""Input validation helpers."""

import ipaddress
import re
from urllib.parse import urlsplit, urlunsplit

from openscout.core.exceptions import URLValidationError

_INVALID_HOST_LABEL = re.compile(r"[^a-z0-9-]")


def validate_url(value: str) -> str:
    """Validate and normalize an HTTP or HTTPS URL."""

    if not isinstance(value, str):
        raise URLValidationError("URL must be a string.")

    candidate = value.strip()

    if not candidate:
        raise URLValidationError("URL cannot be empty.")

    if any(ord(char) < 32 or ord(char) == 127 for char in candidate):
        raise URLValidationError("URL contains invalid control characters.")

    if "\\" in candidate:
        raise URLValidationError(
            "URLs containing backslashes are not supported."
        )

    try:
        parsed = urlsplit(candidate)
        hostname = parsed.hostname
        port = parsed.port
    except ValueError as exc:
        raise URLValidationError(f"Invalid URL: {exc}") from exc

    scheme = parsed.scheme.lower()

    if scheme not in {"http", "https"}:
        raise URLValidationError(
            "Only HTTP and HTTPS URLs are supported."
        )

    if not parsed.netloc or not hostname:
        raise URLValidationError("URL must include a hostname.")

    if parsed.username is not None or parsed.password is not None:
        raise URLValidationError(
            "URLs containing credentials are not supported."
        )

    if "@" in parsed.netloc:
        raise URLValidationError(
            "URLs containing credentials are not supported."
        )

    if port is not None and not 1 <= port <= 65535:
        raise URLValidationError("URL contains an invalid port.")

    if "%" in hostname:
        raise URLValidationError(
            "Scoped IP addresses are not supported."
        )

    try:
        address = ipaddress.ip_address(hostname)
    except ValueError:
        normalized_hostname = _normalize_domain(hostname)
        authority = normalized_hostname
    else:
        if isinstance(address, ipaddress.IPv6Address):
            authority = f"[{address.compressed}]"
        else:
            authority = address.compressed

    if port is not None:
        authority = f"{authority}:{port}"

    return urlunsplit(
        (
            scheme,
            authority,
            parsed.path or "/",
            parsed.query,
            "",
        )
    )


def _normalize_domain(hostname: str) -> str:
    """Normalize and validate an internationalized domain name."""

    hostname = hostname.rstrip(".")

    if not hostname:
        raise URLValidationError(
            "URL must include a valid hostname."
        )

    try:
        normalized = hostname.encode("idna").decode("ascii").lower()
    except UnicodeError as exc:
        raise URLValidationError(
            "URL contains an invalid hostname."
        ) from exc

    if len(normalized) > 253:
        raise URLValidationError("Hostname is too long.")

    labels = normalized.split(".")

    for label in labels:
        if (
            not label
            or len(label) > 63
            or label.startswith("-")
            or label.endswith("-")
            or _INVALID_HOST_LABEL.search(label)
        ):
            raise URLValidationError(
                "URL contains an invalid hostname."
            )

    return normalized
