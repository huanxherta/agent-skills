---
name: github-pr-workflow
description: Full pull request lifecycle — create branches, commit changes, open PRs, monitor CI, auto-fix failures, and merge. Works with gh CLI or git + GitHub REST API.
license: MIT
compatibility: Requires git and optionally gh CLI
metadata:
  author: huanxherta
  version: "1.0"
  category: github
---

# GitHub PR Workflow

Full pull request lifecycle from branch to merge.

## Prerequisites

- `gh` CLI authenticated, or git with HTTPS token
- Repository cloned locally

## Workflow Steps

### 1. Create branch

```bash
git checkout -b feature/my-feature
```

### 2. Make changes and commit

```bash
git add -A
git commit -m "feat: add my feature"
```

### 3. Push and create PR

```bash
git push origin feature/my-feature
gh pr create --title "feat: add my feature" --body "Description here"
```

### 4. Monitor CI

```bash
gh pr checks --watch
```

### 5. Merge

```bash
gh pr merge --squash --auto
```

## Fallback (without gh CLI)

```bash
# Create PR via API
curl -X POST -H "Authorization: token $GITHUB_TOKEN" \
  https://api.github.com/repos/OWNER/REPO/pulls \
  -d '{"title":"feat: my feature","head":"feature/my-feature","base":"main"}'
```

## Pitfalls

- Always pull latest before pushing: `git pull --rebase origin main`
- Use `--auto` flag for merge to wait for CI
- Squash merge keeps main branch clean
