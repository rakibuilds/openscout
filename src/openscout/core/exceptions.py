
"""Shared exceptions used throughout OpenScout."""


class OpenScoutError(Exception):
    """Base exception for expected OpenScout errors."""


class URLValidationError(OpenScoutError):
    """Raised when a URL is invalid or unsupported."""


class FetchError(OpenScoutError):
    """Raised when a web request fails."""


class NetworkAccessError(FetchError):
    """Raised when a network destination is not allowed or cannot be resolved."""


class ResponseTooLargeError(FetchError):
    """Raised when a response exceeds the configured size limit."""

class MediaProcessingError(OpenScoutError):
    """Raised when a media processing operation fails."""