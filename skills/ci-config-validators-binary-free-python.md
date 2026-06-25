---
name: ci-config-validators-binary-free-python
description: "Binary-free Python validators for CI config syntax gates (NATS HOCON, docker-compose). Use when: (1) adding a CI job that validates NATS server.conf / leaf.conf syntax without running nats-server, (2) validating a docker-compose YAML structurally without docker/podman compose installed, (3) nats-server -t exits non-zero on a valid config due to missing TLS cert files (the TLS-cert trap), (4) podman compose config is not installed on the CI runner (skip-everywhere trap), (5) writing a stdlib-only HOCON brace/string depth checker in Python, (6) needing a PyYAML compose validator that runs on any runner with python3."
category: ci-cd
date: 2026-06-20
version: "1.0.0"
user-invocable: false
verification: verified-local
tags:
  - ci-cd
  - nats
  - hocon
  - python
  - stdlib
  - pyyaml
  - docker-compose
  - compose
  - yaml
  - brace-depth
  - syntax-validation
  - config-gate
  - binary-free
  - github-actions
  - ubuntu-latest
  - validation
  - odysseus
  - issue-198
---

# CI Config Validators: Binary-Free Python (NATS HOCON + docker-compose)

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-06-20 |
| **Objective** | Add CI syntax validation gates for NATS configs and docker-compose files that work on any `ubuntu-latest` runner without installing NATS binaries or docker/podman compose |
| **Outcome** | Successful — stdlib-only HOCON brace/string checker for NATS + PyYAML structural validator for compose; both pass 18/18 unit tests; CI-gated in Odysseus PR #330 (issue #198) |
| **Verification** | `verified-local` — 18/18 tests pass, pre-commit clean; CI on PR #330 pending |
| **Source** | HomericIntelligence/Odysseus issue #198 / PR #330 |

## When to Use

- You need a CI syntax gate for NATS `server.conf` / `leaf.conf` but `nats-server -t` exits non-zero on a valid config because TLS cert files are absent (the TLS-cert trap).
- You want to validate docker-compose YAML structure in CI but `podman compose config` / `docker compose config` are not installed on `ubuntu-latest` runners (skip-everywhere trap).
- You are writing a CI config validator that must run on any runner with only `python3` (no extra binary installs).
- You need a HOCON brace-depth checker that correctly handles braces inside quoted strings (the in-string brace trap — see Failed Attempts).
- You need a compose validator that confirms the file is valid YAML with a non-empty `services` mapping.
- You are adding a `validate-configs` step to a justfile recipe and need a corresponding CI workflow step.

## Verified Workflow

### Quick Reference

```bash
# Run the NATS validator (stdlib-only)
python3 tools/validate_nats_config.py configs/nats/server.conf configs/nats/leaf.conf

# Run the compose validator (needs pyyaml, available via yamllint transitive dep)
python3 tools/validate_compose.py e2e/docker-compose.yml

# Install PyYAML if not already available (via yamllint or directly)
pip install --user pyyaml       # for jobs without yamllint
pip install --user yamllint     # yamllint depends on pyyaml — covers both
```

### NATS HOCON Validator (stdlib-only)

The core pattern: track brace depth line-by-line, but **neutralize characters inside quoted strings** before counting `{`/`}`. This is the critical difference from a naive brace counter.

```python
#!/usr/bin/env python3
"""Binary-free NATS HOCON syntax validator (stdlib-only)."""
import sys
from pathlib import Path


def check(text: str) -> tuple[bool, str]:
    depth = 0
    for ln, raw in enumerate(text.splitlines(), start=1):
        out = []
        instr = False
        q = ""
        i = 0
        while i < len(raw):
            ch = raw[i]
            if instr:
                if ch == "\\" and i + 1 < len(raw):
                    out.append(" ")  # neutralize escaped char — don't count braces
                    out.append(" ")
                    i += 2
                    continue
                if ch == q:
                    instr = False
                out.append(" ")  # CRITICAL: neutralize in-string chars — space, NOT ch
                i += 1
                continue
            if ch == "#":
                break  # comment to end of line
            if ch in "\"'":
                instr = True
                q = ch
            out.append(ch)
            i += 1
        if instr:
            return False, f"unterminated string on line {ln}"
        code = "".join(out)
        depth += code.count("{") - code.count("}")
        if depth < 0:
            return False, f"unmatched }} on line {ln}"
    if depth != 0:
        return False, f"unbalanced braces: {depth} unclosed brace(s)"
    return True, "ok"


def main(argv: list[str]) -> int:
    files = argv[1:] if len(argv) > 1 else []
    if not files:
        print("Usage: validate_nats_config.py <file> [...]")
        return 1
    ok = True
    for path in files:
        text = Path(path).read_text(encoding="utf-8")
        valid, msg = check(text)
        status = "OK" if valid else "FAIL"
        print(f"{status}: {path} — {msg}")
        if not valid:
            ok = False
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
```

### Compose Structural Validator (PyYAML)

```python
#!/usr/bin/env python3
"""Structural docker-compose YAML validator using PyYAML."""
import sys
from pathlib import Path

import yaml


def check(path: Path) -> tuple[bool, str]:
    try:
        doc = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        return False, f"YAML parse error: {exc}"
    if not isinstance(doc, dict):
        return False, "top level is not a mapping"
    services = doc.get("services")
    if not isinstance(services, dict) or not services:
        return False, "missing or empty 'services' mapping"
    for name, svc in services.items():
        if not isinstance(svc, dict):
            return False, f"service '{name}' is not a mapping"
    return True, f"{len(services)} service(s)"


def main(argv: list[str]) -> int:
    files = argv[1:] if len(argv) > 1 else []
    if not files:
        print("Usage: validate_compose.py <file> [...]")
        return 1
    ok = True
    for path in files:
        valid, msg = check(Path(path))
        status = "OK" if valid else "FAIL"
        print(f"{status}: {path} — {msg}")
        if not valid:
            ok = False
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
```

### CI Workflow Integration

```yaml
# In .github/workflows/ci.yml (or a dedicated validate.yml)
jobs:
  validate-configs:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Validate NATS configs (binary-free, stdlib-only)
        run: python3 tools/validate_nats_config.py configs/nats/server.conf configs/nats/leaf.conf

      - name: Install PyYAML (for compose validator)
        run: pip install --user pyyaml

      - name: Validate docker-compose files
        run: python3 tools/validate_compose.py e2e/docker-compose.yml

  validate-recipes:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Install yamllint
        run: pip install --user yamllint  # yamllint depends on pyyaml — both available

      - name: Run config lint (yamllint)
        run: python3 -m yamllint configs/
```

### PyYAML Availability Note

PyYAML is a transitive dependency of `yamllint`. If a CI job already installs `yamllint`, PyYAML is available at no extra cost. For jobs that don't install `yamllint`, add `pip install --user pyyaml` explicitly. Always use `--user` — see the `ci-pip-install-user-pep668` skill.

### Detailed Steps

1. **Identify the validation gap.** Run `nats-server -t -c configs/nats/server.conf` on the CI runner. If it exits non-zero on a syntactically valid config (e.g., TLS cert files absent from `/etc/nats/certs/...`), it is unsuitable as a CI gate — it cannot distinguish syntax errors from missing-cert runtime errors.

2. **Write the stdlib-only NATS validator.** The core loop neutralizes in-string characters (replaces with space, NOT the character itself) before counting brace depth. Comments (starting with `#`) terminate the line. Escaped characters inside strings consume two characters and both are neutralized. Only after stripping strings and comments does brace counting happen.

3. **Write the PyYAML compose validator.** Use `yaml.safe_load()` — never `yaml.load()` (unsafe). Check: top level is a `dict`, `services` key exists and is a non-empty `dict`, each service value is a `dict`. This catches truncated files, missing `services:` key, and malformed service entries.

4. **Wire BOTH validators as explicit CI steps** — not just justfile recipes. A `just validate-configs` recipe in the justfile is never invoked by CI unless the workflow explicitly calls it. Add dedicated `run:` steps in the workflow yaml.

5. **Add unit tests.** The NATS validator should cover: valid config, unmatched `}`, unmatched `{`, braces inside quoted strings (e.g., `token = "a{b}"`), escaped quotes inside strings. The compose validator should cover: valid file, invalid YAML, missing `services` key, non-dict service entry.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --- | --- | --- | --- |
| `nats-server -t` as CI syntax gate | `nats-server -c configs/nats/server.conf -t` | Exits non-zero on a **valid** config when TLS cert files are absent (`/etc/nats/certs/...`); cannot distinguish syntax errors from missing-cert runtime errors | Do not use `nats-server -t` as a CI syntax gate when TLS certs are absent; use stdlib-only Python brace checker instead |
| `podman compose config` / `docker compose config` | Used as compose validity gate | Not installed on `ubuntu-latest` CI runners; makes the step vacuous (always skips) | Use PyYAML structural validator instead; works on any runner with `python3` |
| `out.append(ch)` inside `instr` block | First draft of NATS checker appended the actual character when inside a string | Braces inside quoted strings (e.g., `token = "a{b"`) were counted toward depth, causing false-positive failures on valid configs | Inside the `instr` block, append `" "` (a neutral space) instead of `ch`; this neutralizes the character so brace counting is never affected by string content |
| Using `yaml.load()` without Loader | Draft compose validator used bare `yaml.load(f)` | PyYAML emits `FullLoader` warning; unsafe for untrusted input | Always use `yaml.safe_load()` for config file validation |

## Results & Parameters

```yaml
# Verified on HomericIntelligence/Odysseus (issue #198, PR #330, 2026-06-20)
validation_scope:
  nats_files:
    - configs/nats/server.conf
    - configs/nats/leaf.conf
  compose_files:
    - e2e/docker-compose.yml

tool_files:
  nats_validator: tools/validate_nats_config.py    # stdlib-only
  compose_validator: tools/validate_compose.py      # requires pyyaml

test_results:
  total: 18
  passed: 18
  scope: "NATS validator (string escapes, comments, nested blocks, in-string braces) + compose validator (valid/invalid YAML, missing services, non-dict service)"

pyyaml_availability:
  via_yamllint: true        # yamllint depends on pyyaml — no extra install for jobs that already have yamllint
  explicit_install: "pip install --user pyyaml"   # for jobs without yamllint

ci_integration:
  pattern: "dedicated run: steps in .github/workflows/ci.yml — NOT just a justfile recipe"
  note: "CI only invokes just targets that appear explicitly in workflow steps; a recipe with no CI caller provides zero enforcement"
```

## Verified On

| Project | Context | Details |
| --- | --- | --- |
| HomericIntelligence/Odysseus | 2026-06-20, issue #198, PR #330 | 18/18 unit tests pass; pre-commit clean; CI pending. NATS TLS-cert trap discovered and bypassed with stdlib-only brace checker. In-string brace trap (CRITICAL BUG) found and fixed in draft. |

## References

- [Odysseus issue #198](https://github.com/HomericIntelligence/Odysseus/issues/198)
- [Odysseus PR #330](https://github.com/HomericIntelligence/Odysseus/pull/330)
- [nats-server-auth-authz-hardening skill](nats-server-auth-authz-hardening.md) — brace-depth awk extractor for the auth validator (different approach: awk vs Python)
- [ci-pip-install-user-pep668 skill](ci-pip-install-user-pep668.md) — use `pip install --user` in GitHub Actions
