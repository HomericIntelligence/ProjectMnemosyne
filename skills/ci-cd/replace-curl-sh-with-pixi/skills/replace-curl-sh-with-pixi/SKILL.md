---
name: replace-curl-sh-with-pixi
description: "Replace unverifiable curl|sh installer patterns in CI with the setup-pixi composite action to eliminate supply-chain risk. Use when: a workflow installs a runtime or CLI tool via curl -s <url> | sh without hash verification."
category: ci-cd
date: 2026-03-15
user-invocable: false
---

## Overview

| Field | Value |
|-------|-------|
| **Goal** | Replace `curl -s <url> \| sh` installer steps with `uses: ./.github/actions/setup-pixi` |
| **Context** | Supply-chain hardening — live-redirect URLs cannot be SHA256-verified |
| **Trigger** | Workflow installs a runtime (Mojo, Modular CLI, etc.) via piped curl without a hash check |
| **Output** | Modified workflow YAML; fewer steps, no unverifiable remote code execution |

## When to Use

1. A GitHub Actions workflow contains `curl -s https://<some-url> | sh -` to install a runtime
2. A security audit issue (follow-up from SHA256 hardening) asks to check all workflows for
   unverified binary downloads beyond simple `wget` patterns
3. The tool being installed is already provided by the project's Pixi environment (e.g., Mojo)
4. The `setup-pixi` composite action exists at `.github/actions/setup-pixi/action.yml`

## Verified Workflow

### Quick Reference

| Pattern to replace | Safe replacement |
|--------------------|-----------------|
| `curl -s <url> \| sh -` + `modular install mojo` | `uses: ./.github/actions/setup-pixi` |
| Two steps (install CLI + install tool) | One step (composite action) |

### Step 1: Audit all workflows for curl-pipe-sh patterns

```bash
grep -rn "curl.*|.*sh" .github/workflows/*.yml
grep -rn "wget.*\| sh\|curl.*\| bash" .github/workflows/*.yml
```

Identify workflows that use a live-URL installer (no pinned hash, no version in URL filename).

### Step 2: Verify the setup-pixi composite action exists

```bash
ls .github/actions/setup-pixi/action.yml
```

If it does not exist, create it first (see `workflow-deduplication-pixi-composite-action` skill).

### Step 3: Check what the curl-sh step is actually installing

Read the surrounding steps — if the tool (e.g., Mojo) is already available via Pixi, the
entire install block can be replaced with `setup-pixi`.

```bash
grep -A5 "curl.*modular\|modular install" .github/workflows/<file>.yml
```

### Step 4: Replace with composite action

Remove the `curl | sh` step(s) and replace with:

```yaml
- name: Set up Pixi (provides Mojo)
  uses: ./.github/actions/setup-pixi
```

Note: `continue-on-error: true` is NOT needed — `setup-pixi` is reliable. Remove it.

### Step 5: Verify no other curl-pipe-sh patterns remain

```bash
grep -rn "curl.*|.*sh\|wget.*|.*sh" .github/workflows/*.yml
```

Expected: empty output for live-URL installer patterns (SHA256-verified wget downloads are fine).

### Step 6: Commit and push

```bash
git add .github/workflows/<file>.yml
git commit -m "fix(ci): replace curl|sh installer with setup-pixi composite action"
gh pr create --title "fix(ci): ..." --body "Closes #NNNN"
gh pr merge --auto --rebase
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Searching for `wget` patterns only | Used `grep -rn "wget" .github/workflows/` to find unverified downloads | Missed the `curl \| sh` installer in `validate-configs.yml` — it uses `curl`, not `wget` | Always grep for BOTH `wget` and `curl` with pipe patterns when auditing CI |
| Keeping `continue-on-error: true` | Left it on the replacement step | Unnecessary — the entire point is that `setup-pixi` is stable and pinned; `continue-on-error` would hide failures | Remove `continue-on-error` when replacing a curl-sh step with `setup-pixi` |

## Results & Parameters

**Audit command (comprehensive)**:

```bash
# Find any curl/wget piped directly to sh or bash
grep -rn "curl\|wget" .github/workflows/*.yml | grep -v "sha256sum" | grep "|.*sh\b\|bash\b"
```

**Replacement pattern**:

```yaml
# BEFORE (two steps, unverifiable supply-chain risk):
- name: Install Modular CLI
  run: |
    curl -s https://get.modular.com | sh -
    modular auth ${{ secrets.MODULAR_AUTH_TOKEN }}
  continue-on-error: true

- name: Install Mojo
  run: |
    modular install mojo
  continue-on-error: true

# AFTER (one step, pinned via Pixi lockfile):
- name: Set up Pixi (provides Mojo)
  uses: ./.github/actions/setup-pixi
```

**Key distinction from `workflow-binary-sha256-verification` skill**:
- SHA256 verification skill: adds a hash check for a pinned binary download (wget + sha256sum)
- This skill: removes the download entirely by using the Pixi composite action

**When `setup-pixi` is not applicable**:
- The tool is not in the Pixi environment (e.g., a third-party CLI not managed by Pixi)
- In that case, pin the install script to a specific version URL and add `sha256sum --check`
  (see `workflow-binary-sha256-verification` skill)

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectOdyssey | Issue #3941 — CI hardening follow-up from #3316 | [notes.md](../../references/notes.md) |
