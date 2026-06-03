# Protocol & opcode catalog

`openzk` speaks the ZKTeco **standalone SDK protocol** over TCP port 4370. This
page documents what was learned by reverse-engineering the official SDK for
interoperability: the wire framing, the connection handshake, the bulk
table-read mechanism, and the per-command opcodes.

!!! warning "Provenance & disclaimer"
    Opcodes below are **factual numeric values** recovered by disassembling the
    official SDK's exported functions and reading the opcode immediate each one
    sends. **No proprietary code or binary is included or redistributed.** This
    project is **not affiliated with ZKTeco** — see the [Disclaimer](../disclaimer.md).
    Behaviour is firmware-dependent; treat "supported?" notes as observations,
    not guarantees.

## Wire framing

Each packet is:

```
MAGIC(4 bytes) | length(4, LE) | payload
payload = command(2, LE) | checksum(2) | session_id(2, LE) | reply_id(2, LE) | data
```

- `MAGIC` is the fixed 4-byte prefix `50 50 82 7d`.
- The checksum and the `reply_id` increment/wrap behaviour are pinned by
  known-answer test vectors in the test suite, so the bytes are provably correct.
- Multi-packet responses are read **frame by frame** (no fixed-size read that
  could truncate a reply).

See [`framing`](api.md#transport) for the pure implementation.

## Connection handshake

| Step | Command | Code | Notes |
|------|---------|------|-------|
| Connect  | `CMD_CONNECT`  | `1000` | Opens a session; device returns the session id. |
| Auth     | `CMD_AUTH`     | `1102` | Sent if the device replies `ACK_UNAUTH` (`2005`); payload is the scrambled comm key. |
| Handshake| option write   | `12`   | Sets the modern SDK session flag (saved & **restored on close**). |
| Exit     | `CMD_EXIT`     | `1001` | Closes the session. |

Options are read with `CMD_OPTIONS_RRQ` (`11`) and written with
`CMD_OPTIONS_WRQ` (`12`). Capability flags read at connect include `FaceFunOn`,
`FingerFunOn`, `PhotoFunOn`, `~ZKFPVersion`, `FaceVersion`, and the user
extended-format flag.

## Bulk table reads (buffered)

Large tables are read via a prepare/read-chunks flow:

| Command | Code | Role |
|---------|------|------|
| `CMD_PREPARE_BUFFER` | `1503` | Announce a buffered read; device replies with the total size. |
| `CMD_READ_BUFFER`    | `1504` | Read a chunk at `(offset, size)`. |
| `CMD_FREE_DATA`      | `1502` | Release the buffer when done. |

The table is selected with `CMD_DB_RRQ` (`7`) and an **FCT** (function/table) id:

| FCT | Table | openzk method |
|-----|-------|---------------|
| `1` | Attendance log | `attendance()` |
| `2` | Fingerprint templates | `fingerprint_templates()` |
| `4` | Operation log | `op_logs()` |
| `5` | Users | `users()` |

## Per-command opcodes

Recovered from the official SDK. "openzk" shows whether the v1 (read-only) client
exposes it.

| Function | Opcode | Category | What it does | openzk |
|----------|--------|----------|--------------|--------|
| `DownloadUserPhoto`  | `0x271A` | user photo | Fetch a user's stored portrait (JPEG). | ✅ `user_photo()` |
| `GetUserFace`        | `0x0096` | biometric  | Fetch a user's face template (feature vector). | ✅ `face_templates()` |
| `GetUserTmpEx`       | `0x0058` | biometric  | Fetch a user's (extended) fingerprint template. | ◐ via table read |
| `GetUserInfoEx`      | `0x0050` | user       | Extended user info record. | ◐ (table read used) |
| `GetUserGroup`       | `0x0015` | user       | User's access group. | ✗ |
| `GetUserTZs`         | `0x0017` | user       | User's time zones. | ✗ |
| `GetUserIDCard`      | `0x2744` | user       | User's RFID card data. | ✗ |
| `GetUserVD` / `GetUserVerifyStyle` | `0x2724` / `0x0050` | user | Per-user verify settings. | ✗ |
| `GetDeviceInfo`      | `0x000B` | device     | Device info / parameters. | ◐ (options + sizes) |
| `GetPhotoCount`      | `0x07DD` | capture photo | Count of attendance-capture photos. | ✗ |
| `GetPhotoByName`     | `0x07DE` | capture photo | Fetch a capture photo by filename. | ✗ |
| `GetPhotoNamesByTime`| `0x07E0` | capture photo | List capture-photo names in a time range. | ✗ |
| `GetPicList`         | `0x271D` | picture    | List names in the "picture" store. | ✗ |
| `GetCapturePicByList`| `0x271C` | picture    | Fetch capture pictures by list. | ✗ |
| `DownloadPicture`    | `0x272D` | picture    | Download a named picture. | ✗ |
| `UploadUserPhoto`    | `0x2719` | **write**  | Upload a user portrait. | ✗ (out of scope) |
| `UploadPicture`      | `0x272B` | **write**  | Upload a picture. | ✗ (out of scope) |
| `UploadTheme`        | `0x272A` | **write**  | Upload a UI theme. | ✗ (out of scope) |

◐ = the data is reachable through a different mechanism openzk already uses
(e.g. the buffered table read), so a dedicated wrapper isn't exposed.
✗ on the read commands = catalogued but not wrapped in v1; ✗ on writes = out of
scope by design (openzk is read-only).

## Response / status codes

| Code | Meaning |
|------|---------|
| `0x07D0` | `ACK_OK` — success (or "no data" for some file reads). |
| `0x05DC` | buffer/content **header** (carries the payload size). |
| `0x05DD` | buffer/content **data** (the actual bytes, e.g. a JPEG). |
| `0x1379` | "no photo for this user". |
| `0x1375` | command not supported on this firmware. |
| `0x07D1` | error / NAK. |
| `0xFFFF` | unsupported / invalid. |

## A note on enrollment "biophotos"

On some firmware, the visible-light **face enrollment photo** shown at check-in is
delivered only through the device's **PUSH/ADMS** channel (device-to-server
HTTP), not the pull SDK on port 4370 — even the official SDK's pull commands do
not expose it there. `openzk` is a pull-SDK client, so it surfaces the stored
**user portrait** (`DownloadUserPhoto`) and **face templates** (`GetUserFace`),
but not those push-only enrollment frames. This is a firmware design fact, noted
here for interoperability.
