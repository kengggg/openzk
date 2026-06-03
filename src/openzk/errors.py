"""Typed exceptions for openzk."""
from __future__ import annotations


class ZKError(Exception):
    """Base class for all openzk errors."""


class ZKUnreachable(ZKError):
    """Device could not be reached (timeout/refused/reset)."""


class ZKAuthFailed(ZKError):
    """Device rejected the comm key (CMD_ACK_UNAUTH after AUTH)."""


class ZKProtocolError(ZKError):
    """Malformed framing, bad magic, or size mismatch."""


class ZKNotSupported(ZKError):
    """Device returned a not-supported/unsupported code for a command."""

    def __init__(self, function: str, response_code: int) -> None:
        self.function = function
        self.response_code = response_code
        super().__init__(f"{function!r} not supported by device (resp={response_code:#06x})")
