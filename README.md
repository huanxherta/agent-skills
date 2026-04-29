# Agent Skills

Hermes Agent 的技能库，严格遵循 [Agent Skills 规范](https://agentskills.io/specification)。

每个技能独立文件夹，包含 `SKILL.md`（frontmatter + 指令）及可选的 `scripts/`、`references/`、`assets/` 目录。

## 快速导航

| 分类 | 技能数 | 跳转 |
|------|--------|------|
| Chatbot | 1 | [→](#chatbot) |
| Creative | 1 | [→](#creative) |
| DevOps | 2 | [→](#devops) |
| Gaming | 1 | [→](#gaming) |
| GitHub | 1 | [→](#github) |
| MLOps | 1 | [→](#mlops) |

---

## 技能总览

### Chatbot

| 技能 | 用途 | 路径 |
|------|------|------|
| [astrbot-plugin-dev](#astrbot-plugin-dev) | AstrBot QQ 机器人插件开发 | [`chatbot/astrbot-plugin-dev/`](chatbot/astrbot-plugin-dev/) |

<details>
<summary><b>astrbot-plugin-dev</b></summary>

AstrBot QQ 机器人插件开发完整指南。基于 20+ 真实插件总结的开发规范，覆盖插件结构、装饰器、消息处理、LLM 集成、配置系统、数据持久化。

→ [完整文档](chatbot/astrbot-plugin-dev/SKILL.md)
</details>

### Creative

| 技能 | 用途 | 路径 |
|------|------|------|
| [architecture-diagram](#architecture-diagram) | 暗色主题架构图 | [`creative/architecture-diagram/`](creative/architecture-diagram/) |

<details>
<summary><b>architecture-diagram</b></summary>

生成暗色主题 SVG 架构图（HTML 内联），语义化配色，JetBrains Mono 字体。

→ [完整文档](creative/architecture-diagram/SKILL.md)
</details>

### DevOps

| 技能 | 用途 | 路径 |
|------|------|------|
| [ds2api-update](#ds2api-update) | 更新 ds2api Docker 容器 | [`devops/ds2api-update/`](devops/ds2api-update/) |
| [mihomo-proxy-switch](#mihomo-proxy-switch) | 切换 mihomo 代理节点 | [`devops/mihomo-proxy-switch/`](devops/mihomo-proxy-switch/) |

<details>
<summary><b>ds2api-update</b></summary>

从 GHCR 拉取最新镜像，重建容器，保留 env-file 和 config volume。

- 镜像：`ghcr.io/cjackhwang/ds2api:latest`
- 端口：`10055→5001`，nginx 反代 `10100`
- ⚠️ 必须带 `--env-file`，否则 admin 密码丢失

→ [完整文档](devops/ds2api-update/SKILL.md)
</details>

<details>
<summary><b>mihomo-proxy-switch</b></summary>

通过 mihomo API 切换代理节点、验证出口 IP。

- API 端口：`9090`，密钥：`1234`
- mixed-port：`7890`

→ [完整文档](devops/mihomo-proxy-switch/SKILL.md)
</details>

### Gaming

| 技能 | 用途 | 路径 |
|------|------|------|
| [galgame-unpacker](#galgame-unpacker) | 视觉小说资源解包 | [`gaming/galgame-unpacker/`](gaming/galgame-unpacker/) |

<details>
<summary><b>galgame-unpacker</b></summary>

解包 Softpal/Amuse Craft 引擎视觉小说游戏资源。支持 PAC 归档提取和 PGD 图片解码（GE/PGD3 格式，LZSS 压缩）。

- 已测试游戏：CRACK≡TRICK!
- 输出：PNG 格式图片（1280×720）

→ [完整文档](gaming/galgame-unpacker/SKILL.md)
</details>

### GitHub

| 技能 | 用途 | 路径 |
|------|------|------|
| [github-pr-workflow](#github-pr-workflow) | PR 全生命周期 | [`github/github-pr-workflow/`](github/github-pr-workflow/) |

<details>
<summary><b>github-pr-workflow</b></summary>

从创建分支到合并 PR 的完整流程，支持 gh CLI 或 GitHub REST API fallback。

→ [完整文档](github/github-pr-workflow/SKILL.md)
</details>

### MLOps

| 技能 | 用途 | 路径 |
|------|------|------|
| [huggingface-hub](#huggingface-hub) | HF Hub CLI 操作 | [`mlops/huggingface-hub/`](mlops/huggingface-hub/) |

<details>
<summary><b>huggingface-hub</b></summary>

Hugging Face Hub CLI（hf）：搜索、下载、上传模型/数据集，管理 Spaces。

→ [完整文档](mlops/huggingface-hub/SKILL.md)
</details>

---

## 目录结构

```
agent-skills/
├── README.md              ← 本文件
├── LICENSE
├── chatbot/
│   └── astrbot-plugin-dev/
│       └── SKILL.md
├── creative/
│   └── architecture-diagram/
│       └── SKILL.md
├── devops/
│   ├── ds2api-update/
│   │   └── SKILL.md
│   └── mihomo-proxy-switch/
│       └── SKILL.md
├── gaming/
│   └── galgame-unpacker/
│       ├── SKILL.md
│       └── scripts/
│           ├── unpack_pac.py
│           └── pgd_decoder.py
├── github/
│   └── github-pr-workflow/
│       └── SKILL.md
└── mlops/
    └── huggingface-hub/
        └── SKILL.md
```

## SKILL.md 规范

每个 `SKILL.md` 必须包含 YAML frontmatter：

```yaml
---
name: skill-name              # 必填，小写+连字符，≤64字符
description: 描述技能功能       # 必填，≤1024字符
license: MIT                  # 可选
compatibility: 环境要求         # 可选，≤500字符
metadata:                     # 可选
  author: huanxherta
  version: "1.0"
  category: devops
---
```

详见 [Agent Skills 官方规范](https://agentskills.io/specification)。

## 添加新技能

1. 在对应分类目录下创建文件夹（名称与 `name` 字段一致）
2. 编写 `SKILL.md`，严格遵循 frontmatter 规范
3. 可选添加 `scripts/`、`references/`、`assets/` 目录
4. 更新本 README 的技能总览表

## License

[MIT](LICENSE)
