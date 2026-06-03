# openzk

A clean, **read-only** Python client for ZKTeco standalone access-control /
time-attendance devices, speaking their proprietary TCP protocol (port 4370).

`openzk` is a modern, dependency-free alternative to older ZK libraries:

- **Modern SDK handshake** that legacy clients omit (gates extended commands).
- **Command set reverse-engineered from the official SDK** — not guessed.
- **Typed models** and a small, well-tested high-level API.
- **Zero runtime dependencies** (pure Python standard library).

!!! note "Read-only by design"
    v1 only *reads* from the device — users, attendance, templates, photos,
    options. It never writes, clears, unlocks, or reboots, so it is safe to point
    at a production access-control terminal.

## Install

No PyPI release yet — install from Git:

```sh
pip install "git+https://github.com/kengggg/openzk"
# or with uv:
uv add "git+https://github.com/kengggg/openzk"
```

## Quickstart

```python
from openzk import ZKDevice

with ZKDevice("192.0.2.10", port=4370, password=0) as dev:
    print(dev.device_info())
    for u in dev.users():
        print(u.user_id, u.name)
    for att in dev.attendance():        # streamed iterator
        print(att.user_id, att.timestamp, att.status)
    photo = dev.user_photo("8")         # bytes | None
```

## Where to go next

- **[Getting started](guide/getting-started.md)** — connecting, the context
  manager, error handling, capabilities.
- **[Recipes](guide/recipes.md)** — export attendance to CSV, pull photos, run
  live tests, handle unsupported devices.
- **[API reference](reference/api.md)** — every public class and method.
- **[Protocol & opcodes](reference/protocol.md)** — the reverse-engineered
  command catalog.
- **[Architecture](ARCHITECTURE.md)** — the layered design.

## License & disclaimer

[MIT](https://github.com/kengggg/openzk/blob/main/LICENSE) © 2026 Keng Susumpow.
`openzk` is **not affiliated with ZKTeco** — see the [Disclaimer](disclaimer.md).
