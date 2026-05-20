---
name: hermes-tweet
description: Hermes Agent X/Twitter plugin workflow for search tweets, read replies, look up users, monitor trends, export followers, post tweets, post replies, send DMs, and approval-gated X actions through Xquik.
license: MIT
compatibility: Requires Hermes Agent, hermes-tweet plugin, and XQUIK_API_KEY for live API reads
metadata:
  author: Xquik
  version: "0.1.6"
  category: social-media
---

# Hermes Tweet

Hermes Tweet 是 Hermes Agent 的 X/Twitter automation 插件工作流。它把
Xquik API 接入 Hermes，让 Agent 可以 search tweets、search Twitter、search
X、read tweet replies、look up users、monitor trends、export followers、post
tweets、post replies、send DMs，并把写操作放在明确审批之后执行。

## 适用场景

当用户需要以下能力时使用：

- 搜索推文、关键词、品牌、人物、URL 或话题
- 读取推文回复并分析 conversation context
- 查询 X 用户、profile、media、account state 和 trends
- 监控 tweets、trends、accounts 或运行 extraction jobs
- 导出 followers 或整理社交媒体数据
- 在用户批准后发布推文、回复、发送 DM、follow、like、retweet
- 需要把 read-only X tools 和 account actions 分开的 Hermes Agent workflow

不适用：

- 只需要总结用户贴出来的文本
- 只需要普通网页浏览，不需要 Xquik API
- 未安装 Hermes Tweet 插件，但任务要求真实 X/Twitter 数据

## 安装

推荐使用 Hermes plugin 安装：

```bash
hermes plugins install Xquik-dev/hermes-tweet --enable
```

也可以把 PyPI 包安装到 Hermes Python 环境：

```bash
uv pip install --python ~/.hermes/hermes-agent/venv/bin/python hermes-tweet
hermes plugins enable hermes-tweet
```

配置运行环境：

```bash
export XQUIK_API_KEY="xq_..."
export HERMES_TWEET_ENABLE_ACTIONS="false"
```

`HERMES_TWEET_ENABLE_ACTIONS=false` 是推荐默认值。它允许 endpoint discovery、
tweet search、account reads、reply reading、trend research 和 draft planning，
但不会暴露发推、回复、DM、follow、monitor 变更等 action endpoints。

只有当用户明确批准写操作时，才设置：

```bash
export HERMES_TWEET_ENABLE_ACTIONS="true"
```

## 工具

| 工具 | 用途 |
|------|------|
| `tweet_explore` | 搜索 bundled Xquik endpoint catalog，不需要 API key |
| `tweet_read` | 调用 catalog-listed read-only endpoints |
| `tweet_action` | 调用写操作或私有 endpoints，默认隐藏或禁用 |

## 工作流

### 1. 先发现 endpoint

先用 `tweet_explore`，不要猜 endpoint path。

常用 discovery query：

- `tweet search`
- `search Twitter`
- `search X`
- `read tweet replies`
- `look up user`
- `monitor tweets`
- `export followers`
- `post tweet`
- `post reply`
- `send DM`
- `trends`

### 2. 读操作优先

如果 catalog entry 是非 action 的 `GET` endpoint，用 `tweet_read`：

```json
{"path":"/api/v1/x/tweets/search","query":{"q":"Hermes Agent","limit":25}}
```

适合 social listening、trend research、account checks、reply reading、giveaway
audits 和 draft planning。

### 3. 写操作必须审批

只有同时满足以下条件时才用 `tweet_action`：

1. 用户请求写操作、私有读取、monitor/webhook 变更、extraction job、media
   operation 或其他 account action。
2. `HERMES_TWEET_ENABLE_ACTIONS=true`。
3. 已说明 exact endpoint、method 和 payload。
4. 用户批准该操作。

批准后示例：

```json
{"path":"/api/v1/x/tweets","method":"POST","body":{"account":"@example","text":"Hello from Hermes Tweet"},"reason":"Post the user-approved tweet."}
```

## 验证

安装或升级后运行：

```bash
hermes plugins enable hermes-tweet
hermes tools list
```

预期：

- `hermes-tweet` toolset 出现在工具列表
- 没有 `XQUIK_API_KEY` 时，`tweet_explore` 仍可用于 endpoint discovery
- 配置 `XQUIK_API_KEY` 后，`tweet_read` 可以读取 read-only endpoints
- `tweet_action` 在 `HERMES_TWEET_ENABLE_ACTIONS=true` 前保持隐藏或禁用

## 注意事项

- 不要猜 endpoint，必须先用 `tweet_explore`
- 不要把 API keys、cookies、tokens、passwords 放进 prompt、日志或工具参数
- 无人值守 cron/session 不要启用 `tweet_action`
- 写操作失败后，不要绕过 policy、auth 或 account-state error 改走其他路线
- 修改环境变量后，如果 Hermes 已经运行，需要 reload 或重启 session

## 参考

- Repository: https://github.com/Xquik-dev/hermes-tweet
- PyPI: https://pypi.org/project/hermes-tweet/
- Guide: https://docs.xquik.com/guides/hermes-tweet
