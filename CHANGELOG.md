# Changelog

All notable changes to this project are documented here. The format is based on
[Keep a Changelog](https://keepachangelog.com/), and this project adheres to
[Semantic Versioning](https://semver.org/).

## [Unreleased]

## [0.1.0] - 2026-06-03

Initial release.

### Added
- Read-only `ZKDevice` client over TCP/4370 (context manager: connect → auth → SDK
  handshake → capability read; restores state on exit).
- `device_info`, `users` (72/28-byte record formats), `attendance` (streamed),
  `op_logs`, `fingerprint_templates`, `face_templates`, `user_photo`, and raw `option`.
- Pure wire layer (`framing`) pinned by known-answer test vectors; `Transport` interface
  with `TcpTransport` and a `FakeTransport` for tests; buffered table reads.
- Typed error hierarchy (`ZKError`, `ZKUnreachable`, `ZKAuthFailed`, `ZKNotSupported`,
  `ZKProtocolError`).
- Generated opcode table reverse-engineered from the official SDK; `tools/extract_opcodes.py`
  to regenerate it from a user-supplied SDK binary.
- Zero runtime dependencies; `py.typed`.

[Unreleased]: https://github.com/kengggg/openzk/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/kengggg/openzk/releases/tag/v0.1.0
