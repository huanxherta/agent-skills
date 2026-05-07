---
name: html-rendering
description: Render styled HTML pages and capture screenshots with Playwright. Covers light/bright themes, pastel aesthetics, and terminal-inspired designs.
license: MIT
metadata:
  author: huanxherta
  version: "1.0"
  category: creative
---

# HTML Page Rendering

## Overview

Generate styled HTML pages programmatically and capture full-page screenshots using Playwright. Supports multiple visual styles including light themes, pastel aesthetics, and terminal-inspired designs.

## Prerequisites

- Python 3 with `playwright` installed
- Chromium browser available (`playwright install chromium`)

## Style Guidelines

### Color Philosophy
- **NO pure black** (`#000000`) — never use as background or primary color
- **NO dark gray** (`#1a1a1a`, `#2d2d2d`) — avoid dark neutrals
- **NO dark themes by default** — only use when explicitly requested
- **Prefer light/bright backgrounds**: warm whites, soft pastels, cream tones
- **Accent colors**: use colored accents (pink, blue, green, purple) with low saturation

### Approved Color Palettes

#### Pastel Dreamy (粉彩梦幻)
- Background: `#fdf6f9` (warm cream-pink)
- Card: `#ffffff` or `#fff5f8`
- Accent: `#e890b8` (soft rose)
- Text: `#6b5b65` (warm gray)
- Border: `rgba(232, 180, 200, 0.25)`

#### Warm Light (暖白)
- Background: `#f5f0eb` (warm beige)
- Card: `#ffffff`
- Accent: `#c878a0` (rose pink)
- Text: `#5a5560` (warm gray-purple)
- Border: `rgba(160, 140, 130, 0.15)`

#### Terminal Ghost (幽灵终端) — ONLY when requested
- Background: `#0c1525` (deep blue, NOT black)
- Card: `#0f1a2e`
- Accent: `#8fd8ff` (cold blue)
- Text: `#8aa4c8`
- Border: `rgba(143, 216, 255, 0.08)`

### Typography
- Headings: `Inter` or system sans-serif, `font-weight: 800`
- Mono elements: `JetBrains Mono` for code/status bars
- Body: `Noto Sans SC` for Chinese content

### Layout Rules
- `border-radius: 6px` maximum (hard edges preferred)
- Subtle shadows: `0 2px 12px rgba(0,0,0,0.03)` for light themes
- Card-based layout with clear separation
- Responsive: `max-width: 800px` centered on desktop

## Workflow

### Step 1: Generate HTML

Write HTML to a file in `/root/aimisi/`:

```python
html_content = """<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<title>Page Title</title>
<style>
  /* Use approved color palette */
</style>
</head>
<body>
  <!-- Content -->
</body>
</html>
"""

with open('/root/aimisi/output.html', 'w', encoding='utf-8') as f:
    f.write(html_content)
```

### Step 2: Capture Screenshot

```python
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(viewport={"width": 1280, "height": 2000})
    page.goto("file:///root/aimisi/output.html")
    page.wait_for_timeout(1500)  # Wait for fonts/animations
    page.screenshot(path="/root/aimisi/output.png", full_page=True)
    browser.close()
```

### Step 3: Send to QQ Group

```python
import websocket
import json

ws = websocket.create_connection('ws://127.0.0.1:3001')
msg = {
    'action': 'send_group_msg',
    'params': {
        'group_id': GROUP_ID,
        'message': '[CQ:image,file=file:///root/aimisi/output.png]'
    }
}
ws.send(json.dumps(msg))
ws.close()
```

## Common Patterns

### Status Bar
```html
<div class="status-bar">
  <span class="accent">SERVICE</span>
  <span class="sep">|</span>
  <span class="val">127.0.0.1:8088</span>
  <span class="sep">|</span>
  <span class="accent">ONLINE</span>
</div>
```

### Result Card
```html
<div class="result">
  <div class="result-body">
    <div class="result-index">[01]</div>
    <a href="..." class="result-title">Title</a>
    <div class="result-url">https://...</div>
    <div class="result-content">Description...</div>
    <div class="result-meta">
      <span class="engine-tag">engine</span>
      <span class="score">SCORE 1.0</span>
    </div>
  </div>
</div>
```

### Section Title with Divider
```html
<div class="section-title">
  <span class="icon">🎨</span>
  <span>Section Name</span>
  <span class="line"></span>
</div>
```

## Pitfalls

1. **Never default to dark themes** — always ask or infer from context
2. **Don't use pure black** (`#000000`) even for text — use dark grays with color tint
3. **Playwright viewport height** — set generously (2000+) for full-page capture
4. **Font loading** — wait 1500ms+ after `goto()` for Google Fonts to load
5. **File paths** — always use absolute paths with `file://` protocol
6. **Image size** — check PNG size before sending; compress if >2.5MB for QQ

## Examples

### SearXNG Results (Light Theme)
Warm beige background, rose pink accents, clean card layout.

### Prompt Guide (Pastel Theme)
Cream-pink background, soft rose accents, floating animations, colorful tags.

### API Status (Terminal Theme — only when requested)
Deep blue background, cold blue accents, monospace fonts, pulse animations.
