# Python Child — Protocol Implementation Notes

## msgpack Wire Format

Go mother uses `github.com/vmihailenco/msgpack/v5` with struct tags.
Python child hand-rolls encoder/decoder to avoid external deps.

### Type mapping (critical for compatibility)

| Go type | msgpack wire | Python hand-roll |
|---------|-------------|-----------------|
| `string` | fixstr / str8/16/32 (`0xa0-0xbf`, `0xd9-0xdb`) | `str` → fixstr (≤31) or str8/16/32 |
| `[]byte` | bin8/16/32 (`0xc4-0xc6`) | `bytes` → bin8/16/32 |
| `int` / `int64` | fixint (`0x00-0x7f`, `0xe0-0xff`) or int8/16/32/64 (`0xd0-0xd3`) or uint8/16/32/64 (`0xcc-0xcf`) | `int` → fixint/uint/int depending on range |
| `float64` | float64 (`0xcb`) | `float` → float64 |
| `bool` | false (`0xc2`) / true (`0xc3`) | `bool` → false/true |
| `nil` | nil (`0xc0`) | `None` → nil |
| `map[string]interface{}` | fixmap (`0x80-0x8f`) or map16/32 (`0xde-0xdf`) | `dict` → fixmap or map16/32 |
| `[]interface{}` | fixarray (`0x90-0x9f`) or array16/32 (`0xdc-0xdd`) | `list`/`tuple` → fixarray or array16/32 |
| `struct` | fixmap with string keys | N/A (child only receives maps, never sends structs) |

### Common pitfalls

1. **`bytes` vs `str`**: Go `[]byte` in `TunnelDataPayload.Data` is msgpack `bin`. Python must decode as `bytes`, not `str`. If the decoder incorrectly treats `bin` as `str`, tunnel data is corrupted. The hand-rolled `_read_bytes()` preserves raw bytes.

2. **int overflow**: Go `uint64` (e.g. `MemTotalBytes` from monitor) can exceed Python's ease of representation. msgpack `uint64` (`0xcf`) is decoded correctly via `struct.unpack('>Q')` → Python `int` (unbounded).

3. **empty payload**: Go `NewMessage(type, payload)` with `payload=nil` omits the `payload` field entirely. Python `make_msg(type, None)` also omits it. Both sides handle missing `payload` key gracefully.

## WebSocket Client

Hand-rolled to avoid `websocket-client` dependency.

### Handshake
```
Client → Server: GET /path HTTP/1.1 + Upgrade + Sec-WebSocket-Key
Server → Client: HTTP/1.1 101 + Sec-WebSocket-Accept
```
Verify accept hash = `base64(sha1(key + "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"))`.

### Frame Format
```
 0                   1                   2                   3
 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
+-+-+-+-+-------+-+-------------+-------------------------------+
|F|R|R|R| opcode|M| Payload len |    Extended payload length    |
|I|S|S|S|  (4)  |A|     (7)     |          (16/64)              |
|N|V|V|V|       |S|             |   (if payload len==126/127)   |
| |1|2|3|       |K|             |                               |
+-+-+-+-+-------+-+-------------+ - - - - - - - - - - - - - - - +
|     Extended payload length continued, if payload len==127    |
+ - - - - - - - - - - - - - - - +-------------------------------+
|                               |  Masking-key (if MASK set)    |
+-------------------------------+-------------------------------+
| Masking-key (continued)       |          Payload Data         |
+-------------------------------- - - - - - - - - - - - - - - - +
:                     Payload Data continued ...                :
+ - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - +
```

### Key rules
- **Client→Server frames MUST be masked** (MASK bit = 1, 4-byte random mask key)
- **Server→Client frames are unmasked** (MASK bit = 0)
- Control frames (ping/pong/close) max payload 125 bytes
- Auto-respond to PING with PONG (echo payload)
- **⚠️ Byte-order in frame header**: `struct.pack()` format strings for multi-byte fields (`H`, `Q`) MUST use big-endian prefix `>` — e.g. `struct.pack('>BBH', ...)`, `struct.pack('>BBQ', ...)`. Native byte order on x86 is little-endian; WebSocket wire format is big-endian. Omitting `>` causes corrupted length fields for frames > 126 bytes → mother rejects with `websocket: bad MASK`.

### Recv loop
The `recv()` method handles fragmentation implicitly — reads one complete frame per call. FIN bit is assumed set (mother sends unfragmented). Uses `_read_exact(n)` to buffer and reassemble partial TCP reads.

## System Monitoring (no psutil)

All metrics from `/proc` filesystem:

| Metric | Source | Parsing |
|--------|--------|---------|
| CPU % | `/proc/stat` line 1 | `(total - idle) / total * 100` |
| Memory | `/proc/meminfo` | `MemTotal` and `MemAvailable` → `used = total - avail` |
| Disk | `os.statvfs('/')` | `f_blocks * f_frsize` total, minus `f_bfree` |
| Network | `/proc/net/dev` | Sum rx bytes (field 1) and tx bytes (field 9) across all ifaces |
| Uptime | `/proc/uptime` | First field, truncated to int |

### Report payload (msgpack map keys)
```python
{"cpu": float, "mem_used": int, "mem_total": int,
 "disk_used": int, "disk_total": int,
 "net_rx": int, "net_tx": int, "uptime": int}
```

Only `cpu` is float64; all others are integer (sent as msgpack int/uint, decoded by Go as uint64/int64).