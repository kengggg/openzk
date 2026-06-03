
from openzk.errors import (
    ZKAuthFailed,
    ZKError,
    ZKNotSupported,
    ZKProtocolError,
    ZKUnreachable,
)


def test_hierarchy() -> None:
    for exc in (ZKUnreachable, ZKAuthFailed, ZKNotSupported, ZKProtocolError):
        assert issubclass(exc, ZKError)


def test_not_supported_carries_opcode() -> None:
    e = ZKNotSupported("get_face", 0x1375)
    assert e.function == "get_face"
    assert e.response_code == 0x1375
    assert "0x1375" in str(e)
