import os

import pytest

from openzk import ZKDevice

# Live tests run against a real device the operator supplies via env vars.
# Assertions are structural (well-formed data), not tied to any specific
# device's identity or population — no host/serial/headcount is embedded here.
pytestmark = pytest.mark.skipif(
    os.environ.get("OPENZK_LIVE") != "1",
    reason="set OPENZK_LIVE=1 and OPENZK_HOST=... to run live integration",
)


def _dev() -> ZKDevice:
    return ZKDevice(host=os.environ["OPENZK_HOST"], password=0, timeout=10)


def test_device_info_live() -> None:
    with _dev() as d:
        info = d.device_info()
    assert info.serial            # non-empty serial returned
    assert info.platform          # non-empty platform string
    assert info.users_count >= 0
    assert info.attendance_count >= 0


def test_users_live() -> None:
    with _dev() as d:
        users = d.users()
    assert len(users) > 0
    assert all(u.user_id for u in users)   # every user has an id


def test_attendance_live_sample() -> None:
    with _dev() as d:
        first = next(iter(d.attendance()))
    assert first.timestamp.year >= 2000


def test_user_photo_live() -> None:
    # Fetch a photo for the first user that has one; verify it's a valid JPEG.
    with _dev() as d:
        photo = None
        for u in d.users():
            photo = d.user_photo(u.user_id)
            if photo:
                break
    assert photo is None or photo[:3] == b"\xff\xd8\xff"


def test_op_logs_live_sample() -> None:
    with _dev() as d:
        logs = list(d.op_logs())
    assert isinstance(logs, list)


def test_face_templates_live() -> None:
    with _dev() as d:
        faces = d.face_templates()
    assert isinstance(faces, list)
    assert all(len(f.data) > 0 for f in faces)


def test_fingerprint_templates_live() -> None:
    with _dev() as d:
        fps = d.fingerprint_templates()
    assert isinstance(fps, list)
