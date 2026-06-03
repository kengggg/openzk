# Getting started

## Connecting

`ZKDevice` is the entry point. Use it as a context manager — entering performs
the full connect → authenticate → SDK handshake → capability read sequence, and
exiting restores device state and disconnects:

```python
from openzk import ZKDevice

with ZKDevice("192.0.2.10", port=4370, password=0, timeout=10) as dev:
    info = dev.device_info()
    print(info.serial, info.firmware, info.platform)
```

| Parameter | Default | Meaning |
|-----------|---------|---------|
| `host`     | —      | Device IP address |
| `port`     | `4370` | ZK SDK TCP port |
| `password` | `0`    | Comm key (device "communication password"; `0` if unset) |
| `timeout`  | `10`   | Socket timeout in seconds |

## The SDK handshake

Newer firmware gates several commands (e.g. face templates) behind a session
flag that legacy clients never set. `openzk` sets it on connect and **restores
the original value on disconnect**, leaving the device as it found it. You don't
need to do anything — it happens inside the context manager.

## Reading data

```python
with ZKDevice("192.0.2.10") as dev:
    users   = dev.users()                  # list[User]
    for att in dev.attendance():           # Iterator[Attendance] — streamed
        ...
    for log in dev.op_logs():              # Iterator[OpLog]
        ...
    faces   = dev.face_templates()         # list[FaceTemplate]
    fps     = dev.fingerprint_templates()  # list[FingerTemplate]
    photo   = dev.user_photo("8")          # bytes | None
    raw     = dev.option("FaceFunOn")      # str | None
```

`attendance()` and `op_logs()` are **iterators**: the buffer is pulled once and
records are yielded, so a device holding 100k+ attendance rows won't load them
all into memory at once.

## Capabilities & unsupported commands

The handshake reads device capability flags. If you call a command the device
doesn't support (for example `face_templates()` on a device without a face
module), `openzk` raises `ZKNotSupported` rather than hanging or returning
garbage:

```python
from openzk import ZKDevice, ZKNotSupported

with ZKDevice("192.0.2.10") as dev:
    try:
        faces = dev.face_templates()
    except ZKNotSupported:
        faces = []
```

## Error handling

All errors derive from `ZKError`:

| Exception | Raised when |
|-----------|-------------|
| `ZKUnreachable`   | The socket can't connect (timeout / refused / reset). |
| `ZKAuthFailed`    | The device rejected the comm key. |
| `ZKNotSupported`  | The device returned a not-supported code for a command. |
| `ZKProtocolError` | Malformed framing, bad magic, or a size mismatch. |

```python
from openzk import ZKDevice, ZKUnreachable, ZKAuthFailed

try:
    with ZKDevice("192.0.2.10", password=0) as dev:
        users = dev.users()
except ZKUnreachable:
    ...   # device offline / wrong host
except ZKAuthFailed:
    ...   # wrong comm key
```
