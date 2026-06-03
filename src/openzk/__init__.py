"""openzk — a clean, read-only Python client for ZKTeco standalone devices."""
from openzk.client import ZKDevice
from openzk.errors import (
    ZKAuthFailed,
    ZKError,
    ZKNotSupported,
    ZKProtocolError,
    ZKUnreachable,
)
from openzk.models import (
    Attendance,
    DeviceInfo,
    FaceTemplate,
    FingerTemplate,
    OpLog,
    User,
    UserPhoto,
)

__version__ = "0.1.0"
__all__ = [
    "ZKDevice", "ZKError", "ZKUnreachable", "ZKAuthFailed", "ZKNotSupported",
    "ZKProtocolError", "DeviceInfo", "User", "Attendance", "OpLog",
    "FingerTemplate", "FaceTemplate", "UserPhoto", "__version__",
]
