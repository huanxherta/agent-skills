---
name: astrbot-plugin-dev
description: Complete AstrBot plugin development guide. Covers setup, message events, sending messages, config, AI calls, storage, session control, publishing, and platform adapters.
tags: astrbot, plugin, python, bot, qq, telegram
---

# AstrBot 插件开发指南

## 前置要求
- Python 编程经验
- Git / GitHub 使用经验
- 开发者 QQ 群: `975206796`

## 快速开始

### 1. 创建插件仓库
- 模板: https://github.com/Soulter/helloworld → Use this template
- 仓库名格式: `astrbot_plugin_xxx`（全小写、无空格、简短）

### 2. 克隆到本地
```bash
git clone https://github.com/AstrBotDevs/AstrBot
mkdir -p AstrBot/data/plugins
cd AstrBot/data/plugins
git clone 你的插件仓库地址
```

### 3. metadata.yaml（必须修改）
```yaml
name: astrbot_plugin_xxx
desc: 插件描述
version: 1.0.0
author: your_name
repo: https://github.com/xxx/astrbot_plugin_xxx
# 可选字段:
display_name: 展示名
support_platforms: [aiocqhttp, telegram, discord]
astrbot_version: ">=4.16,<5"
```

支持的平台: `aiocqhttp`, `qq_official`, `telegram`, `wecom`, `lark`, `dingtalk`, `discord`, `slack`, `kook`, `vocechat`, `weixin_official_account`, `satori`, `misskey`, `line`

### 4. 插件结构
```
astrbot_plugin_xxx/
├── main.py          # 插件入口
├── metadata.yaml    # 元数据（必须）
├── _conf_schema.json # 配置schema（可选）
├── requirements.txt  # 依赖（可选）
├── logo.png         # Logo 256x256（可选）
└── README.md
```

### 5. 调试
- 启动 AstrBot 本体
- 修改代码后在 WebUI → 插件管理 → `...` → 重载插件
- 加载失败可点"尝试一键重载修复"

### 6. 依赖管理
在插件目录下创建 `requirements.txt`，使用异步库：
- ✅ `aiohttp`, `httpx`
- ❌ `requests`（不要用）

## 最小插件示例

```python
from astrbot.api.star import Context, Star, register
from astrbot.api.event import filter, AstrMessageEvent

@register("astrbot_plugin_hello", "Author", "Hello Plugin", "1.0.0")
class HelloPlugin(Star):
    def __init__(self, context: Context, config: dict):
        super().__init__(context)
        self.config = config
    
    @filter.command("hello")
    async def hello(self, event: AstrMessageEvent):
        yield event.plain_result("Hello, AstrBot!")
```

⚠️ 注意 `__init__` 有 `(context, config)` 两个参数。即使插件不需要配置，也要保留 `config` 参数，否则以后加配置时会踩坑。

## 核心 API

### 接收消息 - 装饰器
```python
# 命令触发
@filter.command("命令名")
async def handler(self, event: AstrMessageEvent):
    yield event.plain_result("回复")

# 正则匹配
@filter.regex("正则表达式")
async def handler(self, event: AstrMessageEvent):
    pass

# 事件监听
@filter.event_message_type(filter.EventMessageType.ALL)
async def handler(self, event: AstrMessageEvent):
    pass

# 关键词
@filter.keyword("关键词")
async def handler(self, event: AstrMessageEvent):
    pass

# 所有消息（需 permission）
@filter.permission_type(filter.PermissionType.ADMIN)
@filter.event_message_type(filter.EventMessageType.ALL)
async def handler(self, event: AstrMessageEvent):
    pass
```

### 发送消息
```python
# 纯文本
yield event.plain_result("文本")

# At 用户
yield event.at_result(event.get_sender_id())

# 合并结果
result = event.plain_result("第一句")
result.chain.extend(event.plain_result("第二句").chain)
yield result

# 图片（URL）
from astrbot.api.message_components import Image
yield event.image_result("https://example.com/img.png")

# 回复消息
yield event.reply("回复内容")
```

### 调用 AI
```python
# 获取当前 provider
provider = self.context.get_using_provider()
if provider:
    # 文本对话
    result = await provider.text_chat(
        prompt="用户消息",
        session_id=event.session_id,
        contexts=[]  # 可传入上下文
    )
    yield event.plain_result(result.completion_text)
    
    # 带工具调用
    result = await provider.text_chat(
        prompt="用户消息",
        func_tool_manager=self.context.get_llm_tool_manager()
    )
```

### 插件配置
### 插件配置
```json
// _conf_schema.json
{
  "api_key": {
    "description": "API密钥",
    "type": "string",
    "default": ""
  },
  "max_count": {
    "description": "最大数量",
    "type": "int",
    "default": 10
  }
}
```

**⚠️ 配置读取的正确方式：**

必须在 `__init__` 中接收 `config` 参数，不能用 `self.context.get_config()`：

```python
@register("astrbot_plugin_xxx", "Author", "Desc", "1.0.0")
class MyPlugin(Star):
    def __init__(self, context: Context, config: dict):
        super().__init__(context)
        self.config = config  # ✅ 正确
        # self.context.get_config()  ❌ 不存在，会报错
    
    @filter.command("test")
    async def test(self, event: AstrMessageEvent):
        api_key = self.config.get("api_key", "")  # 读取配置
```

配置文件路径: `/root/astrbot/data/config/astrbot_plugin_{name}_config.json`

### 命令冲突避免

当有多个插件功能相似时（如两个画图插件），需要用不同命令前缀区分：
- 插件A: `画xxx` → Gemini画图
- 插件B: `画画xxx` → GPT-Image画图

不要用相同的 `@filter.regex()` 模式，否则两个插件都会触发。
**读取配置 — `__init__` 签名必须包含 `config` 参数**:
```python
class MyPlugin(Star):
    def __init__(self, context: Context, config: dict):
        super().__init__(context)
        self.config = config  # 这就是配置！

    async def handler(self, event):
        api_key = self.config.get("api_key", "")  # 用 .get() 安全访问
```

⚠️ **不要用 `self.context.get_config()`** — 不存在这个方法，会报 AttributeError。
⚠️ **`config` 参数必须在 `__init__` 签名里**，否则配置全部读不到（静默回退到默认值）。

**配置文件位置**: `/root/astrbot/data/config/astrbot_plugin_xxx_config.json`
- WebUI 修改配置后会自动写入这个文件
- 也可以手动创建/编辑 JSON 文件，重启 AstrBot 生效
- 格式就是扁平 JSON，key 对应 schema 里的字段名

⚠️ **无配置插件也必须有合法 `_conf_schema.json`**：
- 不能为空对象 `{}` 或纯注释
- 每个字段必须有 `type` + `description` + `default`
- 无配置时用一个无用字段占位：
```json
{
  "_comment": {
    "description": "此插件无需配置",
    "type": "string",
    "default": ""
  }
}
```
- 格式错误会导致 `TypeError: string indices must be integers` 并载入失败

### 存储
⚠️ `context.get_data()` 和 `context.set_data()` **不存在**，会报 AttributeError。

正确方式：用文件存储在插件数据目录：
```python
import os, json

DATA_DIR = "/root/astrbot/data/plugin_data/astrbot_plugin_xxx"

class MyPlugin(Star):
    def __init__(self, context: Context):
        super().__init__(context)
        os.makedirs(DATA_DIR, exist_ok=True)

    def _load(self, key: str) -> dict:
        path = os.path.join(DATA_DIR, f"{key}.json")
        if os.path.exists(path):
            with open(path) as f:
                return json.load(f)
        return {}

    def _save(self, key: str, data: dict):
        with open(os.path.join(DATA_DIR, f"{key}.json"), "w") as f:
            json.dump(data, f, ensure_ascii=False)
```

### 会话控制器
```python
from astrbot.core.utils.session_waiter import session_waiter, SessionController

@filter.command("ask")
async def ask(self, event: AstrMessageEvent):
    yield event.plain_result("请输入你的名字：")
    
    @session_waiter(timeout=30)
    async def get_name(controller: SessionController, event: AstrMessageEvent):
        name = event.message_str
        controller.stop()
        yield event.plain_result(f"你好，{name}！")
    
    await get_name(event)
```

### 文转图
```python
from astrbot.core.utils.html2img import html2img

html = "<h1>Hello</h1><p>World</p>"
img_bytes = await html2img(html)
yield event.image_result(img_bytes)
```

## 开发原则
- 功能需经过测试
- 良好注释
- 持久化数据存 `data` 目录（不是插件目录）
- 良好的错误处理，不要让插件崩溃
- 用 `ruff` 格式化代码
- 用 `aiohttp`/`httpx`，不用 `requests`
- 优先给原插件提交 PR 而非另写

## 发布插件
1. 代码推送到 GitHub
2. 确保 metadata.yaml 完整
3. 有 README.md
4. 有 requirements.txt（如有依赖）
5. AstrBot 插件市场会自动索引

## 安装插件到服务器

```bash
# 复制到插件目录
cp -r astrbot_plugin_xxx /root/astrbot/data/plugins/

# 重启 AstrBot 加载
systemctl restart astrbot.service

# 检查加载状态
journalctl -u astrbot.service --since "10 sec ago" | grep "astrbot_plugin_xxx"
```

成功标志: `Plugin astrbot_plugin_xxx (1.0.0) by Author: 描述`
失败标志: `插件 astrbot_plugin_xxx 载入失败` → 看后面的 Traceback

## 禁用插件

**❌ 不要用 `.disabled` 后缀**：AstrBot会扫描所有目录，包括 `.disabled` 结尾的，会报 `ModuleNotFoundError`。

**✅ 正确方式**：移到 `plugins_backup/` 目录：
```bash
mkdir -p /root/astrbot/data/plugins_backup
mv /root/astrbot/data/plugins/astrbot_plugin_xxx /root/astrbot/data/plugins_backup/
systemctl restart astrbot.service
```

## Pitfalls

### _conf_schema.json 必须是有效 schema
❌ 错误写法（注释不是有效字段）:
```json
{
  "comment": "此插件无需配置"
}
```
会报: `TypeError: string indices must be integers, not 'str'`

✅ 正确写法（无配置用空对象或带 type 的字段）:
```json
{
  "_comment": {
    "description": "无需配置",
    "type": "string",
    "default": ""
  }
}
```
或直接不创建 `_conf_schema.json` 文件。

### metadata.yaml 必须存在且格式正确
AstrBot 依赖它识别插件。缺失会导致插件不被加载，无明显报错。

⚠️ **不要在 metadata.yaml 开头加 `---`** YAML 文档分隔符，会导致 "expected a single document in the stream" 警告。直接写内容即可：
```yaml
# ✅ 正确
name: astrbot_plugin_xxx
desc: 描述
version: 1.0.0

# ❌ 错误 — 不要加 ---
---
name: astrbot_plugin_xxx
```

### 插件目录名必须与 metadata.yaml 中的 name 一致
不一致会导致配置和数据存储路径错误。

### 不要用 requests
AstrBot 是异步框架，用 `requests` 会阻塞事件循环。必须用 `aiohttp` 或 `httpx`。

## 踩坑记录

### ⚠️ AstrBot CLI 必须在项目根目录运行

`astrbot run` 命令必须在 AstrBot 安装目录下执行：`/root/astrbot/`。在其他目录下运行会报错：

```
Error: Runtime error: /path/to/somewhere is not a valid AstrBot root directory
```

**正确启动方式**：
```bash
cd /root/astrbot && astrobot run
# 或
cd /root/astrbot && /root/.local/share/uv/tools/astrbot/bin/python3 /root/.local/bin/astrbot run
```

### ⚠️ gpt-image-2 不能用 /v1/images/generations 或 /v1/images/edits

gpt-image-2、Gemini、Grok 等新一代多模态生图模型的**文生图和图生图都走 `/v1/chat/completions`**。如果文生图发了 `/v1/images/generations`，API 中转站返回 502/401，生成失败。

**正确做法**：文生图也用 Chat Completions，只是 `messages` 中不带 `image_url` 字段：

```python
# ✅ 文生图（无参考图）
{"model": "gpt-image-2", "messages": [
    {"role": "user", "content": [{"type": "text", "text": "一只猫"}]}
]}

# ✅ 图生图（有参考图）
{"model": "gpt-image-2", "messages": [
    {"role": "user", "content": [
        {"type": "image_url", "image_url": {"url": "data:image/png;base64,..."}},
        {"type": "text", "text": "改成蓝色"}
    ]}
]}
```

统一用 `_chat_generate` 方法，`image_bytes=None` 时只发文本，非 None 时加图片。

### 获取消息中的图片（引用/内嵌）

用 `event.get_messages()` + 消息组件类型来获取图片URL，不要直接遍历 `event.message_obj.message`：

```python
from astrbot.api.event import AstrMessageEvent
from astrbot.api.message_components import Image, Reply

async def _get_image_url(self, event: AstrMessageEvent) -> str | None:
    """从消息链或引用消息中获取图片URL"""
    chain = event.get_messages()

    # 1. 先检查引用消息中的图片
    reply_seg = next((seg for seg in chain if isinstance(seg, Reply)), None)
    if reply_seg and reply_seg.chain:
        for seg in reply_seg.chain:
            if isinstance(seg, Image) and seg.url:
                return seg.url

    # 2. 再检查当前消息中的图片
    for seg in chain:
        if isinstance(seg, Image) and seg.url:
            return seg.url

    return None
```

关键点:
- `event.get_messages()` 返回解析后的消息链（list of segments）
- `isinstance(seg, Reply)` 检查引用回复段，`reply_seg.chain` 是被引用消息的链
- `isinstance(seg, Image)` 检查图片段，`seg.url` 是图片URL
- 图片下载用 `aiohttp` 异步请求，不要用 `requests`

### ❌ event.get_match() 不存在

`@filter.regex()` 装饰器匹配后，**不能用 `event.get_match()`**（会报 `AttributeError: 'AiocqhttpMessageEvent' object has no attribute 'get_match'`）。

正确做法：用 `event.message_str` + `re.match()` 手动提取：

```python
import re
from astrbot.api.event import AstrMessageEvent, filter

@filter.regex(r"^画(.+)")
async def draw(self, event: AstrMessageEvent):
    msg = event.message_str.strip()
    match = re.match(r"^画(.+)", msg)
    if not match:
        return
    prompt = match.group(1).strip()
    # ... 处理逻辑
```

- `_conf_schema.json` 格式不对 → `TypeError: string indices must be integers` 载入失败
- 无配置插件也必须有合法 schema，用 `_comment` 占位
- `@register` 装饰器参数顺序: (name, author, desc, version)
- Handler 前两个参数必须是 `self`, `event`
- 插件类文件必须叫 `main.py`
- 持久化数据存 `data` 目录，别存插件目录（重装会被覆盖）
- 不要用 `requests`，用 `aiohttp`/`httpx`

### 禁用/卸载插件

**正确做法**: 把插件目录移到 `plugins_backup/`：
```bash
mkdir -p /root/astrbot/data/plugins_backup
mv /root/astrbot/data/plugins/astrbot_plugin_xxx /root/astrbot/data/plugins_backup/
systemctl restart astrbot.service
```

**❌ 不要改名为 `.disabled` 后缀** — AstrBot 会扫描 `plugins/` 下所有子目录（包括 `.disabled` 结尾的），尝试导入模块导致 `ModuleNotFoundError` 报错。

**重新启用**: 从 `plugins_backup/` 移回 `plugins/` 即可。

### 命令前缀冲突

多个插件的正则匹配会冲突。例如两个画图插件都用 `^画(.+)` ，只有一个能触发。

**解决**: 用不同前缀区分（`画` vs `画画` vs `imagine`），或者用 `@filter.command("画")` 精确命令而非正则。

### ⚠️ GPT-Image API prompt 长度导致上游超时

插件不会截断 prompt，但上游 New API → OpenAI 链路对长 prompt 有超时风险：
- ~400字符 → 正常出图（~80秒）
- ~800字符 → 524 Cloudflare 超时

精简 prompt 控制在 400-500 字符以内。详细行为数据见 `references/17-gpt-image-api.md`。

### ⚠️ AstrBot via uv tool 版本号陷阱

AstrBot 通过 `uv tool` 安装时，版本号可能高于 PyPI（如 v4.24.0 > PyPI 4.14.6）。直接 `uv tool upgrade` 可能反而降级。升级前先用 `pip index versions astrbot` 确认 PyPI 最新版本。

正确的升级方式（允许预发布版本）：
```bash
uv tool upgrade astrbot --prerelease allow
```

### ⚠️ AstrBot 升级后 apscheduler 3→4 不兼容导致启动崩溃

**症状**: `uv tool upgrade astrbot --prerelease allow` 后 AstrBot 启动失败：
```
ModuleNotFoundError: No module named 'apscheduler.schedulers'
```

**原因**: AstrBot v4.24.2 的依赖 `apscheduler` 被从 3.11.2 拉到 4.0.0a6，apscheduler 4.x 重构了整个 API（`apscheduler.schedulers.background` 模块不存在了），但 AstrBot 代码仍依赖 3.x API。

**修复**: 手动回滚 apscheduler 到 3.x：
```bash
# 先停止服务防崩溃循环
systemctl stop astrbot

# 在 AstrBot 的 venv 里回滚 apscheduler
/root/.local/share/uv/tools/astrbot/bin/pip install "apscheduler>=3.11,<4"

# 重启
systemctl restart astrbot
```

**排查步骤**:
1. `journalctl -u astrbot -n 30` 看崩溃日志
2. 确认是 `apscheduler.schedulers` ModuleNotFoundError
3. `/root/.local/share/uv/tools/astrbot/bin/pip show apscheduler` 看当前版本
4. 回滚到 3.x

⚠️ 每次 `uv tool upgrade` 都可能再次拉到 4.0.0a6，需要重复回滚。直到 AstrBot 官方适配 apscheduler 4.x。

**快速修复命令**:
```bash
systemctl stop astrbot
/root/.local/share/uv/tools/astrbot/bin/pip install "apscheduler>=3.11,<4"
systemctl restart astrbot
```

### ❌ `event.message_str` 在引用消息时丢弃 Plain 文本（致命坑）

**根本问题**：当消息链同时包含 `Reply` 和 `Plain` 段时（如用户引用图片+发送"画画 xxx"），`event.message_str` 只返回 `[引用消息]` 而**完全不包含 Plain 段的文本**。Plain 段也不会包含"画画"（"画画"被 Reply 格式化吃掉了）。

**症状**：
- 不引用图片时 `画画 hello` → prompt="hello" ✅
- 引用图片+`画画 hello` → prompt=""（空）❌
- 日志显示 `get_messages count=2, types=['Reply', 'Plain']` 但 prompt 长度为 0

**修复（正确版 — 通用）**：只要有 Plain 段就用它（同时覆盖 Reply+Plain 和 Plain+Image 场景）：

```python
from astrbot.api.message_components import Image, Plain, Reply

@filter.regex(r"画画")
async def generate_image(self, event: AstrMessageEvent):
    chain = event.get_messages()
    msg = event.message_str.strip()

    # Plain segment 是权威文本源（message_str 在图片/引用时不可靠）
    plain_texts = [seg.text for seg in chain if isinstance(seg, Plain)]
    prompt = ""
    if plain_texts:
        text = " ".join(plain_texts).strip()
        match = re.search(r"画画\s*(.*)", text)
        prompt = match.group(1).strip() if match else text
    else:
        match = re.search(r"画画(.*)", msg)
        if match:
            prompt = match.group(1).strip()
```

### ❌ 正则匹配带 `^` 锚点 + 引用消息 = 匹配失败（次生问题）

**注意**：上面的 `event.message_str` 丢弃 Plain 文本是更根本的问题。如果你的 prompt **恰好没有被丢弃**（如用户没发图片，只是纯文本引用），那么以下次生问题才会出现：

用户引用一条消息并发送 `画画 xxx` 时，AstrBot 可能把消息拼成 `[引用消息] 画画 xxx`。如果插件用 `@filter.regex(r"^画画(.+)")` 或 `re.match(r"^画画(.+)", msg)`，`^` 要求"画画"在字符串开头，但前面有 `[引用消息]` 前缀，匹配失败→插件完全不触发。

**修复**：去掉 `^` 锚点，用 `re.search()` 代替 `re.match()`：
```python
# ❌ 错误 — 引用时失效
match = re.match(r"^画画(.+)", msg)

# ✅ 正确
match = re.search(r"画画(.+)", msg)
```

### ⚠️ 修改插件代码后必须清理 __pycache__

AstrBot 在进程重启时会重新导入插件模块，但 Python 的 `.pyc` 字节码缓存可能让旧代码继续生效。修改 `main.py` 后如果行为没变：

```bash
# 清理插件的字节码缓存
find /root/astrbot/data/plugins/astrbot_plugin_xxx -name '__pycache__' -exec rm -rf {} + 2>/dev/null
find /root/astrbot -name '*.pyc' -path '*plugin_xxx*' -delete 2>/dev/null
```

特别是在 `metadata.yaml` 版本号、`@register` 装饰器、或核心逻辑修改后，不清缓存可能导致日志显示的版本号与代码不一致。

### ⚠️ AstrBot 进程崩溃后可能残留 lock 文件

异常退出后 `/root/astrbot/astrbot.lock` 没清理，重启时报 `Cannot acquire lock file`：

```bash
rm -f /root/astrbot/astrbot.lock
# 然后重新启动
```

### ⚠️ 正则匹配不要用 `event.get_match()`

`@filter.regex()` 装饰器不会注入 match 对象。必须用 `event.message_str` + `re.match()` 手动提取：

```python
@filter.regex(r"^画画(.+)")
async def draw(self, event: AstrMessageEvent):
    msg = event.message_str.strip()
    match = re.match(r"^画画(.+)", msg)
    if not match:
        return
    prompt = match.group(1).strip()
```

### ⚠️ 获取图片用 `event.get_messages()` + `Image`/`Reply`

```python
from astrbot.api.message_components import Image, Reply

chain = event.get_messages()
# 先查引用消息
reply_seg = next((seg for seg in chain if isinstance(seg, Reply)), None)
if reply_seg and reply_seg.chain:
    for seg in reply_seg.chain:
        if isinstance(seg, Image) and seg.url:
            return seg.url
# 再查当前消息
for seg in chain:
    if isinstance(seg, Image) and seg.url:
        return seg.url
```

### ⚠️ 禁用插件用 `plugins_backup/` 目录

重命名为 `.disabled` 无效，AstrBot 仍会尝试加载。正确做法：

```bash
mkdir -p /root/astrbot/data/plugins_backup
mv /root/astrbot/data/plugins/astrbot_plugin_xxx /root/astrbot/data/plugins_backup/
```

详细踩坑记录见 `references/astrbot-plugin-pitfalls.md`。

⚠️ **命令前缀冲突**: 如果服务器上有多个功能相似的插件（如两个画图插件），用不同命令前缀区分（"画" vs "画画"），否则正则匹配会冲突。

尝试将 memorix（记忆系统）、万象画卷（AI画图）、mimo_tts（语音克隆）合并为一个插件时发现：

**为什么不行**：
- 每个插件 500-1800 行 main.py + 多层子模块，合并后 3000+ 行单文件不可维护
- 命令空间冲突：三个插件各自有 10-25 个命令/hook，统一前缀 `/ai` 后子命令爆炸
- 配置 schema 合并后 30+ 字段，用户配置困难
- 依赖冲突：memorix 要 faiss/numpy/scipy，omnidraw 只要 aiohttp，mimo_tts 要 pydub
- 功能域差异大：记忆(向量检索+知识图谱)、画图(多Provider容错)、TTS(音频合成) 粘不到一起

**正确做法**：分别安装独立插件，各管各的：
- `astrbot_plugin_memorix` — 长期记忆（Faiss向量+SciPy图谱+SQLite，双路检索+PageRank）
- `astrbot_plugin_omnidraw` — AI画图/视频（多Provider容错，人设自拍，提示词优化器）
- `astrbot_plugin_mimo_tts` — 语音合成（默认语音/克隆/设计三种模式）

**如果确实需要联动**（比如"记忆注入时自动语音朗读"），用 AstrBot 的事件 hook 机制让插件间通过消息链协作，而非合并代码。

### 大型插件子代理超时问题

对大型插件做深度代码分析时，子代理容易超时（600s限制）。应对策略：
- 先用 `read_file(limit=100)` 快速扫描每个文件的头部，理解结构
- 再针对性读取关键函数（on_llm_request、命令handler、核心算法）
- 不要让子代理一次分析太多文件，拆成更小的任务

### 调用 HF Space / 外部 API 的坑

**HF Space 冷启动超时**: CPU-basic 实例不活跃会休眠，冷启动可能需要 60-180 秒。aiohttp 默认超时 120 秒不够用，请求会静默失败（异常信息为空）。

修复方案：
1. 超时设为 300 秒: `aiohttp.ClientTimeout(total=300)`
2. 加保活机制，每 5 分钟 ping 一次 `/api/health` 防休眠
3. 错误日志要包含异常类型: `f"{type(e).__name__}: {e}"`（空错误信息很难排查）

```python
import asyncio
import aiohttp

KEEPALIVE_INTERVAL = 300  # 5分钟

class MyPlugin(Star):
    def __init__(self, context: Context):
        super().__init__(context)
        self.session = None
        self._keepalive_task = asyncio.create_task(self._keepalive_loop())

    async def _get_session(self):
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=300)  # 冷启动需要更长超时
            )
        return self.session

    async def _keepalive_loop(self):
        """定期 ping 防止 HF Space 休眠"""
        await asyncio.sleep(10)
        while True:
            try:
                session = await self._get_session()
                async with session.get(f"{HF_SPACE_URL}/api/health") as resp:
                    if resp.status != 200:
                        logger.warning(f"[MyPlugin] 保活 ping 异常: {resp.status}")
            except Exception as e:
                logger.warning(f"[MyPlugin] 保活 ping 失败: {type(e).__name__}: {e}")
            await asyncio.sleep(KEEPALIVE_INTERVAL)

    async def terminate(self):
        if self._keepalive_task and not self._keepalive_task.done():
            self._keepalive_task.cancel()
        if self.session and not self.session.closed:
            await self.session.close()
```

**排查外部 API 调用失败的步骤**:
1. 先用 `curl` 从服务器直接测 API 是否可达
2. 再用 Python `aiohttp` 测试（排除异步框架问题）
3. 检查 HF Space 状态: `GET /api/health` 看 `loaded_models` 和 `default_reference_audio_exists`
4. 看 AstrBot 日志: `journalctl -u astrbot -f | grep "插件名"`

### ⚠️ after_message_sent 里不要用 event.send() — 会吞掉后续消息

**致命 Bug**: 在 `@filter.after_message_sent()` 钩子里调用 `await event.send()` 会触发 AstrBot 事件传播终止机制，导致该用户后续所有消息被 AstrBot 收到但不回复（日志显示 `xxx 终止了事件传播`）。

**症状**: AstrBot 日志正常收到消息，`Prepare to send` 后紧跟 `xxx - after_message_sent 终止了事件传播`，然后什么也不发生。用户表现为"机器人不理我"。

**根因**: `event.send()` 内部走的是完整事件管道，AstrBot 在 `after_message_sent` 阶段调用它会触发传播终止逻辑。

**修复**: 用 `asyncio.create_task()` 把实际工作扔到后台，handler 立即 return：

```python
import asyncio
from astrbot.core.message.message_event_result import MessageEventResult

@filter.after_message_sent()
async def after_message_sent(self, event: AstrMessageEvent):
    text = self._pending_tts.pop(event.unified_msg_origin, None)
    if not text:
        return
    # ✅ 正确：create_task 后立即 return，不阻塞事件管道
    asyncio.create_task(self._send_voice_after(event, text))

async def _send_voice_after(self, event: AstrMessageEvent, text: str):
    """后台任务：实际的 TTS 合成和发送"""
    data = await self._tts(text)
    if data:
        record = Record.fromBase64(base64.b64encode(data).decode())
        client = event.get_platform_adapter()
        if client:
            await client.send_message(event, MessageEventResult(chain=[record]))
        # ❌ 错误：await event.send(event.chain_result([record]))
```

⚠️ **重要**: 仅用底层适配器 `client.send_message()` 替换 `event.send()` 是不够的——实测 `after_message_sent` handler 本身在 `await` 任何异步操作后返回时就会终止事件传播。必须用 `asyncio.create_task()` 让 handler 立即 return，把实际工作完全放到后台 task 中。

**排查步骤**:
1. `journalctl -u astrbot -f` 看日志
2. 搜索 `终止了事件传播` 关键词
3. 确认是哪个插件的哪个 hook
4. 检查 hook 内是否有 `event.send()` 调用

### 拦截/修改 LLM 回复 — `on_decorating_result`

在消息发送前拦截结果链，可追加语音、图片、修改文本等。常用于"概率发语音"、自动追加水印等场景。

```python
import random
import base64
from astrbot.api.event import filter, AstrMessageEvent
from astrbot.core.message.components import Plain, Record

class MyPlugin(Star):
    def __init__(self, context: Context):
        super().__init__(context)
        self.voice_probability = 0.2  # 20% 概率

    @filter.on_decorating_result()
    async def on_decorating_result(self, event: AstrMessageEvent):
        result = event.get_result()
        if not result or not result.chain:
            return
        if not result.is_llm_result():  # 只对 LLM 回复生效
            return
        if random.random() > self.voice_probability:
            return

        text = result.get_plain_text().strip()
        if not text or len(text) > 200:
            return

        # 合成语音并追加到结果链
        audio_data = await self._tts(text)
        if audio_data:
            b64 = base64.b64encode(audio_data).decode()
            result.chain.append(Record.fromBase64(b64))
```

关键点:
- `@filter.on_decorating_result()` — 消息发送前的 hook，可直接修改 `result.chain`
- `result.is_llm_result()` — 判断是否为 LLM 回复（排除命令回复等）
- `result.get_plain_text()` — 提取所有 Plain 组件的文本
- `Record.fromBase64(b64)` — 从 base64 创建语音消息段
- `Record(file=url)` — 从 URL 创建语音消息段
- 修改 `result.chain` 是原地生效的，无需返回值

### ⚠️ on_decorating_result 阻塞陷阱

**致命问题**: `on_decorating_result` 是同步阻塞的——它在消息发送 pipeline 中执行，任何耗时操作都会阻塞消息发送。如果在 hook 里调用外部 API（如 TTS），API 超时 = 消息永远发不出去。

**正确模式**: 异步分离——缓存快查 + 后台追加

```python
@filter.on_decorating_result()
async def on_decorating_result(self, event: AstrMessageEvent):
    result = event.get_result()
    if not result or not result.chain or not result.is_llm_result():
        return
    if random.random() > self.voice_probability:
        return
    text = result.get_plain_text().strip()
    if not text or len(text) > 200:
        return
    origin = event.unified_msg_origin

    # 只用缓存，不阻塞——没缓存就标记待合成
    cached = self._get_cached(text)
    if cached:
        result.chain.append(Record.fromBase64(base64.b64encode(cached).decode()))
    else:
        self._pending_tts[origin] = text  # 消息发完后再处理

@filter.after_message_sent()
async def after_message_sent(self, event: AstrMessageEvent):
    """消息发送后，异步合成语音 — 用 create_task 不阻塞事件管道"""
    origin = event.unified_msg_origin
    text = self._pending_tts.pop(origin, None)
    if not text:
        return
    # ⚠️ 必须用 create_task，handler 本身不能 await 任何东西，否则终止事件传播
    asyncio.create_task(self._send_voice_after(event, text))

async def _send_voice_after(self, event, text):
    try:
        data = await self._tts(text)
        if data:
            record = Record.fromBase64(base64.b64encode(data).decode())
            client = event.get_platform_adapter()
            if client:
                await client.send_message(event, MessageEventResult(chain=[record]))
    except Exception as e:
        logger.error(f"TTS 异步失败: {e}")
```

这样文本消息先发出去，语音后台追加，不会阻塞。

其他可用 hook:
- `@filter.on_llm_response()` — LLM 响应后触发，参数 `(event, response)`
- `@filter.on_llm_request()` — LLM 请求前触发，可修改 system prompt
- `@filter.after_message_sent()` — 消息发送后触发，适合后台任务

## 图生图（Image Editing）集成

### 方式一：Chat Completions + Vision 协议（推荐 — gpt-image-2 / Gemini / Grok 等）

**这是现代多模态生图模型的主流方式**，不要用 `/images/edits`。

图片编码为 base64 data URI，作为 multimodal content 发送：

```python
async def _edit_chat_vision(self, api_base, api_key, model, image_bytes, prompt, size, timeout):
    url = f"{api_base}/v1/chat/completions"
    img_b64 = base64.b64encode(image_bytes).decode()
    data_uri = f"data:image/png;base64,{img_b64}"

    messages = [{"role": "user", "content": [
        {"type": "image_url", "image_url": {"url": data_uri}},
        {"type": "text", "text": prompt},
    ]}]
    payload = {"model": model, "messages": messages}
    if size:
        payload["size"] = size

    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=timeout)) as session:
        async with session.post(url, headers=headers, json=payload) as resp:
            if resp.status != 200:
                return None
            data = await resp.json()
            return await self._extract_from_chat(data, session)
```

**响应提取** — Chat Completions 返回格式多样，需要多种 fallback：

```python
async def _extract_from_chat(self, data, session):
    # 1. choices[0].message.content → markdown ![xxx](url) 或 data URI 或纯 URL
    if "choices" in data and data["choices"]:
        msg = data["choices"][0].get("message", {})
        content = msg.get("content", "")
        if content:
            match = re.search(r"!\[.*?\]\((.*?)\)", content)  # markdown image
            if match:
                return await self._download_url(match.group(1), session)
            if content.startswith("data:image"):  # data URI
                return base64.b64decode(content.split(",", 1)[1])
            if content.startswith("http"):  # plain URL
                return await self._download_url(content, session)
        # 2. message.images 字段（部分 API 格式）
        for img in msg.get("images", []):
            url = img.get("url") or img.get("image_url", {}).get("url", "")
            if url:
                return await self._download_url(url, session)
    # 3. 兜底: data[0].b64_json 或 data[0].url
    if "data" in data and data["data"]:
        item = data["data"][0]
        if "b64_json" in item:
            return base64.b64decode(item["b64_json"])
        if "url" in item:
            return await self._download_url(item["url"], session)
    return None
```

### 方式二：`/v1/images/edits` + FormData（DALL-E 等传统模型）

⚠️ 仅用于 DALL-E 系列。gpt-image-2 / Gemini / Grok 请用方式一。

⚠️ **FormData 字段名是 `image`（不是 `image[]`）** — `image[]` 是 PHP 数组语法，OpenAI API 不认，会导致图片不被解析或返回原图：

```python
form.add_field("image", image_bytes, filename="input.png", content_type="image/png")
#               ^^^^^ 不是 "image[]"
```

完整示例：

```python
async def _edit_images_api(self, api_base, api_key, model, image_bytes, prompt, size, timeout):
    url = f"{api_base}/v1/images/edits"
    form = aiohttp.FormData()
    form.add_field("model", model)
    form.add_field("prompt", prompt)
    form.add_field("n", "1")
    if size:
        form.add_field("size", size)
    form.add_field("image", image_bytes, filename="input.png", content_type="image/png")
    # ⚠️ 字段名是 "image"（不是 "image[]"）

    headers = {"Authorization": f"Bearer {api_key}"}
    async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=timeout)) as session:
        async with session.post(url, headers=headers, data=form) as resp:
            data = await resp.json()
            if "data" in data and data["data"]:
                return await self._extract_image(data["data"][0], session)
    return None
```

### 统一调度：`edit_mode` 配置 + 自动检测

插件应支持 `edit_mode` 配置项，在 `auto` 模式时根据模型名自动选择。`_conf_schema.json` 中配置：

```json
"edit_mode": {
  "description": "图生图模式",
  "type": "string",
  "default": "auto",
  "options": [
    {"label": "自动识别（推荐）", "value": "auto"},
    {"label": "Chat/Vision通道", "value": "chat_vision"},
    {"label": "images/edits通道", "value": "images_edits"}
  ]
}
```

```python
def _resolve_edit_mode(self, edit_mode: str, model: str) -> str:
    if edit_mode != "auto":
        return edit_mode
    model_lower = model.lower()
    # chat_vision 类模型
    if any(kw in model_lower for kw in ["gpt-image", "gemini", "grok", "imagen", "claude"]):
        return "chat_vision"
    # images_edits 类模型
    if any(kw in model_lower for kw in ["dall-e", "dalle"]):
        return "images_edits"
    return "chat_vision"  # 默认（更通用）
```

### 统一文生图+图生图的插件模式（正确版）

⚠️ **gpt-image-2 / Gemini / Grok 等模型的文生图和图生图都走 Chat Completions API**，不要对它们使用 `/v1/images/generations`！只 DALL-E 用 `/v1/images/*`。

```python
@filter.regex(r"^画画(.+)")
async def generate_image(self, event):
    prompt = ...  # 提取prompt
    image_url = await self._get_image_url(event)  # 检查是否有图片
    img_bytes = None

    if image_url:
        yield event.plain_result("正在编辑图片...")
        img_bytes = await self._download_image(image_url)
        if not img_bytes:
            yield event.plain_result("下载图片失败")
            return
    else:
        yield event.plain_result("正在画...")

    # 统一按模式分发
    mode = self._resolve_edit_mode(edit_mode, model)
    if mode == "images_edits":
        # DALL-E 风格：文生图用 POST /v1/images/generations，图生图用 POST /v1/images/edits + FormData
        if img_bytes:
            result = await self._edit_images_api(api_base, api_key, model, img_bytes, prompt, size, timeout)
        else:
            result = await self._generate_images_api(api_base, api_key, model, prompt, size, timeout)
    else:
        # chat_vision：文生图+图生图统一走 POST /v1/chat/completions + multimodal content
        result = await self._chat_generate(api_base, api_key, model, img_bytes, prompt, size, timeout)

    if result:
        path = f"/tmp/image_gen/{int(time.time())}.png"
        with open(path, "wb") as f:
            f.write(result)
        yield event.image_result(path)
```

`_chat_generate` 签名：`image_bytes: bytes | None` — 为 None 时纯文本生图，有值时图文混合：

```python
async def _chat_generate(self, api_base, api_key, model, image_bytes, prompt, size, timeout):
    url = f"{api_base}/v1/chat/completions"
    user_content = []
    if image_bytes:
        b64 = base64.b64encode(image_bytes).decode()
        user_content.append({"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64}"}})
    user_content.append({"type": "text", "text": prompt})
    
    payload = {"model": model, "messages": [{"role": "user", "content": user_content}]}
    if size:
        payload["size"] = size
    
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    async with aiohttp.ClientSession(timeout=...) as session:
        async with session.post(url, headers=headers, json=payload) as resp:
            return await self._extract_from_chat(await resp.json(), session)
```

### 响应格式兼容

文生图和图生图返回格式相同，统一处理：

```python
async def _extract_image(self, item: dict, session: aiohttp.ClientSession) -> bytes | None:
    if "b64_json" in item:
        return base64.b64decode(item["b64_json"])
    elif "url" in item:
        async with session.get(item["url"]) as img_resp:
            if img_resp.status == 200:
                return await img_resp.read()
    return None
```

### ⚠️ 必须用 aiohttp，不要用 requests

AstrBot 是异步框架，用 `requests` 会阻塞事件循环。文生图和图生图都要用 `aiohttp`。

## 提示词优化器（副脑）模式

当用户输入简短prompt时，用LLM扩写成结构化高质量prompt，大幅提升出图质量。

**核心流程**: 用户输入 → LLM扩写(结构化JSON) → 解析/抢救 → 拼接成长prompt → 生图API

**关键设计**:
- 用轻量模型(gpt-4o-mini)做优化，重量模型(gpt-image-2)做出图，分离API配额
- JSON输出保证6个维度全覆盖: 人物外貌、服装、姿势、场景、光影、技术参数
- **反拼贴标签**: prompt前强制加 `"1girl, solo, single image, NO grid, NO collage"` 防九宫格
- **无敌抢救模式**: JSON解析失败时，按key名逐个定位手动提取value
- 风格预设通过切换style_data实现，支持自定义模式

**人设自拍公式**: `final_prompt = "{persona_base_prompt}, {optimized_action}"`
- 参考图优先级: 用户发的图 > 配置的persona_ref_image
- @llm_tool中用`event.send()`发图片，return string给LLM做文本回复

完整实现见 `references/04-prompt-optimizer-and-persona.md`

## 参考文件
详细文档位于 skill 目录的 `references/` 下，包含：
- **astrbot-plugin-pitfalls.md** — 实战踩坑记录（正则匹配、图片获取、配置读取、禁用插件、缓存问题、日志调试、QQ消息长度限制）
- 03-plugin-integration-patterns.md（Memorix/万象画卷/MiMo TTS三插件深度分析 + 整合架构参考）

模板文件位于 `templates/` 下：
- `astrbot_plugin_image_gen_example/` — 带配置的API调用插件完整示例（main.py + _conf_schema.json + metadata.yaml）
- 01-从这里开始.md（环境准备）
- 02-最小实例.md
- 03-接收消息事件.md（452行，最详细）
- 04-发送消息.md
- 05-插件配置.md
- 06-调用AI.md（553行，AI调用详解）
- 07-存储.md
- 08-文转图.md
- 09-会话控制器.md
- 10-杂项.md
- 11-发布插件.md
- 12-插件指南旧版.md（1725行，旧版完整参考）
- 13-接入平台适配器.md
- 14-HTTP-API.md
- 15-配置文件.md
- 16-图片处理与外部API调用.md（图片获取、妙达Gemini API、图片编辑）
- **17-gpt-image-api.md** — GPT-Image-2 API格式、响应差异、插件集成
- **18-gpt-image-edits-api.md** — GPT-Image 图生图 API (`/v1/images/edits`)，multipart/form-data 格式
- **astrbot-plugin-architecture.md**（memorix/万象画卷/mimo_tts三大插件深度架构分析）
- **04-prompt-optimizer-and-persona.md** — 副脑提示词优化器 + 人设自拍系统完整实现模式（风格预设、JSON解析+抢救模式、反拼贴、@llm_tool注册）
