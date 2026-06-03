import struct
from datetime import datetime

from openzk.codecs import decode_time, parse_attendance, parse_op_logs, parse_users


def test_decode_time_known() -> None:
    t = (((((2026 - 2000) * 12 + (5 - 1)) * 31 + (30 - 1)) * 24 + 9) * 60 + 0) * 60 + 0
    assert decode_time(struct.pack("<I", t)) == datetime(2026, 5, 30, 9, 0, 0)


def test_parse_users_72byte() -> None:
    rec = struct.pack("<HB8s24sIx7sx24s", 8, 0, b"", b"Alice", 0, b"", b"8")
    blob = struct.pack("<I", len(rec)) + rec
    users = parse_users(blob, count=1)
    assert len(users) == 1
    assert users[0].uid == 8 and users[0].user_id == "8" and users[0].name == "Alice"


def test_parse_users_blank_name_becomes_nn() -> None:
    rec = struct.pack("<HB8s24sIx7sx24s", 14, 0, b"", b"", 0, b"", b"14")
    blob = struct.pack("<I", len(rec)) + rec
    users = parse_users(blob, count=1)
    assert users[0].name == "NN-14"


def test_parse_attendance_40byte() -> None:
    ts = (((((2026 - 2000) * 12 + 4) * 31 + 29) * 24 + 17) * 60 + 0) * 60 + 0
    rec = struct.pack("<H24sB4sB8s", 8, b"8", 1, struct.pack("<I", ts), 0, b"")
    blob = struct.pack("<I", len(rec)) + rec
    recs = list(parse_attendance(blob, count=1))
    assert recs[0].user_id == "8" and recs[0].status == 1
    assert recs[0].timestamp.year == 2026


def test_parse_op_logs() -> None:
    ts = (((((2021 - 2000) * 12 + 2) * 31 + 15) * 24 + 12) * 60 + 0) * 60 + 0
    rec = struct.pack("<HBBI", 0, 70, 0, ts) + bytes([8]) + b"\x00" * 7
    assert len(rec) == 16
    blob = struct.pack("<I", len(rec)) + rec
    logs = list(parse_op_logs(blob))
    assert logs[0].op == 70 and logs[0].target_uid == 8
    assert logs[0].timestamp.year == 2021
