
import pytest

from openscout.core.exceptions import OpenScoutError
from openscout.web.dns import InvalidDomainError, lookup_dns, normalize_domain


def test_normalizes_domain() -> None:
    assert normalize_domain("Example.COM.") == "example.com"


def test_normalizes_international_domain() -> None:
    assert normalize_domain("münich.de") == "xn--mnich-kva.de"


@pytest.mark.parametrize(
    "value",
    [
        "",
        "https://example.com",
        "example.com/path",
        "127.0.0.1",
        "-invalid.com",
        "example..com",
    ],
)
def test_rejects_invalid_domains(value: str) -> None:
    with pytest.raises(InvalidDomainError):
        normalize_domain(value)


def test_rejects_unsupported_record_type() -> None:
    with pytest.raises(ValueError, match="Unsupported DNS record types"):
        lookup_dns("example.com", record_types=("INVALID",))


def test_rejects_non_positive_timeout() -> None:
    with pytest.raises(ValueError, match="timeout"):
        lookup_dns("example.com", timeout=0)


def test_invalid_domain_uses_openscout_exception_hierarchy() -> None:
    with pytest.raises(OpenScoutError):
        normalize_domain("https://example.com")
