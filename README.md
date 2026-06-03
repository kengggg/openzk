# openzk

[![CI](https://github.com/kengggg/openzk/actions/workflows/ci.yml/badge.svg)](https://github.com/kengggg/openzk/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg)](pyproject.toml)

A clean, **read-only** Python client for ZKTeco standalone access-control / time-attendance
devices, speaking their proprietary TCP protocol (port 4370).

`openzk` is a modern, dependency-free alternative to older ZK libraries: it implements the
**modern SDK handshake** that legacy clients omit, derives its command set by
**reverse-engineering the official SDK** (rather than guessing), uses **typed models**, and
ships an easy, well-tested high-level API.

> **Read-only by design.** v1 only reads from the device (users, attendance, templates,
> photos, options). It never writes, clears, unlocks, or reboots — safe to point at a
> production access-control terminal.

## Install

No PyPI release yet — install from Git:

```sh
pip install "git+https://github.com/kengggg/openzk"
# or, with uv:
uv add "git+https://github.com/kengggg/openzk"
```

`openzk` has **zero runtime dependencies** (pure Python standard library).

## Quickstart

```python
from openzk import ZKDevice

with ZKDevice("<DEVICE_IP>", port=4370, password=0) as dev:
    print(dev.device_info())                 # serial, firmware, platform, counts, capabilities
    for u in dev.users():                    # list[User]
        print(u.user_id, u.name)
    for att in dev.attendance():             # streamed iterator — won't load 100k rows at once
        print(att.user_id, att.timestamp, att.status)
    for log in dev.op_logs():                # operation log
        ...
    photo = dev.user_photo("8")              # bytes | None (JPEG)
    faces = dev.face_templates()             # list[FaceTemplate]
    fps   = dev.fingerprint_templates()      # list[FingerTemplate]
    val   = dev.option("FaceFunOn")          # raw device option
```

The context manager handles connect → auth → SDK handshake → capability read, and restores
device state + disconnects on exit. Commands the device doesn't support raise
`ZKNotSupported`; unreachable/auth/protocol failures raise typed errors
(`ZKUnreachable`, `ZKAuthFailed`, `ZKProtocolError`).

## Scope (v1)

| Area | Status |
|------|--------|
| Transport | TCP/4370 (USB/COM designed-for via the `Transport` interface, not yet implemented) |
| Read: device info, users (incl. extended format), attendance, op-logs | ✅ |
| Read: fingerprint & face templates, user photos, raw options | ✅ |
| Writes / control (set user, upload photo, unlock, clear, reboot) | ❌ out of scope |

## How the protocol was derived

`openzk` talks the ZKTeco standalone SDK protocol. The wire framing (packet structure,
checksum, auth handshake) and the command **opcodes** were determined by
**reverse-engineering the official ZKTeco SDK for interoperability** — disassembling the
exported functions to read their opcode constants, then validating each parser against a
real device. The opcode table lives in [`src/openzk/opcodes.py`](src/openzk/opcodes.py); it
contains only factual numbers. **No proprietary ZKTeco code or binary is included or
redistributed** in this repository. See [`tools/extract_opcodes.py`](tools/extract_opcodes.py)
to regenerate the table from an SDK binary you supply yourself.

See [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) for the layered design.

## Disclaimer

This project is **not affiliated with, endorsed by, or sponsored by ZKTeco**. "ZKTeco" and
related marks belong to their respective owners. `openzk` exists for **interoperability** with
hardware you own/operate. Use at your own risk. See [`DISCLAIMER.md`](DISCLAIMER.md).

## Contributing

Contributions welcome — see [`CONTRIBUTING.md`](CONTRIBUTING.md). In short:

```sh
uv sync --extra dev
uv run pytest            # unit tests (no device needed)
uv run ruff check .
```

Live device tests are gated and skipped by default:

```sh
OPENZK_LIVE=1 OPENZK_HOST=<your-device-ip> uv run pytest
```

## License

[MIT](LICENSE) © 2026 Keng Susumpow
