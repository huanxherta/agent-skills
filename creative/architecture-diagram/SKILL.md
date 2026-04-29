---
name: architecture-diagram
description: Generate dark-themed SVG diagrams of software systems as standalone HTML files. Semantic component colors, grid background, JetBrains Mono font. Use for architecture diagrams, cloud topology, microservice maps.
license: MIT
metadata:
  author: huanxherta
  version: "1.0"
  category: creative
---

# Architecture Diagram Generator

Generate dark-themed SVG architecture diagrams as standalone HTML files.

## Color Coding

| Color | Component |
|-------|-----------|
| Cyan | Frontend |
| Emerald | Backend |
| Violet | Database |
| Amber | Cloud/AWS |
| Rose | Security |
| Orange | Message Bus |

## Usage

1. Describe the system architecture
2. Agent generates HTML with inline SVG
3. Render in browser or screenshot

## Template Structure

```html
<!DOCTYPE html>
<html>
<head>
  <style>
    body { background: #0f172a; font-family: 'JetBrains Mono', monospace; }
    /* Grid background */
    /* Semantic colors for components */
  </style>
</head>
<body>
  <!-- SVG diagram here -->
</body>
</html>
```

## Design Rules

- Dark background (#0f172a)
- Grid pattern for alignment
- Rounded rectangles for components
- Arrows for data flow
- Color-coded by role
- 800px max width for mobile readability
