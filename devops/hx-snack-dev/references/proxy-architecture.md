# /p/ HTTP(S) Proxy Architecture

`internal/mother/proxy.go` — Zero-config HTTP(S) reverse proxy through child nodes.

## Core Function: `Hub.ProxyHTTP(target, w, r)`

### Sequence
1. `pickChild()` — first-come from children map
2. `registerProxyStream(streamID, dataCh)` — stores in `tunnelStreams` + creates `tunnelReady` channel
3. Send `tunnel_open` WS message to child with target
4. Block on `tunnelReady` channel (child closes it via `tunnel_ready` message)
5. Create `proxyWriter` → wraps child WS writes as `tunnel_data` messages
6. Create `proxyReader` → reads from data channel, `io.Reader` for `http.ReadResponse`
7. **If target is `:443`**: wrap `proxyReader`+`proxyWriter` in `tunnelConn` (implements `net.Conn`), then `tls.Client(tconn, &tls.Config{ServerName: hostname})` — perform TLS handshake
8. Rewrite `r.URL` to point at target, scheme set to `http` or `https` based on port
9. Write outbound request via `outReq.Write(conn)` where `conn` is either raw `tunnelConn` (HTTP) or TLS-wrapped `tunnelConn` (HTTPS)
10. `http.ReadResponse(bufio.NewReader(conn), outReq)` reads response
11. Copy status, headers, body to `w`
12. `unregisterProxyStream(streamID)` cleanup

### tunnelConn (TLS adapter)
```go
type tunnelConn struct {
    reader *proxyReader
    writer *proxyWriter
    host   string
}
// Implements net.Conn: Read, Write, Close, LocalAddr, RemoteAddr,
// SetDeadline, SetReadDeadline, SetWriteDeadline
```

This adapter allows `tls.Client()` to treat the tunnel as a raw TCP connection for TLS handshake and encrypted data transfer.

### proxyWriter
```go
type proxyWriter struct {
    child    *ChildState
    streamID string
}
func (pw *proxyWriter) Write(p []byte) (int, error) {
    // Marshal + send tunnel_data via child.Conn.WriteMessage
}
```

### proxyReader
```go
type proxyReader struct {
    ch   chan []byte
    buf  []byte
    done bool
}
func (pr *proxyReader) Read(p []byte) (int, error) {
    // Drain buffered data, then block on channel
    // Channel close → io.EOF
}
```

### Registration
`registerProxyStream` / `unregisterProxyStream` are simplified versions of `RegisterTunnelStream` — no goroutine, caller manages the data channel lifecycle directly.

## Three URL Formats (All Supported)

The system supports three URL formats through two code paths:

### Format 1 & 2: `https://` and `http://` prefix (via RequestURI interceptor)
```bash
# /p/https://host/path  →  HTTPS with TLS
# /p/http://host/path   →  HTTP plaintext
```
Handled by the wrapper in `cmd/mother/main.go` BEFORE ServeMux cleans the path. Uses `r.RequestURI` which preserves `//`.

```go
wrapped := http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
    if strings.HasPrefix(r.RequestURI, "/p/http://") || strings.HasPrefix(r.RequestURI, "/p/https://") {
        path := strings.TrimPrefix(r.RequestURI, "/p/")
        useTLS := strings.HasPrefix(path, "https://")
        // Extract host, determine port, strip scheme prefix
        // Call hub.ProxyHTTP(target, w, r) directly
        return
    }
    mux.ServeHTTP(w, r)
})
```

### Format 3: Path-segment scheme (via in-mux /p/ handler)
```bash
# /p/https/host/path    →  HTTPS with TLS
# /p/http/host/path     →  HTTP plaintext
# /p/host/path          →  HTTP plaintext (backward compat)
```
Handled by the `/p/` handler registered in `internal/mother/api.go`. Uses path segments (`http/`, `https/`) instead of `://` to avoid Go's `//` normalization.

The in-mux handler stays registered as backward-compatible fallback.

## Handler in api.go (Path-Segment Format)

```go
mux.HandleFunc("/p/", func(w, r) {
    path := strings.TrimPrefix(r.URL.Path, "/p/")

    useTLS := false
    if strings.HasPrefix(path, "http/") {
        path = path[5:]
    } else if strings.HasPrefix(path, "https/") {
        useTLS = true
        path = path[6:]
    }

    target := path
    if idx := strings.Index(path, "/"); idx >= 0 {
        target = path[:idx]
    }
    if !strings.Contains(target, ":") {
        if useTLS { target += ":443" } else { target += ":80" }
    }

    r.URL.Path = "/p/" + path
    hub.ProxyHTTP(target, w, r)
})
```

## Key Design Decisions

- **Three URL formats**: `/p/https://host/path`, `/p/http://host/path`, `/p/http[s]/host/path`, `/p/host/path` all work.
- **Go ServeMux // normalization**: `http.ServeMux` collapses `//` to `/` in `r.URL.Path`. Workaround: main.go wrapper intercepts before ServeMux using `r.RequestURI` (which preserves raw URI).
- **TLS via `tunnelConn`**: `proxyReader`+`proxyWriter` wrapped as `net.Conn` → `tls.Client` does transparent TLS handshake and encryption over the raw TCP tunnel.
- **One-shot tunnels**: Each `/p/` request creates a fresh tunnel stream, proxies one request, then tears down. No persistent tunnel state.
- **First child always**: `pickChild()` returns the first child in map iteration order. Future: could add random selection or health-aware picking.