"""Transport layer: abstract Transport, TCP implementation, command helpers."""
from __future__ import annotations

import abc
import socket
from struct import pack, unpack

from openzk.errors import ZKAuthFailed, ZKProtocolError, ZKUnreachable
from openzk.framing import MAGIC, USHRT_MAX, Frame, build_packet, make_commkey, parse_frame

CMD_CONNECT = 1000
CMD_EXIT = 1001
CMD_AUTH = 1102
CMD_ACK_OK = 2000
CMD_ACK_UNAUTH = 2005
CMD_PREPARE_DATA = 1500
CMD_DATA = 1501
CMD_FREE_DATA = 1502
CMD_PREPARE_BUFFER = 1503
CMD_READ_BUFFER = 1504
CMD_OPTIONS_RRQ = 11
MAX_CHUNK = 0xFFC0


def first_data(frames: list[Frame], want_cmd: int) -> bytes:
    """Concatenate data from all frames whose cmd == want_cmd."""
    return b"".join(f.data for f in frames if f.cmd == want_cmd)


class Transport(abc.ABC):
    @abc.abstractmethod
    def connect(self) -> None: ...
    @abc.abstractmethod
    def disconnect(self) -> None: ...
    @abc.abstractmethod
    def capture(self, command: int, data: bytes = b"") -> list[Frame]:
        """Send a command; return the first response frame plus any follow-on frames."""


class TcpTransport(Transport):
    def __init__(self, host: str, port: int = 4370, timeout: float = 10.0,
                 password: int = 0, idle: float = 1.5) -> None:
        self.host = host
        self.port = port
        self.timeout = timeout
        self.password = password
        self.idle = idle
        self._sock: socket.socket | None = None
        self.session_id = 0
        self.reply_id = USHRT_MAX - 1

    def connect(self) -> None:
        try:
            self._sock = socket.create_connection((self.host, self.port), timeout=self.timeout)
        except OSError as e:
            raise ZKUnreachable(f"cannot reach {self.host}:{self.port}: {e}") from e
        self.session_id = 0
        self.reply_id = USHRT_MAX - 1
        frame = self._exchange(CMD_CONNECT)
        self.session_id = frame.session
        if frame.cmd == CMD_ACK_UNAUTH:
            frame = self._exchange(CMD_AUTH, make_commkey(self.password, self.session_id))
        if frame.cmd != CMD_ACK_OK:
            raise ZKAuthFailed(f"connect rejected: cmd={frame.cmd:#06x}")

    def disconnect(self) -> None:
        if self._sock is not None:
            try:
                self._exchange(CMD_EXIT)
            except (OSError, ZKProtocolError):
                pass
            self._sock.close()
            self._sock = None

    def _recv_exact(self, n: int) -> bytes:
        assert self._sock is not None
        buf = b""
        while len(buf) < n:
            chunk = self._sock.recv(n - len(buf))
            if not chunk:
                raise ZKProtocolError("socket closed mid-read")
            buf += chunk
        return buf

    def _recv_frame(self) -> Frame:
        top = self._recv_exact(8)
        if top[:4] != MAGIC:
            raise ZKProtocolError(f"bad magic: {top[:4].hex()}")
        length = unpack("<I", top[4:8])[0]
        payload = self._recv_exact(length)
        frame, _ = parse_frame(MAGIC + pack("<I", length) + payload)
        return frame

    def _exchange(self, command: int, data: bytes = b"") -> Frame:
        assert self._sock is not None
        pkt = build_packet(command, data, self.session_id, self.reply_id)
        self._sock.send(MAGIC + pack("<I", len(pkt)) + pkt)
        frame = self._recv_frame()
        self.reply_id = frame.reply
        return frame

    def capture(self, command: int, data: bytes = b"") -> list[Frame]:
        assert self._sock is not None
        frames = [self._exchange(command, data)]
        self._sock.settimeout(self.idle)
        try:
            while True:
                try:
                    f = self._recv_frame()
                except (TimeoutError, OSError):
                    break
                self.reply_id = f.reply
                frames.append(f)
        finally:
            self._sock.settimeout(self.timeout)
        return frames


def read_buffer(transport: Transport, command: int, fct: int, ext: int = 0) -> bytes:
    """Buffered table read: PREPARE_BUFFER(command,fct,ext) then chunked READ_BUFFER.
    Mirrors the official SDK / pyzk read_with_buffer flow."""
    cs = pack("<bhii", 1, command, fct, ext)
    frames = transport.capture(CMD_PREPARE_BUFFER, cs)
    if not frames:
        return b""
    head = frames[0]
    if head.cmd == CMD_DATA:
        return first_data(frames, CMD_DATA)
    if head.cmd != CMD_ACK_OK or len(head.data) < 5:
        return b""
    size = unpack("<I", head.data[1:5])[0]
    if size == 0:
        return b""
    out = bytearray()
    start = 0
    while start < size:
        this = min(MAX_CHUNK, size - start)
        chunk_frames = transport.capture(CMD_READ_BUFFER, pack("<ii", start, this))
        out += first_data(chunk_frames, CMD_DATA)
        start += this
    transport.capture(CMD_FREE_DATA)
    return bytes(out)
