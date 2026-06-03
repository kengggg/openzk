import struct

from openzk.framing import Frame
from openzk.transport import CMD_ACK_OK, first_data, read_buffer
from tests.fakes import FakeTransport


def test_capture_returns_scripted_frames() -> None:
    def responder(cmd: int, data: bytes) -> list[Frame]:
        return [Frame(cmd=CMD_ACK_OK, session=1, reply=1, data=b"\x01\x02")]
    t = FakeTransport(responder)
    frames = t.capture(11, b"~SerialNumber\x00")
    assert frames[0].data == b"\x01\x02"
    assert t.sent == [(11, b"~SerialNumber\x00")]


def test_first_data_picks_first_nonack() -> None:
    frames = [
        Frame(cmd=0x05dc, session=1, reply=1, data=b"\x08\x00\x00\x00"),
        Frame(cmd=0x05dd, session=1, reply=2, data=b"JPEGBYTES"),
        Frame(cmd=CMD_ACK_OK, session=1, reply=3, data=b""),
    ]
    assert first_data(frames, 0x05dd) == b"JPEGBYTES"


def test_read_buffer_inline_data() -> None:
    # PREPARE_BUFFER returns CMD_DATA inline -> returned as-is
    def responder(cmd: int, data: bytes) -> list[Frame]:
        from openzk.transport import CMD_DATA
        return [Frame(cmd=CMD_DATA, session=1, reply=1, data=b"INLINEROWS")]
    t = FakeTransport(responder)
    assert read_buffer(t, command=7, fct=5, ext=0) == b"INLINEROWS"


def test_read_buffer_chunked() -> None:
    # PREPARE_BUFFER returns ACK_OK with size in data[1:5]; one READ_BUFFER chunk follows
    body = b"A" * 10
    def responder(cmd: int, data: bytes) -> list[Frame]:
        from openzk.transport import (
            CMD_ACK_OK,
            CMD_DATA,
            CMD_PREPARE_BUFFER,
            CMD_PREPARE_DATA,
            CMD_READ_BUFFER,
        )
        if cmd == CMD_PREPARE_BUFFER:
            return [Frame(cmd=CMD_ACK_OK, session=1, reply=1,
                          data=b"\x00" + struct.pack("<I", len(body)))]
        if cmd == CMD_READ_BUFFER:
            return [Frame(cmd=CMD_PREPARE_DATA, session=1, reply=1,
                          data=struct.pack("<I", len(body)) + b"\x00\x00\x00\x00"),
                    Frame(cmd=CMD_DATA, session=1, reply=2, data=body),
                    Frame(cmd=CMD_ACK_OK, session=1, reply=3, data=b"")]
        return []
    t = FakeTransport(responder)
    assert read_buffer(t, command=7, fct=5, ext=0) == body
