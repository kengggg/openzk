"""Fake transport for tests: replays scripted responses, records sent commands."""
from __future__ import annotations

from collections.abc import Callable

from openzk.framing import Frame
from openzk.transport import Transport


class FakeTransport(Transport):
    def __init__(self, responder: Callable[[int, bytes], list[Frame]]) -> None:
        self._responder = responder
        self.sent: list[tuple[int, bytes]] = []
        self.connected = False

    def connect(self) -> None:
        self.connected = True

    def disconnect(self) -> None:
        self.connected = False

    def capture(self, command: int, data: bytes = b"") -> list[Frame]:
        self.sent.append((command, data))
        return self._responder(command, data)
