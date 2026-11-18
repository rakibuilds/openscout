
"""Domain registration intelligence using RDAP."""

from dataclasses import dataclass, field
from urllib.parse import quote, urlsplit

import httpx

from openscout.core.exceptions import OpenScoutError
from openscout.web.dns import normalize_domain

RDAP_BOOTSTRAP_URL = "https://data.iana.org/rdap/dns.json"
USER_AGENT = "OpenScout/0.1.0"


class DomainLookupError(OpenScoutError):
    """Raised when domain registration information cannot be retrieved."""


class DomainNotFoundError(DomainLookupError):
    """Raised when a domain has no RDAP registration record."""


@dataclass(slots=True)
class DomainEvent:
    """A domain registration event."""

    action: str
    date: str


@dataclass(slots=True)
class DomainLookupResult:
    """Structured domain registration information."""

    domain: str
    registrar: str | None = None
    registered: str | None = None
    expires: str | None = None
    updated: str | None = None
    statuses: list[str] = field(default_factory=list)
    nameservers: list[str] = field(default_factory=list)
    events: list[DomainEvent] = field(default_factory=list)
    registry: str | None = None


def _get_rdap_base_url(
    domain: str,
    bootstrap: dict,
) -> str:
    """Find the authoritative RDAP service using IANA bootstrap data."""

    labels = domain.lower().split(".")
    services = bootstrap.get("services", [])

    matches: list[tuple[int, str]] = []

    for service in services:
        if not isinstance(service, list) or len(service) != 2:
            continue

        tlds, urls = service

        if not isinstance(tlds, list) or not isinstance(urls, list):
            continue

        for tld in tlds:
            if not isinstance(tld, str):
                continue

            if labels[-len(tld.split(".")):] == tld.lower().split("."):
                for url in urls:
                    if isinstance(url, str):
                        matches.append((len(tld.split(".")), url))

    if not matches:
        raise DomainLookupError(
            f"No RDAP service was found for {domain}."
        )

    matches.sort(key=lambda item: item[0], reverse=True)
    base_url = matches[0][1].rstrip("/")

    parsed = urlsplit(base_url)

    if (
        parsed.scheme not in {"https", "http"}
        or not parsed.hostname
        or parsed.username is not None
        or parsed.password is not None
    ):
        raise DomainLookupError("The RDAP service returned an invalid URL.")

    return base_url


def _extract_registrar(entities: list) -> str | None:
    """Extract the registrar name from RDAP entities."""

    for entity in entities:
        if not isinstance(entity, dict):
            continue

        roles = entity.get("roles", [])

        if "registrar" not in roles:
            continue

        vcard = entity.get("vcardArray")

        if (
            isinstance(vcard, list)
            and len(vcard) > 1
            and isinstance(vcard[1], list)
        ):
            for item in vcard[1]:
                if (
                    isinstance(item, list)
                    and len(item) >= 4
                    and item[0] == "fn"
                ):
                    return str(item[3])

        handle = entity.get("handle")

        if handle:
            return str(handle)

    return None


def _extract_events(data: dict) -> list[DomainEvent]:
    """Extract registration lifecycle events."""

    events: list[DomainEvent] = []

    for item in data.get("events", []):
        if not isinstance(item, dict):
            continue

        action = item.get("eventAction")
        date = item.get("eventDate")

        if action and date:
            events.append(
                DomainEvent(
                    action=str(action),
                    date=str(date),
                )
            )

    return events


def _extract_event_date(
    events: list[DomainEvent],
    action: str,
) -> str | None:
    """Find an event date by its action."""

    for event in events:
        if event.action.lower() == action:
            return event.date

    return None


def _parse_domain_response(
    domain: str,
    data: dict,
    registry: str,
) -> DomainLookupResult:
    """Convert an RDAP response into a structured result."""

    entities = data.get("entities", [])
    if not isinstance(entities, list):
        entities = []

    statuses = data.get("status", [])
    if not isinstance(statuses, list):
        statuses = []

    nameservers = data.get("nameservers", [])
    if not isinstance(nameservers, list):
        nameservers = []

    events = _extract_events(data)

    return DomainLookupResult(
        domain=domain,
        registrar=_extract_registrar(entities),
        registered=_extract_event_date(events, "registration"),
        expires=_extract_event_date(events, "expiration"),
        updated=_extract_event_date(events, "last changed"),
        statuses=[str(item) for item in statuses],
        nameservers=[
            str(item["ldhName"]).lower().rstrip(".")
            for item in nameservers
            if isinstance(item, dict) and item.get("ldhName")
        ],
        events=events,
        registry=registry,
    )


def lookup_domain(
    value: str,
    timeout: float = 5.0,
    client: httpx.Client | None = None,
) -> DomainLookupResult:
    """Retrieve domain registration information through RDAP."""

    domain = normalize_domain(value)

    if timeout <= 0:
        raise ValueError("RDAP timeout must be greater than zero.")

    owns_client = client is None

    if owns_client:
        client = httpx.Client(
            timeout=timeout,
            follow_redirects=True,
            max_redirects=5,
            headers={
                "User-Agent": USER_AGENT,
                "Accept": "application/rdap+json, application/json",
            },
        )

    assert client is not None

    try:
        bootstrap_response = client.get(RDAP_BOOTSTRAP_URL)
        bootstrap_response.raise_for_status()

        try:
            bootstrap = bootstrap_response.json()
        except ValueError as exc:
            raise DomainLookupError(
                "IANA RDAP bootstrap returned invalid JSON."
            ) from exc

        base_url = _get_rdap_base_url(domain, bootstrap)

        rdap_url = f"{base_url}/domain/{quote(domain, safe='.-')}"

        response = client.get(rdap_url)

        if response.status_code == 404:
            raise DomainNotFoundError(
                f"No RDAP registration record was found for {domain}."
            )

        response.raise_for_status()

        try:
            data = response.json()
        except ValueError as exc:
            raise DomainLookupError(
                "RDAP server returned invalid JSON."
            ) from exc

        if not isinstance(data, dict):
            raise DomainLookupError(
                "RDAP server returned an unexpected response."
            )

        if data.get("objectClassName") != "domain":
            raise DomainLookupError(
                "RDAP response does not describe a domain."
            )

        return _parse_domain_response(
            domain=domain,
            data=data,
            registry=urlsplit(base_url).hostname or base_url,
        )

    except DomainLookupError:
        raise
    except httpx.HTTPStatusError as exc:
        raise DomainLookupError(
            f"RDAP server returned HTTP {exc.response.status_code}."
        ) from exc
    except httpx.HTTPError as exc:
        raise DomainLookupError(
            f"RDAP request failed: {exc}"
        ) from exc
    finally:
        if owns_client:
            client.close()
