"""Parse raw device table blobs into models. Layouts validated live (later task)."""
from __future__ import annotations

from collections.abc import Iterator
from datetime import datetime
from struct import unpack

from openzk.models import Attendance, OpLog, User


def decode_time(buf: bytes) -> datetime:
    """Decode a 4-byte ZK packed timestamp (seconds since 2000, packed fields)."""
    t = unpack("<I", buf)[0]
    second = t % 60
    t //= 60
    minute = t % 60
    t //= 60
    hour = t % 24
    t //= 24
    day = t % 31 + 1
    t //= 31
    month = t % 12 + 1
    t //= 12
    year = t + 2000
    return datetime(year, month, day, hour, minute, second)


def _decode_str(raw: bytes, encoding: str = "latin-1") -> str:
    return raw.split(b"\x00")[0].decode(encoding, errors="ignore").strip()


def parse_users(blob: bytes, count: int) -> list[User]:
    """Parse the user table. Supports 72-byte (modern) and 28-byte (legacy) records."""
    if len(blob) <= 4:
        return []
    total = unpack("<I", blob[:4])[0]
    body = blob[4:]
    packet = total // count if count else 72
    users: list[User] = []
    if packet == 28:
        size, fmt = 28, "<HB5s8sIxBhI"
        while len(body) >= size:
            uid, priv, pwd, name, card, group, _tz, user_id = unpack(fmt, body[:size])
            users.append(_mk_user(uid, priv, pwd, name, card, str(group), str(user_id)))
            body = body[size:]
    else:
        size, fmt = 72, "<HB8s24sIx7sx24s"
        while len(body) >= size:
            uid, priv, pwd, name, card, group, user_id = unpack(fmt, body[:size])
            users.append(_mk_user(uid, priv, pwd, name, card,
                                  _decode_str(group), _decode_str(user_id)))
            body = body[size:]
    return users


def _mk_user(uid: int, priv: int, pwd: bytes, name: bytes, card: int,
             group_id: str, user_id: str) -> User:
    nm = _decode_str(name) or f"NN-{user_id}"
    return User(uid=uid, user_id=user_id, name=nm, privilege=priv,
                password=_decode_str(pwd), group_id=group_id, card=card)


def parse_attendance(blob: bytes, count: int) -> Iterator[Attendance]:
    """Parse the attendance buffer (40-byte records on TFT-line devices)."""
    if len(blob) <= 4:
        return
    body = blob[4:]
    size = 40  # TFT-line attendance records are 40 bytes
    while len(body) >= size:
        uid, user_id, status, ts, punch, _space = unpack("<H24sB4sB8s", body[:size])
        yield Attendance(user_id=_decode_str(user_id), timestamp=decode_time(ts),
                         status=status, punch=punch)
        body = body[size:]


def parse_op_logs(blob: bytes) -> Iterator[OpLog]:
    """Parse the operation log (16-byte records). Layout confirmed by prior RE:
    bytes[2]=op, bytes[4:8]=packed timestamp, bytes[8]=target uid."""
    if len(blob) <= 4:
        return
    body = blob[4:]
    while len(body) >= 16:
        rec = body[:16]
        op = rec[2]
        ts = decode_time(rec[4:8])
        target_uid = rec[8]
        yield OpLog(op=op, timestamp=ts, target_uid=target_uid, raw=rec)
        body = body[16:]
