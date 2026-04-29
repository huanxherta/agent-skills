---
name: ds2api-update
description: Update ds2api Docker container from upstream GHCR image. Use when user asks to check or update ds2api. Handles pull, compare, recreate with env-file preservation.
license: MIT
compatibility: Requires Docker, access to ghcr.io
metadata:
  author: huanxherta
  version: "1.0"
  category: devops
---

# ds2api Update

Update the ds2api Docker container from the upstream GHCR image.

## Architecture

- Image: `ghcr.io/cjackhwang/ds2api:latest`
- Container: `ds2api`, port `10055→5001`
- Nginx: listens `10100`, reverse proxies to `127.0.0.1:10055`
- Config: `/root/ds2api/config.json` mounted as volume
- Access URL: `119.45.171.58:10100`

## Steps

### 1. Pull latest image

```bash
docker pull ghcr.io/cjackhwang/ds2api:latest
```

### 2. Compare build dates

```bash
docker inspect ghcr.io/cjackhwang/ds2api:latest --format '{{.Created}}'
```

### 3. Recreate container

```bash
docker stop ds2api && docker rm ds2api
docker run -d --name ds2api -p 10055:5001 \
  -v /root/ds2api/config.json:/app/config.json:rw \
  --env-file /root/ds2api/.env \
  --restart always ghcr.io/cjackhwang/ds2api:latest
```

### 4. Verify

```bash
docker ps -f name=ds2api
curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:10055/
```

## Pitfalls

- **MUST** include `--env-file /root/ds2api/.env` — without it, admin password is lost on recreate!
- Do NOT map to port 10100 — nginx owns that port, causes `address already in use` error
- Config is volume-mounted, not baked into image — safe across updates
- ghcr.io pull may fail with TLS timeout from China — retry usually works
