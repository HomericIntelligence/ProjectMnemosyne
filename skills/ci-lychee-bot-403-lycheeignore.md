---
name: ci-lychee-bot-403-lycheeignore
description: "Fix lychee link-check CI failures caused by bot-blocking 403 responses or intermittent
  connection resets from external sites. Use when: (1) lychee link-check CI job fails with HTTP 403
  on claude.ai or other Anthropic URLs that block automated bots, (2) contributor-covenant.org or
  similar community sites return connection reset (os error 104) intermittently causing flaky CI,
  (3) a site returns a non-2xx response to lychee's user-agent that is clearly valid when visited
  in a browser."
category: ci-cd
date: 2026-05-03
version: "1.0.0"
user-invocable: false
verification: verified-ci
tags:
  - lychee
  - link-check
  - ci
  - "403"
  - lycheeignore
  - bot-protection
---

# CI: Lychee Link-Check Bot 403 and Connection Reset Fix

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-05-03 |
| **Objective** | Fix lychee link-check CI failures caused by HTTP 403 responses from bot-protected URLs and intermittent connection resets from external community sites |
| **Outcome** | Successful — link-check CI job passed after adding patterns to `.lycheeignore` |
| **Verification** | verified-ci (PR #5347, ProjectOdyssey) |

## When to Use

- `link-check` CI job fails with HTTP 403 on `claude.ai`, `platform.claude.com`, or `code.claude.com`
- `link-check` CI job fails with `os error 104` (connection reset) on `contributor-covenant.org`
  or similar external community/standards sites
- Lychee reports a URL as broken that loads correctly in a browser (bot-protection false-positive)
- Adding new Anthropic documentation links to markdown files causes CI failures
- The link-check is blocking a PR merge and the URLs are visually verified as valid

## Verified Workflow

### Quick Reference

```bash
# Add to .lycheeignore (create file if it doesn't exist):
cat >> .lycheeignore << 'EOF'

# Ignore Claude/Anthropic URLs that return 403 to bots (valid URLs, bot-protection blocks lychee)
claude\.ai
platform\.claude\.com
code\.claude\.com

# Ignore external sites that may be intermittently unavailable or return connection resets
contributor-covenant\.org
EOF

# Verify the file has correct regex patterns
cat .lycheeignore

# Test locally (if lychee is installed)
lychee --config .lychee.toml "**/*.md"
```

### Detailed Steps

1. **Identify the failing URLs** — check the CI log for lychee output:

   ```text
   [ERROR] https://claude.ai/code — Status 403 (Forbidden)
   [ERROR] https://contributor-covenant.org/... — Connection reset (os error 104)
   ```

2. **Classify each failure**:

   | Failure Type | URL Pattern | Root Cause | Action |
   |-------------|-------------|------------|--------|
   | HTTP 403 | `claude.ai`, `platform.claude.com`, `code.claude.com` | Anthropic URLs return 403 to automated bots (lychee's user-agent) | Add to `.lycheeignore` |
   | Connection reset (os error 104) | `contributor-covenant.org` | Intermittent network/server issue; site is valid but unreliable from CI | Add to `.lycheeignore` |

3. **Add patterns to `.lycheeignore`**:

   ```text
   # Ignore Claude/Anthropic URLs that return 403 to bots
   # (valid URLs — Anthropic's bot-protection blocks lychee's user-agent)
   claude\.ai
   platform\.claude\.com
   code\.claude\.com

   # Ignore external sites that may be intermittently unavailable
   # contributor-covenant.org returns "Connection reset by peer" (os error 104) in CI
   contributor-covenant\.org
   ```

   Notes on `.lycheeignore` format:
   - Patterns are **regular expressions** (not glob patterns)
   - Escape literal dots with `\.`
   - A pattern matches any URL containing the pattern substring
   - Comments start with `#`
   - File must exist at the project root (same directory as `.lychee.toml` or where lychee is invoked)

4. **Verify the fix** — commit and push to trigger CI, or run locally:

   ```bash
   # Run lychee locally (if installed via pixi/brew/cargo)
   lychee --config .lychee.toml "**/*.md" --exclude-path .pixi

   # Or via pixi (if lychee is in pixi.toml)
   pixi run lychee "**/*.md"
   ```

5. **Commit**:

   ```bash
   git add .lycheeignore
   git commit -m "fix(ci): add claude.ai and contributor-covenant.org to .lycheeignore

   lychee treats HTTP 403 as a hard error. claude.ai returns 403 to bots.
   contributor-covenant.org intermittently resets connections (os error 104).
   Both patterns caused link-check CI failures despite the URLs being valid."
   ```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| `--exclude-all-private` lychee flag | Tried excluding private/localhost URLs | Does not affect external URLs returning 403 | `--exclude-all-private` only skips private IP ranges and localhost, not bot-blocked external URLs |
| Waiting for intermittent failures to clear | Assumed connection resets were transient and would stop | `contributor-covenant.org` resets consistently enough in CI to block every run | Add to `.lycheeignore`; don't rely on intermittent availability of external CI gates |
| `--accept 403` lychee config option | Tried adding `accept = [403]` to `.lychee.toml` | Accepts 403 globally — too broad, would hide real broken links | Prefer `.lycheeignore` for targeted URL exclusion; reserve `--accept` for status codes you want to globally ignore |

## Results & Parameters

### `.lycheeignore` Entries for Common CI Failures

```text
# Ignore Claude/Anthropic URLs that return 403 to bots (valid URLs, bot-protection blocks lychee)
claude\.ai
platform\.claude\.com
code\.claude\.com

# Ignore external sites that may be intermittently unavailable
contributor-covenant\.org
```

### Pattern Format Reference

| Pattern | Matches | Notes |
|---------|---------|-------|
| `claude\.ai` | Any URL containing `claude.ai` | Escaped dot = literal dot |
| `platform\.claude\.com` | `https://platform.claude.com/...` | Subdomain patterns |
| `contributor-covenant\.org` | Any `contributor-covenant.org` URL | Handles all paths under domain |

### Lychee Configuration (`.lychee.toml`)

For the `.lycheeignore` file to be picked up automatically, ensure your `.lychee.toml` references it
(this is the default behavior — lychee reads `.lycheeignore` automatically):

```toml
# .lychee.toml
[params]
exclude_path = [".pixi", "node_modules", "target"]
# .lycheeignore is read automatically — no explicit config needed
```

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectOdyssey | 2026-05-03 — PR #5347/#5348, CI fix session | `claude.ai` (403) and `contributor-covenant.org` (os error 104) caused link-check failures; both fixed by `.lycheeignore` entries |

## References

- [lychee — .lycheeignore documentation](https://lychee.cli.rs/usage/excluding-links/)
- [lychee GitHub](https://github.com/lycheeverse/lychee)
