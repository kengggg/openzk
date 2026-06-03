"""Frozen dataclass models for the openzk client.

These are plain, immutable value objects returned by :class:`openzk.client.ZKDevice`.
They perform no I/O and hold only decoded device data.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import datetime


@dataclass(frozen=True)
class DeviceInfo:
    """Device identity and record counts.

    Attributes:
        ip: The device IP/hostname the client connected to.
        serial: Device serial number (``~SerialNumber``).
        firmware: Firmware version string (``FirmVer``).
        platform: Hardware/firmware platform string (``~Platform``).
        users_count: Number of enrolled users.
        attendance_count: Number of stored attendance records.
        faces_count: Number of enrolled face templates.
        fingers_count: Number of enrolled fingerprint templates.
        capabilities: Raw capability option map read from the device.
    """

    ip: str
    serial: str
    firmware: str
    platform: str
    users_count: int
    attendance_count: int
    faces_count: int
    fingers_count: int
    capabilities: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class User:
    """An enrolled device user.

    Attributes:
        uid: Internal numeric record index used by the device.
        user_id: Human-facing user ID (badge/PIN), as a string.
        name: Display name; falls back to ``NN-<user_id>`` when blank.
        privilege: Privilege level code (e.g. user vs. admin).
        password: User PIN/password, if set.
        group_id: Access group identifier.
        card: RFID card number (``0`` when none).
    """

    uid: int
    user_id: str
    name: str
    privilege: int
    password: str
    group_id: str
    card: int


@dataclass(frozen=True)
class Attendance:
    """A single attendance (punch) record.

    Attributes:
        user_id: The user ID that produced the punch.
        timestamp: When the punch occurred.
        status: Verification status code (e.g. fingerprint, face, password).
        punch: Punch state code (e.g. check-in/check-out).
    """

    user_id: str
    timestamp: datetime
    status: int
    punch: int


@dataclass(frozen=True)
class OpLog:
    """A device operation-log entry.

    Attributes:
        op: Operation code identifying what occurred.
        timestamp: When the operation occurred.
        target_uid: The UID affected by the operation, when applicable.
        raw: The original 16-byte record, preserved for further analysis.
    """

    op: int
    timestamp: datetime
    target_uid: int
    raw: bytes


@dataclass(frozen=True)
class FingerTemplate:
    """An enrolled fingerprint template.

    Attributes:
        uid: The user's internal numeric record index.
        finger_index: Which finger this template represents (0-9).
        data: The raw template bytes.
    """

    uid: int
    finger_index: int
    data: bytes


@dataclass(frozen=True)
class FaceTemplate:
    """An enrolled face template.

    Attributes:
        uid: The user's internal numeric record index.
        data: The raw face-template bytes.
    """

    uid: int
    data: bytes


@dataclass(frozen=True)
class UserPhoto:
    """A user's enrollment portrait.

    Attributes:
        user_id: The user ID the photo belongs to.
        data: The raw JPEG image bytes.
    """

    user_id: str
    data: bytes

    @property
    def byte_size(self) -> int:
        """Size of the photo in bytes.

        Returns:
            The length of :attr:`data`.
        """
        return len(self.data)

    @property
    def sha256(self) -> str:
        """Content hash of the photo.

        Returns:
            The hex-encoded SHA-256 digest of :attr:`data`.
        """
        return hashlib.sha256(self.data).hexdigest()
