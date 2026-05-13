# Tunnel Bidirectional Flow — Detailed

## Why v1 wasn't enough

v1 tunnels were one-directional:
- `handleTunnelConn` read TCP → sent `tunnel_data` to child
- No handler for incoming `tunnel_data` from child → TCP
- Result: TCP connections hung waiting for response data that never came

## v2 Architecture

### Structures

```
TunnelManager
├── tunnels: map[id]→*Tunnel          # All tunnels
└── pools: map[port]→*TunnelPool      # Shared listeners
    └── TunnelPool
        ├── listener: net.Listener
        ├── backends: []*Tunnel        # Round-robin select
        └── nextIdx: uint64 (atomic)
```

### Data Flow

```
Client → Mother:PORT  ──TCP──▶ acceptLoop()
                                  │
                                  ▼ round-robin pick
                              handleBidirConn(tunnel, conn)
                                  │
                    ┌─────────────┼─────────────┐
                    ▼                           ▼
              TCP→Child                    Child→TCP
              conn.Read()              RegisterTunnelStream
                  │                      callback writes
                  ▼                      to conn
              tunnel_data               ▲
              via WS ──────▶     Hub dispatches
                              tunnel_data from
                              child's WS read loop
                                  ▲
                                  │
                    Child handleTunnel goroutine
                    target.Read → tunnel_data → mother
```

### Race Condition Avoided

Without `tunnel_ready`:
1. Mother sends `tunnel_open`, immediately reads TCP → sends `tunnel_data`
2. Child receives `tunnel_open`, starts `handleTunnel` goroutine
3. `handleTunnel` calls `net.DialTimeout` (could take seconds)
4. But `tunnel_data` packets from mother are already arriving
5. If `handleTunnel` hasn't registered the channel yet → data dropped

With `tunnel_ready`:
1. Mother sends `tunnel_open`, then blocks on `<-readyCh`
2. Child receives `tunnel_open` → dials target → registers channel → sends `tunnel_ready`
3. Hub handler closes `readyCh` → mother unblocks
4. Now mother starts reading TCP → guaranteed channel exists

### Load Balancing

```
Pool :8080 → [tunnel-A (child-1), tunnel-B (child-2), tunnel-C (child-3)]

Connection 1 → nextIdx=0 → tunnel-A (child-1)
Connection 2 → nextIdx=1 → tunnel-B (child-2)
Connection 3 → nextIdx=2 → tunnel-C (child-3)
Connection 4 → nextIdx=3%3=0 → tunnel-A (child-1)
...
```

Adding a tunnel to existing pool: just `pool.backends = append(pool.backends, t)`.

Removing last tunnel from pool: close pool.cancel, close listener, delete from pools map.