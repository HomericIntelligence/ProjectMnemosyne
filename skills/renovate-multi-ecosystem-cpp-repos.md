---
name: renovate-multi-ecosystem-cpp-repos
description: "Configure Renovate bot for C++20 repos using Conan, FetchContent, pixi, GitHub Actions, and Dockerfiles. Use when: (1) adding automated dependency updates to a C++ project, (2) need custom regex for CMake FetchContent GIT_TAG, (3) configuring Renovate for a multi-repo org with submodules."
category: ci-cd
date: 2026-04-01
version: "1.0.0"
user-invocable: false
verification: unverified
tags:
  - renovate
  - conan
  - pixi
  - fetchcontent
  - github-actions
  - dockerfile
  - dependency-management
---

# Renovate Bot for Multi-Ecosystem C++20 Repos

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-04-01 |
| **Objective** | Configure Renovate bot to auto-update all dependency types in C++20 repos: Conan, CMake FetchContent, pixi, GitHub Actions, Dockerfiles |
| **Outcome** | Configs created and committed; Renovate app being installed on org |
| **Verification** | unverified (Renovate app installation in progress, no PRs opened yet) |

## When to Use

- Adding automated dependency updates to a C++20 project that uses Conan + FetchContent + pixi
- Need to track CMake FetchContent `GIT_TAG` versions (no native Renovate manager — requires custom regex)
- Configuring Renovate for a multi-repo org where a meta-repo has submodules that each need their own config
- Want GitHub Actions minor/patch updates to auto-merge

## Verified Workflow

> **Note:** Verification level is `unverified` — configs committed but Renovate app installation in progress. Will be upgraded to `verified-ci` once Renovate opens its first PRs.

### Quick Reference

```bash
# Add renovate.json to repo root, then install the Renovate GitHub App
# https://github.com/apps/renovate → install for org
```

### Renovate Manager Support

| Ecosystem | Renovate Manager | Native? | Used In |
|-----------|-----------------|---------|---------|
| Conan 2.x (`conanfile.py`) | `conan` | Yes | C++ repos |
| pixi.toml (conda-forge) | `pixi` | Yes | C++ repos |
| CMake FetchContent (`GIT_TAG`) | `regex` (custom) | No | C++ repos with nats.c |
| GitHub Actions (`uses:`) | `github-actions` | Yes | All repos |
| Dockerfile (`FROM`) | `dockerfile` | Yes | C++ repos with containers |
| Python (`pyproject.toml`) | `pep621` | Yes | Python repos |

### C++20 Repo Config (`renovate.json`)

```json
{
  "$schema": "https://docs.renovatebot.com/renovate-schema.json",
  "extends": ["config:recommended"],
  "schedule": ["before 5am on Monday"],
  "customManagers": [
    {
      "customType": "regex",
      "fileMatch": ["CMakeLists\\.txt$"],
      "matchStrings": [
        "FetchContent_Declare\\([\\s\\S]*?GIT_REPOSITORY\\s+https://github\\.com/(?<depName>[^/]+/[^.]+)\\.git\\s+GIT_TAG\\s+(?<currentValue>v?[\\d.]+)"
      ],
      "datasourceTemplate": "github-tags",
      "versioningTemplate": "semver"
    }
  ],
  "packageRules": [
    {
      "matchManagers": ["conan"],
      "groupName": "C++ Conan dependencies"
    },
    {
      "matchManagers": ["pixi"],
      "groupName": "pixi build tools",
      "schedule": ["before 5am on the first day of the month"]
    },
    {
      "matchManagers": ["github-actions"],
      "groupName": "GitHub Actions",
      "automerge": true
    }
  ]
}
```

### Meta-Repo Config (Odysseus root with submodules)

```json
{
  "$schema": "https://docs.renovatebot.com/renovate-schema.json",
  "extends": ["config:recommended"],
  "schedule": ["before 5am on Monday"],
  "ignorePaths": [
    "control/**", "testing/**", "infrastructure/**",
    "provisioning/**", "research/**", "shared/**", "ci-cd/**"
  ],
  "packageRules": [
    {
      "matchManagers": ["github-actions"],
      "automerge": true
    }
  ]
}
```

The `ignorePaths` prevents Renovate from scanning submodule directories — each submodule has its own `renovate.json` and gets its own PRs in its own repo.

### Installation Steps

1. Create `renovate.json` in each repo root
2. Go to https://github.com/apps/renovate
3. Install for the GitHub org (or select specific repos)
4. Renovate auto-discovers configs and opens onboarding PRs
5. Merge the onboarding PR to activate

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Dependabot for Conan | Considered GitHub Dependabot | Dependabot has no native Conan, pixi, or FetchContent support | Renovate is the correct choice for C++ ecosystems — much broader manager coverage |
| Single config for meta-repo + submodules | Tried one renovate.json at Odysseus root to cover everything | Submodules are separate git repos — Renovate needs a config per repo to open PRs | Use `ignorePaths` in the meta-repo config, put individual configs in each submodule |

## Results & Parameters

```yaml
# Schedule
conan_and_fetchcontent: "before 5am on Monday"  # weekly
pixi_tools: "before 5am on the first day of the month"  # monthly
github_actions: "auto-merge minor/patch"

# FetchContent regex pattern (key part)
# Matches: FetchContent_Declare(\n  nats_c\n  GIT_REPOSITORY https://github.com/nats-io/nats.c.git\n  GIT_TAG v3.9.1)
regex: "FetchContent_Declare\\([\\s\\S]*?GIT_REPOSITORY\\s+https://github\\.com/(?<depName>[^/]+/[^.]+)\\.git\\s+GIT_TAG\\s+(?<currentValue>v?[\\d.]+)"
datasource: "github-tags"
versioning: "semver"

# Files created
repos_configured:
  - Odysseus (root — ignores submodules)
  - control/ProjectAgamemnon
  - control/ProjectNestor
  - testing/ProjectCharybdis
```

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| Odysseus | Meta-repo config | ignorePaths for submodules, GH Actions auto-merge |
| ProjectAgamemnon | C++20 repo config | Conan + FetchContent regex + pixi + GH Actions + Dockerfile |
| ProjectNestor | C++20 repo config | Same as Agamemnon |
| ProjectCharybdis | C++20 repo config | Same as Agamemnon (fewer deps currently) |
