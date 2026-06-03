# Recipes

Task-oriented snippets. All are read-only.

## Export attendance to CSV

```python
import csv
from openzk import ZKDevice

with ZKDevice("192.0.2.10") as dev, open("attendance.csv", "w", newline="") as fh:
    w = csv.writer(fh)
    w.writerow(["user_id", "timestamp", "status", "punch"])
    for a in dev.attendance():                     # streamed — safe for large buffers
        w.writerow([a.user_id, a.timestamp.isoformat(), a.status, a.punch])
```

## Export the user list

```python
from openzk import ZKDevice

with ZKDevice("192.0.2.10") as dev:
    for u in dev.users():
        print(f"{u.uid}\t{u.user_id}\t{u.name}\tpriv={u.privilege}")
```

## Pull every available user photo

Not all users have a stored portrait; `user_photo` returns `None` when there is
none.

```python
from pathlib import Path
from openzk import ZKDevice

out = Path("photos"); out.mkdir(exist_ok=True)
with ZKDevice("192.0.2.10") as dev:
    for u in dev.users():
        jpeg = dev.user_photo(u.user_id)
        if jpeg:
            (out / f"{u.user_id}.jpg").write_bytes(jpeg)
```

## Back up biometric templates

```python
from openzk import ZKDevice

with ZKDevice("192.0.2.10") as dev:
    faces = dev.face_templates()         # list[FaceTemplate] (proprietary vectors)
    fps   = dev.fingerprint_templates()  # list[FingerTemplate]
for f in faces:
    print(f.uid, len(f.data), "bytes")
```

!!! info
    Templates are proprietary biometric feature vectors, not images. They are
    useful for backup/migration to another ZK device, not for viewing.

## Read a raw device option

```python
with ZKDevice("192.0.2.10") as dev:
    print(dev.option("FaceFunOn"))     # "1" / "0" / None
    print(dev.option("~ZKFPVersion"))
```

## Gracefully handle devices without a feature

```python
from openzk import ZKDevice, ZKNotSupported

with ZKDevice("192.0.2.10") as dev:
    try:
        faces = dev.face_templates()
    except ZKNotSupported:
        faces = []     # device has no face module
```

## Run the live integration test against your device

The live tests are skipped unless you opt in with environment variables:

```sh
OPENZK_LIVE=1 OPENZK_HOST=192.0.2.10 uv run pytest -q
```

They assert only that the device returns well-formed data — they don't embed any
specific device's identity.
