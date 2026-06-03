import struct

from openzk.framing import MAGIC, Frame, build_packet, checksum, make_commkey, parse_frame


def test_checksum_connect_known_vector() -> None:
    # CMD_CONNECT(1000) header with session=0, reply=65534 -> checksum 0xfc17 (validated vs pyzk)
    hdr = struct.pack("<4H", 1000, 0, 0, 65534)
    assert checksum(hdr) == 0xfc17


def test_build_connect_packet_matches_official() -> None:
    # session=0, reply=65534 -> packet carries reply+1 wrapped to 0, checksum over original
    pkt = build_packet(1000, b"", session_id=0, reply_id=65534)
    assert pkt == bytes.fromhex("e80317fc00000000")


def test_make_commkey_zero_key() -> None:
    k = make_commkey(0, 1234)
    assert isinstance(k, bytes) and len(k) == 4


def test_parse_frame_roundtrip() -> None:
    payload = struct.pack("<4H", 2000, 0, 4660, 7) + b"hello"
    framed = MAGIC + struct.pack("<I", len(payload)) + payload
    frame, rest = parse_frame(framed)
    assert frame == Frame(cmd=2000, session=4660, reply=7, data=b"hello")
    assert rest == b""
