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
    """Concatenate the payloads of all frames matching a command.

    Args:
        frames: The frames to scan.
        want_cmd: The command code to match.

    Returns:
        The concatenated ``data`` of every frame whose ``cmd`` equals
        ``want_cmd`` (empty bytes if none match).
    """
    return b"".join(f.data for f in frames if f.cmd == want_cmd)


class Transport(abc.ABC):
    """Abstract command transport for a ZK device.

    Implementations move :class:`~openzk.framing.Frame` packets to and from a
    device. The library depends only on this interface, which allows real
    sockets and in-memory fakes (for tests) to be used interchangeably.
    """

    @abc.abstractmethod
    def connect(self) -> None:
        """Establish the connection and authenticate."""

    @abc.abstractmethod
    def disconnect(self) -> None:
        """Tear down the connection, releasing any resources."""

    @abc.abstractmethod
    def capture(self, command: int, data: bytes = b"") -> list[Frame]:
        """Send a command and collect the response frames.

        Args:
            command: The ZK command code to send.
            data: Optional command payload.

        Returns:
            The first response frame followed by any subsequent (streamed)
            frames the device sends before going idle.
        """


class TcpTransport(Transport):
    """TCP implementation of :class:`Transport` for ZK devices.

    Speaks the official ZK TCP framing: a connect/auth handshake on
    :meth:`connect`, request/response with a rolling reply id, and idle-based
    detection of the end of a streamed response in :meth:`capture`.
    """

    def __init__(self, host: str, port: int = 4370, timeout: float = 10.0,
                 password: int = 0, idle: float = 1.5) -> None:
        """Initialize the TCP transport.

        Args:
            host: Device IP address or hostname.
            port: Device TCP service port (ZKTeco default ``4370``).
            timeout: Socket connect/read timeout in seconds.
            password: Numeric comm key used for CMD_AUTH; ``0`` when unset.
            idle: Seconds of silence used to detect the end of a streamed
                multi-frame response in :meth:`capture`.
        """
        self.host = host
        self.port = port
        self.timeout = timeout
        self.password = password
        self.idle = idle
        self._sock: socket.socket | None = None
        self.session_id = 0
        self.reply_id = USHRT_MAX - 1

    def connect(self) -> None:
        """Open the socket and perform connect + optional auth.

        Sends CMD_CONNECT; if the device replies CMD_ACK_UNAUTH, follows up with
        CMD_AUTH using the scrambled comm key.

        Raises:
            ZKUnreachable: The socket connection could not be established.
            ZKAuthFailed: The device rejected the connection or comm key.
        """
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
        """Send CMD_EXIT and close the socket.

        Errors during the exit exchange are suppressed; the socket is always
        closed. Safe to call when already disconnected.
        """
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
        """Send a command and read until the device goes idle.

        Sends one request, then keeps reading frames using the ``idle`` timeout
        to detect the end of a streamed response.

        Args:
            command: The ZK command code to send.
            data: Optional command payload.

        Returns:
            The first response frame followed by any streamed follow-on frames.

        Raises:
            ZKProtocolError: A frame had bad magic or the socket closed
                mid-read.
        """
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
    """Read a device table via the buffered SDK flow.

    Issues CMD_PREPARE_BUFFER for ``(command, fct, ext)``, then pulls the result
    in ``MAX_CHUNK``-sized CMD_READ_BUFFER requests and frees the buffer. Mirrors
    the official SDK / pyzk ``read_with_buffer`` flow.

    Args:
        transport: The transport used to exchange frames.
        command: The underlying data command (e.g. CMD_DB_RRQ).
        fct: The table/function selector for the read.
        ext: Optional extension parameter passed to PREPARE_BUFFER.

    Returns:
        The assembled table blob, or empty bytes if the device reports no data.
    """
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
