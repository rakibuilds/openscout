
"""DNS record lookup for web intelligence."""

import ipaddress
import re
from dataclasses import dataclass

import dns.resolver

from openscout.core.exceptions import OpenScoutError

SUPPORTED_RECORD_TYPES = ("A", "AAAA", "MX", "NS", "TXT", "CAA", "CNAME")


class InvalidDomainError(OpenScoutError):
    """Raised when a domain name is invalid."""


@dataclass(slots=True)
class DNSRecord:
    """A single DNS record."""

    record_type: str
    value: str
    ttl: int | None = None


@dataclass(slots=True)
class DNSLookupResult:
    """Results of a DNS lookup."""

    domain: str
    records: list[DNSRecord]
    errors: dict[str, str]


def normalize_domain(value: str) -> str:
    """Validate and normalize a DNS hostname."""

    candidate = value.strip().rstrip(".")

    if not candidate or any(char in candidate for char in "/:@?#"):
        raise InvalidDomainError("Enter a domain name, not a URL or IP address.")

    try:
        ipaddress.ip_address(candidate)
        raise InvalidDomainError("DNS lookup expects a domain name, not an IP address.")
    except ValueError:
        pass

    try:
        domain = candidate.encode("idna").decode("ascii").lower()
    except UnicodeError as exc:
        raise InvalidDomainError("Domain contains invalid international characters.") from exc

    if len(domain) > 253:
        raise InvalidDomainError("Domain name is too long.")

    labels = domain.split(".")
    label_pattern = re.compile(r"^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?$")

    if any(not label_pattern.fullmatch(label) for label in labels):
        raise InvalidDomainError("Domain contains an invalid hostname label.")

    return domain


def lookup_dns(
    value: str,
    timeout: float = 3.0,
    record_types: tuple[str, ...] = SUPPORTED_RECORD_TYPES,
) -> DNSLookupResult:
    """Look up selected DNS record types for a domain."""

    domain = normalize_domain(value)

    if timeout <= 0:
        raise ValueError("DNS timeout must be greater than zero.")

    requested_types = tuple(dict.fromkeys(item.upper() for item in record_types))

    unsupported = set(requested_types) - set(SUPPORTED_RECORD_TYPES)
    if unsupported:
        raise ValueError(
            f"Unsupported DNS record types: {', '.join(sorted(unsupported))}"
        )

    resolver = dns.resolver.Resolver()
    records: list[DNSRecord] = []
    errors: dict[str, str] = {}

    for record_type in requested_types:
        try:
            answer = resolver.resolve(
                domain,
                record_type,
                lifetime=timeout,
                raise_on_no_answer=False,
            )

            if answer.rrset is None:
                continue

            ttl = answer.rrset.ttl

            for item in answer:
                records.append(
                    DNSRecord(
                        record_type=record_type,
                        value=item.to_text(),
                        ttl=ttl,
                    )
                )

        except dns.resolver.NXDOMAIN:
            errors[record_type] = "Domain does not exist."
            break
        except dns.resolver.NoNameservers:
            errors[record_type] = "No usable DNS nameservers responded."
        except dns.resolver.LifetimeTimeout:
            errors[record_type] = "DNS query timed out."

    return DNSLookupResult(
        domain=domain,
        records=records,
        errors=errors,
    )
