---
name: github-actions-mojo
description: "GitHub Actions CI setup for Mojo projects with pixi"
category: ci-cd
date: 2025-12-28
---

# GitHub Actions for Mojo

Configure GitHub Actions CI/CD for Mojo projects using pixi.

## Overview

| Item | Details |
|------|---------|
| Date | 2025-12-28 |
| Objective | Set up reliable CI for Mojo codebase |
| Outcome | Success |

## When to Use

- Setting up CI/CD for a new Mojo project
- Migrating from manual testing to automated CI
- Configuring pixi environment in GitHub Actions
- Running parallel test groups for faster CI

## Verified Workflow

1. **Create workflow file** at `.github/workflows/test.yml`:

   ```yaml
   name: Test

   on:
     pull_request:
     push:
       branches: [main]

   jobs:
     test:
       runs-on: ubuntu-latest
       steps:
         - uses: actions/checkout@v4

         - name: Install pixi
           uses: prefix-dev/setup-pixi@v0.8.1
           with:
             pixi-version: v0.39.5

         - name: Run tests
           run: pixi run mojo test <test-path>/
   ```

2. **Use matrix for parallel test groups**:

   ```yaml
   strategy:
     matrix:
       test-group:
         - { path: "<test-path>/core", pattern: "test_*.mojo" }
         - { path: "<test-path>/models", pattern: "test_*.mojo" }

   steps:
     - run: pixi run mojo test ${{ matrix.test-group.path }}
   ```

3. **Cache pixi environment**:

   ```yaml
   - uses: prefix-dev/setup-pixi@v0.8.1
     with:
       cache: true
   ```

## Failed Attempts

| Attempt | Why Failed | Lesson |
|---------|-----------|--------|
| Manual Mojo install | Version mismatch, PATH issues | Use pixi for dependency management |
| Single test job | 30+ min runtime | Split into parallel matrix jobs |
| No caching | Slow reinstalls every run | Enable pixi cache |
| `mojo test .` | Didn't find all tests | Specify explicit paths |

## Results & Parameters

```yaml
# Complete workflow example
name: Comprehensive Tests

on:
  pull_request:
    paths: ['**/*.mojo', 'pixi.toml']

jobs:
  test:
    runs-on: ubuntu-latest
    timeout-minutes: 30

    strategy:
      fail-fast: false
      matrix:
        test-group:
          - { name: "core", path: "<test-path>/core" }
          - { name: "models", path: "<test-path>/models" }

    steps:
      - uses: actions/checkout@v4

      - uses: prefix-dev/setup-pixi@v0.8.1
        with:
          pixi-version: v0.39.5
          cache: true

      - name: Run ${{ matrix.test-group.name }} tests
        run: |
          pixi run mojo test ${{ matrix.test-group.path }}
```

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectOdyssey | Mojo v0.25.7 CI setup | [notes.md](../../references/notes.md) |

## References

- Pixi GitHub Action: https://github.com/prefix-dev/setup-pixi
- Mojo test documentation: https://docs.modular.com/mojo/cli/test
- Related: ci-cd/pre-commit-mojo
