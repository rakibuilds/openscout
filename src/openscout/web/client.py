
"""HTTP client for fetching public web pages."""

import ipaddress
import socket
from time import perf_counter
from typing import Self
from urllib.parse import urljoin, urlsplit

import httpx

from openscout.core.config import OpenScoutConfig
from openscout.core.exceptions import (
    FetchError,
    NetworkAccessError,
    ResponseTooLargeError,
)
from openscout.core.results import FetchResult, RedirectHop
from openscout.core.validation import validate_url

_REDIRECT_STATUSES = {301, 302, 303, 307, 308}


class WebClient:
    """HTTP client with destination checks and response-size limits."""

    def __init__(self, config: OpenScoutConfig | None = None) -> None:
        self.config = config or OpenScoutConfig()

        self._client = httpx.Client(
            timeout=self.config.request_timeout,
            follow_redirects=False,
            trust_env=False,
            headers={"User-Agent": self.config.user_agent},
        )

    def fetch(
        self,
        url: str,
        *,
        raise_for_status: bool = True,
    ) -> FetchResult:
        """Fetch a URL while enforcing configured network restrictions.

        Set raise_for_status=False to inspect HTTP error responses such as
        404 and 500 without treating them as connection failures.
        """

        current_url = validate_url(url)
        started_at = perf_counter()
        redirects_followed = 0
        redirects: list[RedirectHop] = []

        while True:
            self._check_destination(current_url)

            try:
                with self._client.stream("GET", current_url) as response:
                    if response.status_code in _REDIRECT_STATUSES:
                        location = response.headers.get("location")

                        if not location:
                            if raise_for_status:
                                response.raise_for_status()

                            raise FetchError(
                                "Redirect response did not include "
                                "a Location header."
                            )

                        if redirects_followed >= self.config.max_redirects:
                            raise FetchError(
                                "The maximum number of redirects "
                                "was exceeded."
                            )

                        redirects.append(
                            RedirectHop(
                                url=str(response.url),
                                status_code=response.status_code,
                                location=urljoin(
                                    str(response.url),
                                    location,
                                ),
                            )
                        )

                        current_url = validate_url(
                            urljoin(str(response.url), location)
                        )
                        redirects_followed += 1
                        continue

                    if raise_for_status:
                        response.raise_for_status()

                    content_length = response.headers.get("content-length")

                    if content_length is not None:
                        try:
                            declared_size = int(content_length)
                        except ValueError:
                            declared_size = None

                        if (
                            declared_size is not None
                            and declared_size
                            > self.config.max_response_bytes
                        ):
                            raise ResponseTooLargeError(
                                "Response exceeds the configured size limit."
                            )

                    chunks: list[bytes] = []
                    total_bytes = 0

                    for chunk in response.iter_bytes():
                        total_bytes += len(chunk)

                        if total_bytes > self.config.max_response_bytes:
                            raise ResponseTooLargeError(
                                "Response exceeds the configured size limit."
                            )

                        chunks.append(chunk)

                    elapsed_ms = (
                        perf_counter() - started_at
                    ) * 1000

                    return FetchResult(
                        url=str(response.url),
                        status_code=response.status_code,
                        headers=dict(response.headers),
                        content=b"".join(chunks),
                        elapsed_ms=elapsed_ms,
                        redirects=redirects,
                    )

            except (FetchError, NetworkAccessError):
                raise
            except httpx.HTTPError as exc:
                raise FetchError(
                    f"Could not fetch {current_url}: {exc}"
                ) from exc

    def _check_destination(self, url: str) -> None:
        """Reject non-public destinations unless explicitly allowed."""

        if self.config.allow_private_network:
            return

        parsed = urlsplit(url)
        hostname = parsed.hostname

        if not hostname:
            raise NetworkAccessError(
                "The URL does not contain a hostname."
            )

        try:
            literal_address = ipaddress.ip_address(hostname)
        except ValueError:
            literal_address = None

        if literal_address is not None:
            self._reject_non_public_address(literal_address)
            return

        port = parsed.port or (
            443 if parsed.scheme == "https" else 80
        )

        try:
            resolved = socket.getaddrinfo(
                hostname,
                port,
                type=socket.SOCK_STREAM,
            )
        except socket.gaierror as exc:
            raise NetworkAccessError(
                f"Could not resolve hostname {hostname}: {exc}"
            ) from exc

        if not resolved:
            raise NetworkAccessError(
                f"Hostname {hostname} did not resolve to an address."
            )

        addresses = {
            ipaddress.ip_address(result[4][0])
            for result in resolved
        }

        for address in addresses:
            self._reject_non_public_address(address)

    @staticmethod
    def _reject_non_public_address(
        address: ipaddress.IPv4Address | ipaddress.IPv6Address,
    ) -> None:
        """Reject addresses that are not globally routable."""

        if not address.is_global:
            raise NetworkAccessError(
                f"Access to non-public IP address {address} is blocked."
            )

    def close(self) -> None:
        """Close the underlying HTTP client."""

        self._client.close()

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *_: object) -> None:
        self.close()
