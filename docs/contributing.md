# Contributing to openzk

Thanks for your interest! `openzk` is a small, focused, read-only client library.

## Development setup

Uses [uv](https://docs.astral.sh/uv/):

```sh
uv sync --extra dev
uv run pytest            # unit tests — no device required
uv run ruff check .
uv run ruff format --check .
```

## Project layout

```
src/openzk/      the library (pure stdlib, zero runtime deps)
  framing.py     wire framing: checksum, packet build/parse  (no I/O)
  transport.py   Transport interface + TcpTransport + buffered read
  session.py     connect/auth + SDK handshake + capability read
  opcodes.py     generated opcode table (factual numbers)
  models.py      frozen dataclasses
  codecs.py      raw-blob -> model parsers
  client.py      high-level read-only ZKDevice
  errors.py      typed exceptions
tools/           extract_opcodes.py (regenerate opcodes.py from an SDK binary)
tests/           unit tests + a gated live-integration test
```

## Testing philosophy

- Unit tests are **mock-free except the socket**: real framing, a `FakeTransport` that
  replays scripted frames, real parsing.
- The wire layer is pinned by **known-answer vectors** (checksum / packet bytes).
- The live test (`tests/test_integration.py`) only runs with `OPENZK_LIVE=1` and
  `OPENZK_HOST=<device-ip>`; it asserts **structure** (well-formed data), never a specific
  device's identity.

```sh
OPENZK_LIVE=1 OPENZK_HOST=192.0.2.10 uv run pytest
```

## Guidelines

- Keep the library **read-only**. Write/control operations are intentionally out of scope.
- Type hints on all public functions; `openzk` ships `py.typed`.
- New device-table parsers must be **validated against a real device** before being relied on
  (see the live test), not just inferred.
- Conventional commit messages (`feat:`, `fix:`, `docs:`, `test:`, `chore:`).
- Do **not** commit any proprietary SDK binary or vendor software. `*.dll` is git-ignored.

## Regenerating the opcode table

`src/openzk/opcodes.py` is generated. To refresh it from an SDK binary you supply:

```sh
uv sync --extra extract
uv run python tools/extract_opcodes.py /path/to/sdk-binary
```
