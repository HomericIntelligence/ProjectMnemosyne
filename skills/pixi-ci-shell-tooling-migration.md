---
name: pixi-ci-shell-tooling-migration
description: "Migrate GitHub Actions CI for shell-only repos from ad-hoc curl tool installs to pixi-based tooling. Use when: (1) CI installs yq/shellcheck/bats via curl onto ubuntu-latest, (2) tests fail with yq parse errors on valid v4 expressions, (3) PATH shadowing causes tool version mismatches in bats subshells, (4) adding pixi to a repo that has no Python/Mojo (pure shell GitOps)."
category: ci-cd
date: 2026-04-23
version: "1.0.0"
user-invocable: false
verification: verified-local
tags:
  - pixi
  - yq
  - go-yq
  - shellcheck
  - bats
  - github-actions
  - shell
  - gitops
  - path-shadowing
---

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-04-23 |
| **Objective** | Migrate a shell-only GitOps repo (Myrmidons) from ad-hoc `curl` tool installs on ubuntu-latest to pixi-managed tooling, eliminating PATH shadowing and silent version mismatches |
| **Outcome** | Operational — 51/51 unit tests pass, 44/44 harness tests pass, shellcheck clean |
| **Verification** | verified-local (CI validation pending first push) |
| **Project** | HomericIntelligence/Myrmidons — shell-only GitOps, no Python/Mojo |

## When to Use

- A GitHub Actions CI workflow installs `yq`, `shellcheck`, or `bats` via ad-hoc `curl` onto an ubuntu-latest runner
- Tests fail with yq parse errors like `invalid input text 'tostring)'` despite the expression being valid yq v4
- A bats test resolves a different tool binary than the runner's main shell (subshell PATH ordering differs)
- Adding pixi to a repo that contains only shell scripts (no Python, no Mojo) — pure GitOps tooling
- Migrating from `[project]` to `[workspace]` block in `pixi.toml` (pixi 0.63+ deprecation)
- Wanting a composite action pattern for CI tool setup matching the ProjectScylla/Odyssey standard

## Verified Workflow

### Quick Reference

```toml
# pixi.toml — shell-only repo
[workspace]
name = "myrmidons"
channels = ["conda-forge"]
platforms = ["linux-64"]

[dependencies]
go-yq = ">=4.44"          # CRITICAL: NOT "yq" — that installs python-yq v3
shellcheck = ">=0.10"
jq = ">=1.7"
curl = ">=8"
bats-core = ">=1.11"

[feature.lint.dependencies]
shellcheck = ">=0.10"
yamllint = ">=1.35"

[feature.lint.tasks]
lint-shell = "shellcheck scripts/*.sh scripts/**/*.sh"
lint-yaml = "yamllint agents/ fleets/"

[tasks]
test-unit = "bats tests/unit/"
test-schema = "bats tests/schema/"
test-integration = "bats tests/integration/ || true"
```

```yaml
# .github/actions/setup-pixi/action.yml — composite action
name: Set Up Pixi Environment
description: Install Pixi and restore the cached Myrmidons tool environment.

inputs:
  environment:
    description: Pixi environment to activate
    required: false
    default: default

runs:
  using: composite
  steps:
    - name: Set up Pixi
      uses: prefix-dev/setup-pixi@ba3bb36eb2066252b2363392b7739741bb777659  # v0.8.1
      with:
        pixi-version: v0.39.5
        cache: true
```

### Detailed Steps

#### Step 1: Add `pixi.toml` to the repo root

Use `[workspace]` (not `[project]`) for pixi 0.63+. The critical dependency name:

```toml
[workspace]
name = "myrepo"
channels = ["conda-forge"]
platforms = ["linux-64"]

[dependencies]
go-yq = ">=4.44"   # Mikefarah's yq v4 — NOT "yq" which is python-yq v3
bats-core = ">=1.11"
shellcheck = ">=0.10"
jq = ">=1.7"
curl = ">=8"
```

Run `pixi install` to generate `pixi.lock` and commit both files.

#### Step 2: Create the composite action

```bash
mkdir -p .github/actions/setup-pixi
```

Create `.github/actions/setup-pixi/action.yml` with the content from Quick Reference above. Pin `prefix-dev/setup-pixi` to a commit SHA, not just a tag.

#### Step 3: Migrate CI workflow jobs

Replace all ad-hoc `curl` install steps:

```yaml
# BEFORE (broken — PATH shadowing, version unpredictable):
- name: Install yq
  run: |
    curl -L https://github.com/mikefarah/yq/releases/download/v4.44.3/yq_linux_amd64 \
      -o /usr/local/bin/yq
    chmod +x /usr/local/bin/yq

- name: Install shellcheck
  run: sudo apt-get install -y shellcheck

- name: Install bats
  run: |
    git clone --depth 1 https://github.com/bats-core/bats-core.git /tmp/bats
    sudo /tmp/bats/install.sh /usr/local

# AFTER (pixi-managed, deterministic):
- name: Set up Pixi
  uses: ./.github/actions/setup-pixi

- name: Run tests
  run: pixi run test-unit
```

#### Step 4: Define tasks in pixi.toml

Replace `find tests -name '*.sh' | while` discovery patterns with explicit task definitions:

```toml
[tasks]
test-unit    = "bats tests/unit/ --formatter tap"
test-schema  = "bats tests/schema/ --formatter tap"

[feature.lint.tasks]
lint-shell   = "shellcheck scripts/*.sh"
lint-yaml    = "yamllint -c .yamllint agents/ fleets/"
```

This prevents bats from discovering standalone harness scripts that fail in CI context.

#### Step 5: Verify locally

```bash
pixi run test-unit        # Should pass all unit tests
pixi run test-schema      # Should pass schema tests
pixi run --environment lint lint-shell   # Should be clean
```

#### Step 6: Commit pixi.lock

```bash
git add pixi.toml pixi.lock .github/actions/setup-pixi/action.yml
git commit -m "feat: migrate CI tooling to pixi (go-yq v4, bats, shellcheck)"
```

`pixi.lock` must be committed — it pins exact tool versions for reproducible CI.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| `curl -o /usr/local/bin/yq` without sudo on ubuntu-latest | Downloaded mikefarah yq v4 to `/usr/local/bin/yq` | Appeared to succeed but ubuntu-latest's `/usr/bin/yq` (python-yq v3) took precedence in bats subshells; tests failed with `invalid input text 'tostring)'` | PATH ordering in subshells can differ from the runner's main shell — always verify with `which yq && yq --version` in the actual bats test context |
| conda-forge package named `yq` | Added `yq` to `[dependencies]` in pixi.toml | Installs python-yq v3 (a jq Python wrapper), not Mikefarah's yq v4; expressions like `\| tostring` and `to_entries[]` are rejected | The conda-forge package `yq` is python-yq v3. Mikefarah's go-based yq v4 ships as **`go-yq`** on conda-forge |
| `find tests -name '*.bats' \| while IFS='' read -r script` in CI | Discovered and ran all test scripts dynamically | Picked up standalone harness scripts (designed for manual use) that fail in CI with exit 127 due to missing environment setup | Use explicit `pixi run test-unit`, `pixi run test-schema` tasks instead of glob discovery; keeps job scopes clean |
| `[project]` block in pixi.toml | Used `[project]` as the top-level block | pixi 0.63+ deprecates `[project]` in favor of `[workspace]`; generates deprecation warnings that pollute CI logs | Use `[workspace]` for all new pixi.toml files |
| `sudo apt-get install shellcheck` on ubuntu-latest | Installed shellcheck via apt | apt ships an older shellcheck version (0.7.x vs 0.10.x); misses SC2317 and other newer checks | Use pixi to pin shellcheck version; conda-forge has current versions |
| `cache: true` on `prefix-dev/setup-pixi` inline | Set `cache: true` directly on the setup-pixi action step | HTTP 400 / `Saved cache with ID -1` failures in some runner environments | Use `actions/cache@v4` explicitly with `.pixi` + `~/.cache/rattler/cache` paths, or rely on the composite action to manage it |

## Results & Parameters

### conda-forge Package Name Map (Critical)

| Tool | conda-forge Package | Notes |
| ------ | --------------------- | ------- |
| Mikefarah yq v4 | **`go-yq`** | Supports `\| tostring`, `to_entries[]`, all v4 expressions |
| python-yq v3 | `yq` | jq wrapper; rejects v4 expressions; this is what ubuntu-latest ships |
| shellcheck | `shellcheck` | Current version (0.10.x) |
| bats | `bats-core` | Full test framework |
| jq | `jq` | JSON processor |

### Composite Action Template

`.github/actions/setup-pixi/action.yml`:

```yaml
name: Set Up Pixi Environment
description: Install Pixi and restore the cached environment.

inputs:
  environment:
    description: Pixi environment to activate
    required: false
    default: default

runs:
  using: composite
  steps:
    - name: Set up Pixi
      uses: prefix-dev/setup-pixi@ba3bb36eb2066252b2363392b7739741bb777659  # v0.8.1
      with:
        pixi-version: v0.39.5
        cache: true
```

### Workflow Pattern for Shell-Only Repo

```yaml
name: CI

on:
  pull_request:
  push:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    timeout-minutes: 15
    steps:
      - uses: actions/checkout@11bd71901bbe5b1630ceea73d27597364c9af683  # v4.2.2

      - name: Set up Pixi
        uses: ./.github/actions/setup-pixi

      - name: Run unit tests
        run: pixi run test-unit

      - name: Run schema tests
        run: pixi run test-schema

  lint:
    runs-on: ubuntu-latest
    timeout-minutes: 10
    steps:
      - uses: actions/checkout@11bd71901bbe5b1630ceea73d27597364c9af683  # v4.2.2

      - name: Set up Pixi
        uses: ./.github/actions/setup-pixi

      - name: Lint shell scripts
        run: pixi run --environment lint lint-shell

      - name: Lint YAML
        run: pixi run --environment lint lint-yaml
```

### Verification Commands

```bash
# Confirm correct yq version is active in pixi environment
pixi run yq --version
# Expected: yq (https://github.com/mikefarah/yq/) version v4.x.x

# Confirm yq v4 expressions work
pixi run yq eval '.spec | to_entries[] | .key + "=" + (.value | tostring)' agents/hermes/example.yaml

# Run full test suite
pixi run test-unit && pixi run test-schema

# Run lint
pixi run --environment lint lint-shell
```

### PATH Shadowing Diagnostic

To confirm the bug is PATH shadowing (not a script error):

```bash
# In the bats test, add this temporary debug:
@test "debug yq version" {
  run which yq
  echo "yq path: $output"
  run yq --version
  echo "yq version: $output"
}
```

If `which yq` returns `/usr/bin/yq` instead of `/usr/local/bin/yq` or the pixi path, PATH shadowing is confirmed.

## Verified On

| Project | Context | Details |
| --------- | --------- | --------- |
| Myrmidons (HomericIntelligence/Myrmidons) | CI broken on main — ubuntu-latest PATH shadowing bug with yq | 51/51 unit tests, 44/44 harness tests, shellcheck clean after pixi migration |
