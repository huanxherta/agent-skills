# Debugging Pitfalls — hx-snack

## Silent tunnel failures: the debugging checklist

When a tunnel is created but requests hang/time out with no response:

### 1. Is the child binary up-to-date?
Check child version: look for `[child] tunnel request:` in remote child logs.
If absent: child binary doesn't have bidirectional tunnel support → re-download from `/dl/child`.

### 2. Is the tunnel using the correct child ID?
After mother restart, child gets a NEW random ID. Query `/api/children`:
```bash
curl -s http://119.45.171.58:10300/api/children | python3 -c "import sys,json; [print(c['id']) for c in json.load(sys.stdin)['children']]"
```
Delete stale tunnels and re-create with the fresh child ID.

### 3. Can the child reach the target?
```bash
curl -X POST http://119.45.171.58:10300/api/tasks \
  -H "Content-Type: application/json" \
  -d '{"child_id":"<id>","command":"curl","args":["--connect-timeout","5","http://target"]}'
```
Wait 5-6s then check result at `/api/tasks/<task_id>`.

### 4. Is the listener actually accepting connections?
```bash
ss -tlnp | grep <listen_port>
```
If not listening: tunnel pool may have been cleaned up or never created.

### 5. Add debug logging to handleBidirConn
See SKILL.md Pitfalls section for the exact log statements. Rebuild mother and restart.

### 6. Multiple mother processes?
```bash
ps aux | grep mother | grep -v grep
```
If more than one: `kill $(pgrep mother)` and restart clean.

### 7. Testing locally — TUN proxy trap
Server runs mihomo TUN (tun0, 198.18.0.1/30). Connections to `119.45.171.58` from local are intercepted:
```bash
# ✅ Test locally
curl http://127.0.0.1:18080/...
curl http://10.10.0.15:18080/...

# ❌ Will silently fail
curl http://119.45.171.58:18080/...
```
External clients are unaffected.

### 8. `/p/` proxy returns empty body or 503
- **503 "no children online"**: child hasn't reconnected after mother restart. Wait 5-10s, check `/api/children`.
- **Empty reply / timeout**: child might have reconnected but tunnel hasn't propagated yet. Child takes ~2-3s to register after WS connect. Retry.
- **Silent failure with no proxy log**: the `/p/` handler may not have been reached. Check `tail -f mother.err.log | grep proxy` — if no output, the request hit a different handler (e.g. static file server).
- **TLS handshake failure**: target `:443` but the remote host doesn't speak TLS on that port. The `tls.Client.Handshake()` error will appear in `[proxy] ... TLS handshake error:` log.

## WebSocket Connection Diagnostics

### Symptom: "Flashing node" on dashboard

A child node appears briefly on the dashboard then disappears, or the online count flickers. Two root causes:

#### A. Legitimate child with `bad MASK` error (rapid reconnect loop)

When `gorilla/websocket` server reads a frame with an invalid masking key, it fires `websocket: bad MASK` and disconnects. The child immediately reconnects → appears briefly → disconnects → repeats. This can generate **millions** of connect/disconnect cycles and balloon `mother.err.log` to hundreds of MB.

**Diagnose:**
```bash
# Check for bad MASK storm
grep 'bad MASK' /root/hx-snack/mother.err.log | wc -l

# Check restart count (each restart causes reconnect)
grep -c 'Mother listening' /root/hx-snack/mother.err.log

# Check connection/disconnection counts
grep -c 'child.*connected' /root/hx-snack/mother.err.log
grep -c 'disconnected' /root/hx-snack/mother.err.log

# See unique children that successfully registered
grep 'registered:' /root/hx-snack/mother.err.log | \
  awk -F'registered: ' '{print $2}' | sort | uniq -c | sort -rn
```

**Root cause**: `bad MASK` means the WebSocket client sent a frame without proper XOR masking. Go's `gorilla/websocket` dialer auto-masks by default — if this error appears, the child-side WebSocket client may be a different library, a hand-rolled implementation with broken masking, or a non-WebSocket client altogether.

#### B. Non-WebSocket client (port scanner / misconfigured client)

A TCP connection is established but the client never sends a valid HTTP upgrade request. The Go HTTP server accepts the connection but can't parse the data → the connection sits in ESTABLISHED state with data stuck in the kernel's receive buffer.

**Diagnose with `ss -tnp`:**
```bash
# List all connections to mother port, show Send-Q (stuck data indicator)
ss -tnp 'sport = :10300'

# Filter out known-good connections (mihomo proxy, browser, legitimate child)
ss -tnp 'sport = :10300' | grep -v '119.45.171\|198.18.0.1\|1.15.226.223'
```

**Key indicator**: `Send-Q > 0` means the kernel received data but the application hasn't read it. This happens when:
- Client sent non-HTTP binary data → Go HTTP parser can't parse it → data stays unread
- Client sent an HTTP request but to the wrong path (e.g., `GET /` instead of `GET /ws`) → HTML page returned but the client never reads it → server's response data stuck in Send-Q

**Verify if an IP is a legitimate child:**
```bash
# Check if the IP ever registered in logs
grep '<suspect_ip>' /root/hx-snack/mother.err.log

# If zero matches → never completed WebSocket handshake → NOT a child
```

**Identify the IP's origin:**
```bash
curl -s "http://ip-api.com/json/<suspect_ip>?lang=zh-CN" | python3 -m json.tool
```

### Log file size explosion

A `bad MASK` reconnection storm can grow `mother.err.log` to hundreds of MB in hours. The log file at `/root/hx-snack/mother.err.log` is rotated manually:

```bash
# Check size
ls -lh /root/hx-snack/mother.err.log

# Truncate if needed (after fixing the root cause)
truncate -s 0 /root/hx-snack/mother.err.log
```

### Unrecognized connections on port 10300

The mother port is publicly exposed. Unknown IPs connecting at TCP level but never completing WebSocket handshake are almost always **port scanners or random internet noise**, not legitimate children with configuration issues. A legitimate child will always appear in the logs as `child <id> connected` within milliseconds of TCP establishment.