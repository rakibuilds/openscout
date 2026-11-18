import pytest

from openscout.core.exceptions import URLValidationError
from openscout.core.validation import validate_url


def test_valid_https_url() -> None:
    assert validate_url("https://example.com") == "https://example.com/"


def test_valid_url_removes_fragment() -> None:
    assert (
        validate_url("https://example.com/page?source=test#section")
        == "https://example.com/page?source=test"
    )


@pytest.mark.parametrize(
    "url",
    [
        "",
        "example.com",
        "ftp://example.com",
        "javascript:alert(1)",
        "https://user:password@example.com",
    ],
)
def test_invalid_urls_are_rejected(url: str) -> None:
    with pytest.raises(URLValidationError):
        validate_url(url)