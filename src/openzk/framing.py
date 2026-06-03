"""Pure ZK protocol framing: checksum, auth key, packet build/parse. No I/O."""
from __future__ import annotations

from dataclasses import dataclass
from struct import pack, unpack

MAGIC = b"\x50\x50\x82\x7d"   # MACHINE_PREPARE_DATA (0x5050, 0x7d82)
USHRT_MAX = 65535


@dataclass(frozen=True)
class Frame:
    cmd: int
    session: int
    reply: int
    data: bytes


def checksum(buf: bytes) -> int:
    """ZK packet checksum (from the official SDK)."""
    s = 0
    i = 0
    while i + 1 < len(buf):
        s += unpack("<H", buf[i:i + 2])[0]
        i += 2
        if s > USHRT_MAX:
            s -= USHRT_MAX
    if i < len(buf):
        s += buf[-1]
    while s > USHRT_MAX:
        s -= USHRT_MAX
    s = ~s
    while s < 0:
        s += USHRT_MAX
    return s & 0xFFFF


def make_commkey(key: int, session_id: int, ticks: int = 50) -> bytes:
    """Scramble comm key + session id for CMD_AUTH (the official SDK MakeKey)."""
    key = int(key)
    session_id = int(session_id)
    k = 0
    for i in range(32):
        k = (k << 1 | 1) if (key & (1 << i)) else (k << 1)
    k += session_id
    k = pack(b"I", k & 0xFFFFFFFF)
    k = unpack(b"BBBB", k)
    k = pack(b"BBBB", k[0] ^ ord("Z"), k[1] ^ ord("K"), k[2] ^ ord("S"), k[3] ^ ord("O"))
    k = unpack(b"HH", k)
    k = pack(b"HH", k[1], k[0])
    b = 0xFF & ticks
    k = unpack(b"BBBB", k)
    return pack(b"BBBB", k[0] ^ b, k[1] ^ b, b, k[3] ^ b)


def build_packet(command: int, data: bytes, session_id: int, reply_id: int) -> bytes:
    """Build the inner ZK packet (no TCP top). Checksum over original reply_id;
    packet carries reply_id+1 wrapped at USHRT_MAX (matches official SDK)."""
    hdr = pack("<4H", command, 0, session_id, reply_id) + data
    c = checksum(hdr)
    reply = reply_id + 1
    if reply >= USHRT_MAX:
        reply -= USHRT_MAX
    return pack("<4H", command, c, session_id, reply) + data


def parse_frame(buf: bytes) -> tuple[Frame, bytes]:
    """Parse one TCP-framed packet from the head of buf. Returns (frame, remaining)."""
    from openzk.errors import ZKProtocolError
    if len(buf) < 8:
        raise ZKProtocolError(f"short header: {len(buf)} bytes")
    if buf[:4] != MAGIC:
        raise ZKProtocolError(f"bad magic: {buf[:4].hex()}")
    length = unpack("<I", buf[4:8])[0]
    total = 8 + length
    if len(buf) < total:
        raise ZKProtocolError(f"truncated packet: need {total}, have {len(buf)}")
    payload = buf[8:total]
    cmd = unpack("<H", payload[0:2])[0]
    session = unpack("<H", payload[4:6])[0]
    reply = unpack("<H", payload[6:8])[0]
    return Frame(cmd=cmd, session=session, reply=reply, data=payload[8:]), buf[total:]
