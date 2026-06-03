"""Session: connect + AUTH + SDKBuild handshake + capability read, restored on close."""
from __future__ import annotations

from openzk.transport import CMD_ACK_OK, CMD_OPTIONS_RRQ, Transport

CMD_OPTIONS_WRQ = 12
CMD_REFRESHDATA = 1013

OPTION_NAMES = (
    "~SerialNumber", "FirmVer", "~Platform", "~DeviceName",
    "FaceFunOn", "FingerFunOn", "PhotoFunOn", "~ZKFPVersion", "FaceVersion",
    "MultiBioDataSupport", "MultiBioPhotoSupport", "~UserExtFmt", "IsSupportPull",
)


class Session:
    def __init__(self, transport: Transport) -> None:
        self.transport = transport
        self._orig_sdkbuild: str | None = None

    def read_option(self, name: str) -> str | None:
        frames = self.transport.capture(CMD_OPTIONS_RRQ, name.encode() + b"\x00")
        if frames and frames[0].cmd == CMD_ACK_OK:
            return frames[0].data.split(b"=", 1)[-1].split(b"\x00")[0].decode("latin-1", "replace")
        return None

    def write_option(self, name: str, value: str) -> None:
        self.transport.capture(CMD_OPTIONS_WRQ, f"{name}={value}\x00".encode())
        self.transport.capture(CMD_REFRESHDATA)

    def open(self) -> None:
        self.transport.connect()
        self._orig_sdkbuild = self.read_option("SDKBuild") or "0"
        self.write_option("SDKBuild", "1")

    def close(self) -> None:
        if self._orig_sdkbuild is not None:
            try:
                self.write_option("SDKBuild", self._orig_sdkbuild)
            except Exception:
                pass
            self._orig_sdkbuild = None
        self.transport.disconnect()

    def capabilities(self) -> dict[str, str]:
        caps: dict[str, str] = {}
        for name in OPTION_NAMES:
            val = self.read_option(name)
            if val not in (None, ""):
                caps[name] = val  # type: ignore[assignment]
        return caps
