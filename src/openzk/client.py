"""High-level read-only ZKDevice client."""
from __future__ import annotations

from collections.abc import Iterator
from struct import unpack

from openzk.codecs import parse_attendance, parse_op_logs, parse_users
from openzk.errors import ZKNotSupported, ZKProtocolError
from openzk.models import (
    Attendance,
    DeviceInfo,
    FaceTemplate,
    FingerTemplate,
    OpLog,
    User,
)
from openzk.opcodes import OPCODES
from openzk.session import Session
from openzk.transport import (
    CMD_ACK_OK,
    TcpTransport,
    Transport,
    first_data,
    read_buffer,
)

CMD_DB_RRQ = 7
CMD_GET_FREE_SIZES = 50
FCT_USER = 5
FCT_ATTLOG = 1
FCT_OPLOG = 4
FCT_FINGERTMP = 2
CMD_RECV_HEADER = 0x05DC
CMD_RECV_CONTENT = 0x05DD
CMD_NO_PIC = 0x1379


class ZKDevice:
    """High-level read-only client for a ZKTeco device.

    ``ZKDevice`` is the primary entry point of the library. It wraps a
    :class:`~openzk.transport.Transport` and a :class:`~openzk.session.Session`
    to expose convenient methods for reading device metadata, users, attendance
    records, operation logs, and biometric templates. All operations are
    read-only; nothing on the device is mutated.

    Use it as a context manager so that the connection, authentication, SDK
    handshake, and capability read happen on entry and are cleanly torn down on
    exit.

    Example:
        >>> with ZKDevice("192.168.1.201") as dev:
        ...     info = dev.device_info()
        ...     users = dev.users()
        ...     for record in dev.attendance():
        ...         print(record)
    """

    def __init__(self, host: str = "", port: int = 4370, password: int = 0,
                 timeout: float = 10.0, transport: Transport | None = None) -> None:
        """Initialize a device client.

        Args:
            host: Device IP address or hostname.
            port: Device TCP service port (ZKTeco default ``4370``).
            password: Numeric comm key used for CMD_AUTH; ``0`` when unset.
            timeout: Socket connect/read timeout in seconds.
            transport: Optional pre-built :class:`~openzk.transport.Transport`.
                Primarily for dependency injection and testing; when provided,
                ``host``/``port``/``password``/``timeout`` are ignored and the
                given transport is used as-is.
        """
        self.transport = transport or TcpTransport(host, port, timeout, password)
        self.session = Session(self.transport)
        self._caps: dict[str, str] = {}

    def __enter__(self) -> ZKDevice:
        """Open the session and read device capabilities.

        Performs connect, authentication, the SDK handshake, and a capability
        read (caching the result for :meth:`device_info`).

        Returns:
            This :class:`ZKDevice` instance, ready for use.
        """
        self.session.open()
        self._caps = self.session.capabilities()
        return self

    def __exit__(self, *exc: object) -> None:
        """Restore the device SDK handshake flag and disconnect.

        Args:
            *exc: Standard exception tuple from the ``with`` block (unused).
        """
        self.session.close()

    def option(self, name: str) -> str | None:
        """Read a raw device option by name.

        Args:
            name: The option key (e.g. ``"FirmVer"`` or ``"~SerialNumber"``).

        Returns:
            The raw option value as a string, or ``None`` if the device did not
            return a value for that option.
        """
        return self.session.read_option(name)

    def _read_sizes(self) -> tuple[int, int, int, int]:
        """Return (users, fingers, records, faces) via CMD_GET_FREE_SIZES."""
        frames = self.transport.capture(CMD_GET_FREE_SIZES, b"")
        data = frames[0].data if frames else b""
        users = fingers = records = faces = 0
        if len(data) >= 80:
            f = unpack("<20i", data[:80])
            users, fingers, records = f[4], f[6], f[8]
        if len(data) >= 92:
            faces = unpack("<3i", data[80:92])[0]
        return users, fingers, records, faces

    def device_info(self) -> DeviceInfo:
        """Read device metadata and record counts.

        Combines cached capabilities (serial, platform, etc.) with a live read
        of the free-size table for user/finger/attendance/face counts.

        Returns:
            A :class:`~openzk.models.DeviceInfo` with serial, firmware,
            platform, the four record counts, and the full capabilities map.
        """
        c = self._caps
        users_count, fingers_count, attendance_count, faces_count = self._read_sizes()
        return DeviceInfo(
            ip=getattr(self.transport, "host", ""),
            serial=c.get("~SerialNumber", self.option("~SerialNumber") or ""),
            firmware=self.option("FirmVer") or "",
            platform=c.get("~Platform", ""),
            users_count=users_count, attendance_count=attendance_count,
            faces_count=faces_count, fingers_count=fingers_count,
            capabilities=dict(c),
        )

    def users(self) -> list[User]:
        """Read all enrolled users from the device.

        Returns:
            A list of :class:`~openzk.models.User` objects (empty if none).
        """
        blob = read_buffer(self.transport, CMD_DB_RRQ, FCT_USER, 0)
        total = unpack("<I", blob[:4])[0] if len(blob) >= 4 else 0
        count = max(1, total // 72) if total else 1
        return parse_users(blob, count=count)

    def attendance(self) -> Iterator[Attendance]:
        """Stream attendance (punch) records from the device.

        Records are yielded lazily as they are parsed rather than materialized
        all at once, which keeps memory bounded on devices with large logs.

        Yields:
            :class:`~openzk.models.Attendance` records in device order.

        Example:
            >>> with ZKDevice(host) as dev:
            ...     for rec in dev.attendance():
            ...         print(rec.user_id, rec.timestamp)
        """
        blob = read_buffer(self.transport, CMD_DB_RRQ, FCT_ATTLOG, 0)
        total = unpack("<I", blob[:4])[0] if len(blob) >= 4 else 0
        count = max(1, total // 40) if total else 1
        yield from parse_attendance(blob, count=count)

    def op_logs(self) -> Iterator[OpLog]:
        """Stream device operation-log entries.

        Yielded lazily as they are parsed, like :meth:`attendance`.

        Yields:
            :class:`~openzk.models.OpLog` records in device order.
        """
        blob = read_buffer(self.transport, CMD_DB_RRQ, FCT_OPLOG, 0)
        yield from parse_op_logs(blob)

    def user_photo(self, user_id: str) -> bytes | None:
        """Fetch a user's enrollment portrait as JPEG bytes.

        Args:
            user_id: The device user ID (e.g. ``"8"``).

        Returns:
            The JPEG bytes, or ``None`` if the device has no photo for this user.

        Raises:
            ZKNotSupported: The device returned an unexpected response code.
            ZKProtocolError: The assembled photo size did not match the header.

        Example:
            >>> with ZKDevice(host) as dev:
            ...     jpeg = dev.user_photo("8")
        """
        op = OPCODES.get("DownloadUserPhoto", 0x271A)
        frames = self.transport.capture(op, f"{user_id}.jpg\x00".encode("latin-1"))
        if not frames:
            return None
        head = frames[0]
        if head.cmd in (CMD_NO_PIC, CMD_ACK_OK):
            return None
        if head.cmd != CMD_RECV_HEADER:
            raise ZKNotSupported("DownloadUserPhoto", head.cmd)
        declared = unpack("<I", head.data[:4])[0] if len(head.data) >= 4 else 0
        content = first_data(frames, CMD_RECV_CONTENT)
        if declared and len(content) != declared:
            raise ZKProtocolError(
                f"photo size mismatch: header={declared} got={len(content)}")
        return content or None

    def face_templates(self) -> list[FaceTemplate]:
        """Read enrolled face templates for every user.

        Returns:
            A list of :class:`~openzk.models.FaceTemplate`; only users with a
            non-empty template are included.

        Raises:
            ZKNotSupported: The device lacks face support (capability
                ``FaceFunOn`` is not ``"1"``).
        """
        if self._caps.get("FaceFunOn") != "1":
            raise ZKNotSupported("GetUserFace", 0x1375)
        import struct
        op = OPCODES.get("GetUserFace", 0x0096)
        out: list[FaceTemplate] = []
        for u in self.users():
            pid = str(u.user_id).encode()
            payload = pid + struct.pack(f"<{24 - len(pid)}xxB2x", 50)
            frames = self.transport.capture(op, payload)
            data = first_data(frames, CMD_RECV_CONTENT)
            if data:
                out.append(FaceTemplate(uid=u.uid, data=data))
        return out

    def fingerprint_templates(self) -> list[FingerTemplate]:
        """Read all enrolled fingerprint templates.

        Returns:
            A list of :class:`~openzk.models.FingerTemplate` (empty if none).
        """
        blob = read_buffer(self.transport, CMD_DB_RRQ, FCT_FINGERTMP, 0)
        if len(blob) <= 4:
            return []
        body = blob[4:]
        out: list[FingerTemplate] = []
        while len(body) >= 6:
            size = unpack("<H", body[:2])[0]
            if size < 6 or size > len(body):
                break
            uid, fid, _valid = unpack("<HHb", body[2:7])
            out.append(FingerTemplate(uid=uid, finger_index=fid, data=body[6:size]))
            body = body[size:]
        return out
