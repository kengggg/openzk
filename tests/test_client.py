import struct

from openzk.client import ZKDevice
from openzk.framing import Frame
from openzk.transport import (
    CMD_ACK_OK,
    CMD_DATA,
    CMD_FREE_DATA,
    CMD_OPTIONS_RRQ,
    CMD_PREPARE_BUFFER,
    CMD_PREPARE_DATA,
    CMD_READ_BUFFER,
)
from tests.fakes import FakeTransport


def _user_blob() -> bytes:
    rec = struct.pack("<HB8s24sIx7sx24s", 8, 0, b"", b"Alice", 0, b"", b"8")
    return struct.pack("<I", len(rec)) + rec


def _responder(cmd: int, data: bytes) -> list[Frame]:
    if cmd == CMD_OPTIONS_RRQ:
        name = data.split(b"\x00")[0].decode()
        vals = {"~SerialNumber": "<DEVICE_SERIAL>", "FirmVer": "<DEVICE_FW>",
                "~Platform": "<DEVICE_PLATFORM>"}
        return [Frame(cmd=CMD_ACK_OK, session=1, reply=1,
                      data=f"{name}={vals.get(name,'')}".encode())]
    if cmd == 12 or cmd == 1013:  # option write / refresh
        return [Frame(cmd=CMD_ACK_OK, session=1, reply=1, data=b"")]
    if cmd == CMD_PREPARE_BUFFER:
        blob = _user_blob()
        return [Frame(cmd=CMD_ACK_OK, session=1, reply=1,
                      data=b"\x00" + struct.pack("<I", len(blob)))]
    if cmd == CMD_READ_BUFFER:
        blob = _user_blob()
        return [Frame(cmd=CMD_PREPARE_DATA, session=1, reply=1,
                      data=struct.pack("<I", len(blob)) + b"\x00\x00\x00\x00"),
                Frame(cmd=CMD_DATA, session=1, reply=2, data=blob),
                Frame(cmd=CMD_ACK_OK, session=1, reply=3, data=b"")]
    if cmd == CMD_FREE_DATA:
        return [Frame(cmd=CMD_ACK_OK, session=1, reply=1, data=b"")]
    return [Frame(cmd=CMD_ACK_OK, session=1, reply=1, data=b"")]


def test_users_via_fake_transport() -> None:
    dev = ZKDevice(transport=FakeTransport(_responder))
    with dev:
        users = dev.users()
    assert len(users) == 1
    assert users[0].name == "Alice" and users[0].user_id == "8"


def test_context_manager_connects() -> None:
    t = FakeTransport(_responder)
    with ZKDevice(transport=t):
        assert t.connected
    assert not t.connected
