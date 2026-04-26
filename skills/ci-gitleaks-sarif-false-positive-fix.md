---
name: ci-gitleaks-sarif-false-positive-fix
description: 'Fix gitleaks SARIF false-positive detection causing security-report
  required check to always fail, blocking PR auto-merges. Use when: (1) security-report
  required check fails on every run even with no real secrets, (2) gitleaks SARIF
  check uses grep with \s instead of jq, (3) swarm session is blocked because
  security-report is a required status check that never passes.'
category: ci-cd
date: 2026-04-25
version: 1.0.0
user-invocable: false
---
# CI Gitleaks SARIF False-Positive Fix

## Overview

| Item | Details |
|------|---------|
| Date | 2026-04-25 |
| Objective | Fix gitleaks SARIF parsing and security-report aggregator so required check passes |
| Outcome | verified-local — fix committed to ProjectKeystone PR #451; upstream gitleaks job passed (0 secrets with allowlist) |

Addresses two bugs that cause `security-report` (a required PR status check) to always fail,
blocking all PR auto-merges. The root causes are a fragile POSIX grep regex and a naive
failure-detection gate that catches false-positive symbols.

**Phase 0 rule**: Before running any myrmidon swarm, verify `security-report` passes on main.
If it is a required check and it fails, fix it first — a broken required check blocks every PR
auto-merge regardless of actual security findings.

## When to Use

- `security-report` is a required status check that fails on every PR and every push to main
- Gitleaks SARIF check step uses `grep -q '"results":\s*\[\]'` — this is always the bug
- Final check step uses `grep -q "❌" report.md` — this catches false-positive symbols
- Starting a myrmidon swarm on a repo where `security-report` is required: verify it passes first
- Any repo using a `security-report` aggregator job that reads a `report.md` with ❌/✅ symbols
- After adding documentation, k8s YAML, or skill files that contain placeholder credentials

## Verified Workflow

### Quick Reference

```bash
# Step 1: Confirm Bug 1 — fragile POSIX grep (never matches even for empty results)
grep -n 'grep.*results.*\\\s' .github/workflows/security-scan.yml

# Step 2: Fix Bug 1 — replace with jq-based SARIF parsing
# BEFORE (broken — \s is literal in POSIX grep, never matches):
grep -q '"results":\s*\[\]' results.sarif

# AFTER (correct — jq parses the JSON structure):
jq '[.runs[].results[]] | length == 0' results.sarif | grep -q true

# Step 3: Fix Bug 2 — replace naive ❌ gate with specific line-prefix matching
# BEFORE (catches ANY ❌ in the report including false-positive from Bug 1):
grep -q "❌" report.md

# AFTER (only fails on real security findings with specific prefixes):
! grep -qE "^- ❌ Secret Scanning:|^- ❌ Docker Image Scanning:" report.md

# Step 4: Check if gitleaks actually found results (after fixing Bug 1)
# If jq reports length > 0, gitleaks found real-looking secrets — likely false positives
# in docs/k8s/example files → add .gitleaks.toml allowlist (see Results & Parameters)

# Step 5: Verify fix locally
jq '[.runs[].results[]] | length' results.sarif   # should be 0 after allowlist
```

### Full Repair Sequence

1. **Audit the workflow**: Find the SARIF check step and the final gate step.

```bash
grep -n 'grep.*results\|grep.*❌\|security-report\|report.md' \
  .github/workflows/security-scan.yml
```

2. **Fix the SARIF parser** (Bug 1): Replace POSIX grep with `jq`.

```yaml
# In the "Check gitleaks results" step:
- name: Check gitleaks results
  run: |
    if [ -f results.sarif ]; then
      if jq '[.runs[].results[]] | length == 0' results.sarif | grep -q true; then
        echo "- ✅ Secret Scanning: No secrets detected" >> report.md
      else
        COUNT=$(jq '[.runs[].results[]] | length' results.sarif)
        echo "- ❌ Secret Scanning: ${COUNT} secret(s) found" >> report.md
      fi
    else
      echo "- ⚠️ Secret Scanning: SARIF file not found" >> report.md
    fi
```

3. **Fix the failure gate** (Bug 2): Replace `grep -q "❌"` with specific prefix matching.

```yaml
# In the final "security-report" or "Check results" step:
- name: Check for failures
  run: |
    if grep -qE "^- ❌ Secret Scanning:|^- ❌ Docker Image Scanning:" report.md; then
      echo "Security scan found critical failures"
      cat report.md
      exit 1
    fi
    echo "All security checks passed"
    cat report.md
```

4. **Add `.gitleaks.toml` allowlist** if gitleaks finds false positives after Bug 1 is fixed
   (see Results & Parameters for copy-paste template).

5. **Commit and push**, confirm `security-report` passes in CI.

### Verification Checklist

```bash
# 1. No POSIX \s in SARIF check
grep -c 'grep.*\\s.*sarif' .github/workflows/security-scan.yml
# → should be 0

# 2. jq is used for SARIF parsing
grep -c 'jq.*runs.*results' .github/workflows/security-scan.yml
# → should be >= 1

# 3. Final gate does not use bare ❌ grep
grep -c 'grep.*"❌"' .github/workflows/security-scan.yml
# → should be 0

# 4. .gitleaks.toml exists if docs/k8s dirs are present
[ -f .gitleaks.toml ] && echo "OK" || echo "MISSING — add allowlist"
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|---------------|---------------|----------------|
| 1 | `grep -q '"results":\s*\[\]' results.sarif` | POSIX `grep` treats `\s` as a literal backslash-s, not whitespace; never matches even when results array is empty | Always use `jq` for JSON/SARIF parsing; never use POSIX grep for structured data |
| 2 | `grep -q "❌" report.md` as the CI failure gate | Any ❌ symbol anywhere in the report triggers failure, including the false-positive status written by Bug 1; creates a self-reinforcing failure loop | Use specific line-prefix patterns (`^- ❌ Secret Scanning:`) to target real failures only |
| 3 | Fixing Bug 1 alone without .gitleaks.toml | After fixing the parser, gitleaks correctly reported 5 findings — all in docs/k8s/example files with placeholder credentials | Fix the parser first (to see real findings), then add the allowlist; do both in the same PR |

## Results & Parameters

### Copy-Paste `.gitleaks.toml` Template

Use this as a starting point for any HomericIntelligence repo with k8s YAML and documentation:

```toml
title = "ProjectKeystone Gitleaks Configuration"

[extend]
useDefault = true

[[allowlists]]
description = "Documentation and example files containing placeholder credentials"
paths = [
  "k8s/metrics-security.yaml",
  "k8s/secrets.yaml",
  "docs/KUBERNETES_DEPLOYMENT.md",
  "docs/METRICS_SECURITY.md",
  ".claude/skills/quality-security-scan/SKILL.md",
]
```

**Extend the paths list** for your repo's actual false-positive files. Common candidates:

| File Pattern | Why Gitleaks Flags It |
|---|---|
| `k8s/secrets.yaml` | Base64 TLS cert placeholder or `REPLACE_ME` credential |
| `k8s/*-security.yaml` | `prometheus:PASSWORD` in curl example metrics endpoint |
| `docs/KUBERNETES_DEPLOYMENT.md` | `-----BEGIN PRIVATE KEY-----` comment placeholder |
| `docs/METRICS_SECURITY.md` | Curl example with `Authorization: Bearer <token>` |
| `.claude/skills/*/SKILL.md` | Example API keys like `sk_live_1234567890` |

### Common False-Positive Patterns Gitleaks Detects

```
prometheus:PASSWORD     → in docs curl examples showing metric endpoints
-----BEGIN PRIVATE KEY-----  → in k8s YAML comments as placeholder text
base64-encoded string   → TLS cert placeholders in k8s/secrets.yaml
sk_live_1234567890      → example Stripe key in documentation/skill files
```

### jq Command Reference

```bash
# Check if SARIF has zero results
jq '[.runs[].results[]] | length == 0' results.sarif

# Count findings
jq '[.runs[].results[]] | length' results.sarif

# List finding rule IDs
jq '[.runs[].results[].ruleId] | unique' results.sarif

# List finding locations (files)
jq '[.runs[].results[].locations[].physicalLocation.artifactLocation.uri] | unique' results.sarif
```

### Key Lessons Summary

1. Never use POSIX `grep` for patterns with `\s` — use `grep -E` or `jq` for structured data.
2. Always use `jq` to parse SARIF/JSON; grepping for JSON structure is fragile.
3. Gitleaks flags placeholder credentials in k8s YAML, documentation curl examples, and any file
   with `BEGIN PRIVATE KEY` or known secret patterns — add `.gitleaks.toml` allowlist upfront
   for `docs/` and `k8s/` directories in new repos.
4. When `security-report` is a required check, a false-positive blocker prevents ALL PR
   auto-merges — fix it as Phase 0 before any swarm.
5. Two-stage fix: (a) fix SARIF parsing with `jq`, (b) add `.gitleaks.toml` path allowlist
   for known false-positive files. Both changes belong in the same PR.
