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
    """Manage the device session lifecycle and option access.

    Wraps a :class:`~openzk.transport.Transport` to read/write device options
    and to perform the SDK handshake required for many table reads. On
    :meth:`open` the original ``SDKBuild`` value is saved and set to ``"1"``;
    :meth:`close` restores it before disconnecting so the device is left in its
    prior state.
    """

    def __init__(self, transport: Transport) -> None:
        """Initialize the session.

        Args:
            transport: The transport used to exchange command frames.
        """
        self.transport = transport
        self._orig_sdkbuild: str | None = None

    def read_option(self, name: str) -> str | None:
        """Read a single device option via CMD_OPTIONS_RRQ.

        Args:
            name: The option key to query.

        Returns:
            The option value (text after ``=``, up to the NUL terminator), or
            ``None`` if the device did not acknowledge the request.
        """
        frames = self.transport.capture(CMD_OPTIONS_RRQ, name.encode() + b"\x00")
        if frames and frames[0].cmd == CMD_ACK_OK:
            return frames[0].data.split(b"=", 1)[-1].split(b"\x00")[0].decode("latin-1", "replace")
        return None

    def write_option(self, name: str, value: str) -> None:
        """Write a device option and refresh device state.

        Sends CMD_OPTIONS_WRQ with ``name=value`` followed by CMD_REFRESHDATA.

        Args:
            name: The option key to set.
            value: The value to assign.
        """
        self.transport.capture(CMD_OPTIONS_WRQ, f"{name}={value}\x00".encode())
        self.transport.capture(CMD_REFRESHDATA)

    def open(self) -> None:
        """Connect and perform the SDK handshake.

        Connects the transport, saves the current ``SDKBuild`` option (defaulting
        to ``"0"`` if absent), then sets ``SDKBuild`` to ``"1"`` so the device
        serves buffered table reads.
        """
        self.transport.connect()
        self._orig_sdkbuild = self.read_option("SDKBuild") or "0"
        self.write_option("SDKBuild", "1")

    def close(self) -> None:
        """Restore the SDK handshake flag and disconnect.

        If :meth:`open` ran, restores the original ``SDKBuild`` value (ignoring
        write errors) before disconnecting the transport.
        """
        if self._orig_sdkbuild is not None:
            try:
                self.write_option("SDKBuild", self._orig_sdkbuild)
            except Exception:
                pass
            self._orig_sdkbuild = None
        self.transport.disconnect()

    def capabilities(self) -> dict[str, str]:
        """Read the standard set of device capability options.

        Queries each well-known option name and collects the ones the device
        answers with a non-empty value.

        Returns:
            A mapping of option name to value for every present capability.
        """
        caps: dict[str, str] = {}
        for name in OPTION_NAMES:
            val = self.read_option(name)
            if val not in (None, ""):
                caps[name] = val  # type: ignore[assignment]
        return caps
