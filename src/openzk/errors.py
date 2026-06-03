"""Typed exceptions for openzk."""
from __future__ import annotations


class ZKError(Exception):
    """Base class for all openzk errors; catch this to handle any failure."""


class ZKUnreachable(ZKError):
    """Raised when the device socket cannot be reached (timeout/refused/reset)."""


class ZKAuthFailed(ZKError):
    """Raised when the device rejects the connection or comm key during auth."""


class ZKProtocolError(ZKError):
    """Raised on malformed framing, bad magic, truncation, or a size mismatch."""


class ZKNotSupported(ZKError):
    """Raised when the device replies that a requested command is unsupported."""

    def __init__(self, function: str, response_code: int) -> None:
        """Initialize the error.

        Args:
            function: Name of the requested device function/command.
            response_code: The unexpected response code the device returned.
        """
        self.function = function
        self.response_code = response_code
        super().__init__(f"{function!r} not supported by device (resp={response_code:#06x})")
