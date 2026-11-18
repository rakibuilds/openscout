
"""Application configuration."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class OpenScoutConfig:
    """Default settings for OpenScout operations."""

    request_timeout: float = 20.0
    max_response_bytes: int = 5 * 1024 * 1024
    max_redirects: int = 5
    allow_private_network: bool = False
    user_agent: str = (
        "OpenScout/0.1.0 (+https://github.com/rakibuilds/openscout)"
    )

    def __post_init__(self) -> None:
        """Validate configuration values."""

        if self.request_timeout <= 0:
            raise ValueError("request_timeout must be greater than zero.")

        if self.max_response_bytes <= 0:
            raise ValueError("max_response_bytes must be greater than zero.")

        if self.max_redirects < 0:
            raise ValueError("max_redirects cannot be negative.")

        if not self.user_agent.strip():
            raise ValueError("user_agent cannot be empty.")
