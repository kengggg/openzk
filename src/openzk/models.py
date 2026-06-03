"""Frozen dataclass models. No I/O."""
from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import datetime


@dataclass(frozen=True)
class DeviceInfo:
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
    uid: int
    user_id: str
    name: str
    privilege: int
    password: str
    group_id: str
    card: int


@dataclass(frozen=True)
class Attendance:
    user_id: str
    timestamp: datetime
    status: int
    punch: int


@dataclass(frozen=True)
class OpLog:
    op: int
    timestamp: datetime
    target_uid: int
    raw: bytes


@dataclass(frozen=True)
class FingerTemplate:
    uid: int
    finger_index: int
    data: bytes


@dataclass(frozen=True)
class FaceTemplate:
    uid: int
    data: bytes


@dataclass(frozen=True)
class UserPhoto:
    user_id: str
    data: bytes

    @property
    def byte_size(self) -> int:
        return len(self.data)

    @property
    def sha256(self) -> str:
        return hashlib.sha256(self.data).hexdigest()
