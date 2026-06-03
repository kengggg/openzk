from openzk.framing import Frame
from openzk.session import Session
from openzk.transport import CMD_ACK_OK, CMD_OPTIONS_RRQ
from tests.fakes import FakeTransport


def _opt_responder(values: dict[str, str]):
    def responder(cmd: int, data: bytes) -> list[Frame]:
        if cmd == CMD_OPTIONS_RRQ:
            name = data.split(b"\x00")[0].decode()
            val = values.get(name, "")
            return [Frame(cmd=CMD_ACK_OK, session=1, reply=1,
                          data=f"{name}={val}".encode())]
        return [Frame(cmd=CMD_ACK_OK, session=1, reply=1, data=b"")]
    return responder


def test_read_option() -> None:
    t = FakeTransport(_opt_responder({"~SerialNumber": "<DEVICE_SERIAL>"}))
    s = Session(t)
    assert s.read_option("~SerialNumber") == "<DEVICE_SERIAL>"


def test_open_sets_and_restores_sdkbuild() -> None:
    sent_writes: list[bytes] = []
    def responder(cmd: int, data: bytes) -> list[Frame]:
        if cmd == 12:  # OPTIONS_WRQ
            sent_writes.append(data)
        return [Frame(cmd=CMD_ACK_OK, session=1, reply=1, data=b"SDKBuild=")]
    t = FakeTransport(responder)
    s = Session(t)
    s.open()
    s.close()
    assert any(b"SDKBuild=1" in w for w in sent_writes)
    assert any(b"SDKBuild=0" in w for w in sent_writes)  # restored (original empty -> 0)
