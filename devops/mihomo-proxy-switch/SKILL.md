---
name: mihomo-proxy-switch
description: Switch mihomo (Clash Meta) proxy nodes and verify exit IP via API. Use when user wants to change proxy, check current node, or verify IP location.
license: MIT
compatibility: Requires mihomo running with API enabled on port 9090
metadata:
  author: huanxherta
  version: "1.0"
  category: devops
---

# Mihomo Proxy Switch

Switch mihomo (Clash Meta) proxy nodes and verify exit IP.

## Prerequisites

- mihomo running with secret `1234` on API port `9090`
- Config at `/home/hx/mihomo-config/config.yaml`

## Commands

### Get current proxy info

```bash
curl -s -H "Authorization: Bearer 1234" http://127.0.0.1:9090/proxies/手动选择
```

### List available nodes

```bash
curl -s -H "Authorization: Bearer 1234" http://127.0.0.1:9090/proxies/手动选择 | jq '.now'
```

### Switch node

```bash
curl -s -X PUT -H "Authorization: Bearer 1234" \
  -H "Content-Type: application/json" \
  -d '{"name": "node-name"}' \
  http://127.0.0.1:9090/proxies/手动选择
```

### Verify exit IP

```bash
curl -s --proxy http://127.0.0.1:7890 https://api.ipify.org
```

## Pitfalls

- Group name must match exactly (e.g. "手动选择")
- Node names are case-sensitive
- mixed-port is `7890`, TUN is `198.18.0.1/30`
