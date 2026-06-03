import hashlib
from datetime import datetime

from openzk.models import Attendance, DeviceInfo, FaceTemplate, FingerTemplate, User, UserPhoto


def test_user_frozen_and_fields() -> None:
    u = User(uid=8, user_id="8", name="Alice", privilege=0, password="", group_id="", card=0)
    assert u.uid == 8 and u.name == "Alice"
    import dataclasses

    import pytest
    with pytest.raises(dataclasses.FrozenInstanceError):
        u.name = "X"  # type: ignore[misc]


def test_attendance_fields() -> None:
    a = Attendance(user_id="8", timestamp=datetime(2026, 5, 30, 9, 0, 0), status=1, punch=0)
    assert a.user_id == "8" and a.status == 1


def test_user_photo_sha() -> None:
    p = UserPhoto(user_id="8", data=b"\xff\xd8\xff\xe0x")
    assert p.sha256 == hashlib.sha256(p.data).hexdigest()
    assert p.byte_size == len(p.data)


def test_device_info_and_templates() -> None:
    d = DeviceInfo(ip="1.2.3.4", serial="S", firmware="F", platform="P",
                   users_count=1, attendance_count=2, faces_count=3, fingers_count=4,
                   capabilities={"FaceFunOn": "1"})
    assert d.capabilities["FaceFunOn"] == "1"
    assert FingerTemplate(uid=8, finger_index=0, data=b"x").finger_index == 0
    assert FaceTemplate(uid=8, data=b"y").uid == 8
