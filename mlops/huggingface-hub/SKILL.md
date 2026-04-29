---
name: huggingface-hub
description: Hugging Face Hub CLI (hf) — search, download, upload models/datasets, manage Spaces and repos. Use when interacting with HuggingFace Hub from the terminal.
license: Apache-2.0
compatibility: Requires hf CLI installed (curl -LsSf https://hf.co/cli/install.sh | bash -s)
metadata:
  author: huanxherta
  version: "1.0"
  category: mlops
---

# Hugging Face CLI (hf) Reference

The `hf` command is the modern CLI for interacting with Hugging Face Hub.

## Quick Start

```bash
# Install
curl -LsSf https://hf.co/cli/install.sh | bash -s

# Auth
export HF_TOKEN=hf_xxxxx
hf auth login --token $HF_TOKEN

# Verify
hf auth whoami
```

## Core Commands

### Repository Management

```bash
hf repos create user/repo --type model
hf repos delete user/repo --type model
hf repos move old-name new-name
```

### Upload / Download

```bash
hf upload user/repo ./local-dir
hf download user/repo
```

### Spaces

```bash
hf repos create user/my-space --type space --space-sdk docker
```

### Models & Datasets

```bash
hf models list --search "llama"
hf datasets list --search "squad"
```

## Pitfalls

- Use `hf` not `huggingface-cli` (deprecated)
- `--token` flag needs the token as the next argument (not `=value`)
- For large uploads use `hf upload-large-folder` for resumable transfers
- HF_TOKEN env var takes precedence over saved token
