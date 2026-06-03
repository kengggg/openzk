# Architecture

`openzk` is layered so each module has one responsibility and can be understood and tested
on its own.

```
client.py     ZKDevice — high-level, read-only API (context manager)
   │
session.py    connect → AUTH → SDKBuild handshake → capability read (restored on close)
   │
transport.py  Transport interface · TcpTransport · buffered table read · frame capture
   │
framing.py    pure wire: checksum, make_commkey, build_packet, parse_frame   (no I/O)

opcodes.py    generated command-opcode table (factual numbers)
models.py     frozen dataclasses (DeviceInfo, User, Attendance, OpLog, *Template, UserPhoto)
codecs.py     parse raw device-table blobs → models
errors.py     typed exception hierarchy
```

## Wire layer (`framing.py`)

Pure functions, no sockets. Packets are framed as `MAGIC(4) + length(4) + payload`, where the
payload is `cmd(2) + checksum(2) + session_id(2) + reply_id(2) + data`. The checksum and the
`reply_id` increment/wrap behaviour are pinned by **known-answer test vectors** so the bytes
on the wire are provably correct.

## Transport (`transport.py`)

An abstract `Transport` defines `connect`/`disconnect`/`capture`. `TcpTransport` implements it
over a socket, reading **frame-by-frame** (no fixed-size `recv` that could truncate a
multi-packet reply). `capture()` returns the first response frame plus any follow-on frames a
command emits. `read_buffer()` implements the device's buffered table-read flow
(`PREPARE_BUFFER` → chunked `READ_BUFFER`). A `FakeTransport` (in tests) replays scripted
frames so the whole stack is unit-testable without hardware.

## Session (`session.py`)

Performs the connect/auth sequence and then the **modern SDK handshake** (`SDKBuild=1`) that
gates extended commands on newer firmware — a step legacy clients skip. It reads device
capability flags so the client can fail fast (`ZKNotSupported`) instead of issuing a doomed
command, and restores the original handshake state on close.

## Deriving the command set

Opcodes were obtained by **reverse-engineering the official SDK for interoperability**:
disassembling each exported function and reading the opcode constant it sends. Those numbers
are committed in `opcodes.py`. **Payload shapes** were cross-checked against existing open
clients; **response parsers** (`codecs.py`) were validated byte-for-byte against a real device
before being relied on. No proprietary code or binary is included — see
[`../DISCLAIMER.md`](../DISCLAIMER.md).

## Design rules

- **Read-only.** No write/control commands in the public API.
- **No silent guessing.** A parser that hasn't been validated against real hardware is not
  shipped as public API.
- **Typed and dependency-free.** Pure stdlib; frozen dataclasses; `py.typed`.
