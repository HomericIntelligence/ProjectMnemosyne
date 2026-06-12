---
name: library-product-import-boundary-enforcement-test
description: "Enforce a library-vs-product import boundary with two regression tests: a subprocess-isolated import-surface check and a static import grep. Use when: (1) gating a heavy product subpackage (curses/pydantic/fcntl) behind an optional extra so base `import pkg` stays lean, (2) writing a test that asserts `import pkg` does not pull forbidden modules, (3) a CI import-surface test gives false failures because pytest itself preloads the forbidden dependency."
category: testing
date: 2026-06-11
version: "1.0.0"
user-invocable: false
verification: verified-ci
tags: []
---

## Overview

When a heavy "product" layer (CLI/automation code with deps like `curses`,
`pydantic`, `fcntl`) is co-located in the same distribution as a lean utility
"library", the base `import pkg` surface must stay cheap. If product modules
leak into the base import path, every consumer of the library pays the cost of
loading the product's dependency tree, and the dependency arrow that an ADR
declares (product → library, never the reverse) silently rots.

This skill captures two complementary regression tests that enforce the
boundary mechanically, plus the hard-won gotchas that make them correct rather
than flaky. It was learned driving **ProjectHephaestus PR #997 (issue #711)**
to green CI — documenting and gating `hephaestus.automation` as an opt-in
product layer behind a `[automation]` optional extra, with the contract written
in `docs/adr/0001-automation-library-boundary.md`.

The two tests:

1. **Import-surface test (subprocess-isolated)** — assert `import pkg` does NOT
   add forbidden modules to `sys.modules`. Runs in a fresh interpreter because
   pytest pre-pollutes `sys.modules`.
2. **Static import-grep test** — walk the library tree and flag any
   `from pkg.product` / `import pkg.product` line, proving the dependency arrow
   points only one way.

## When to Use

Use this skill when:

- You are gating a heavy product subpackage (`curses`/`pydantic`/`fcntl`-style
  deps) behind an optional extra so the base `import pkg` stays lean.
- You need a test that asserts `import pkg` does not pull forbidden modules into
  `sys.modules`.
- A CI import-surface test gives false failures because **pytest itself**
  preloads the forbidden dependency (e.g. `pydantic`) before your assertion
  runs.
- You want to enforce a one-way dependency arrow declared in an ADR (product →
  library, never library → product) with a mechanical regression test rather
  than code review vigilance.

## Verified Workflow

The boundary is documented in an ADR (e.g. `docs/adr/0001-...`) and enforced by
two tests placed under the **mirrored** test path
(`tests/unit/validation/`, not `tests/unit/` root) per the
test-tree-mirrors-package convention.

### Quick Reference

| Goal | Technique | Critical detail |
| --- | --- | --- |
| Assert `import pkg` stays lean | Subprocess import-surface test | Run in `sys.executable -c`, parse a printed `LEAKED:` line — never in-process |
| Forbidden modules list | `curses`, `pydantic`/`pydantic.*`, `pkg.product.*` | NEVER include `fcntl` — stdlib `pathlib` loads it transitively on POSIX |
| One-way dependency arrow | Static grep over `LIB_ROOT.rglob("*.py")` | Skip paths whose parts contain the product package name |
| Gate heavy deps | `[project.optional-dependencies] automation = [...]` | Don't duplicate base deps (e.g. `tzdata`) into the extra |
| Keep docs honest | ADR / test-docstring / pyproject must agree | Verify enumerated facts (script counts) against the actual codebase |

**1. Subprocess-isolated import-surface test.** Run the import in a fresh
interpreter and parse a printed marker. Doing this in-process is meaningless:
pytest already imports `pydantic`, so `sys.modules` is pre-polluted and the
assertion false-passes.

```python
import subprocess
import sys

code = (
    "import sys\n"
    "before = set(sys.modules)\n"
    "import hephaestus  # noqa: F401\n"
    "after = set(sys.modules)\n"
    "new = after - before\n"
    "leaked = sorted(m for m in new if m == 'curses' or m == 'pydantic' "
    "or m.startswith('pydantic.') or m.startswith('hephaestus.automation'))\n"
    "print('LEAKED:' + ','.join(leaked))\n"
)
result = subprocess.run(
    [sys.executable, "-c", code],
    check=True,
    capture_output=True,
    text=True,
)
leaked_line = next(
    line for line in result.stdout.splitlines() if line.startswith("LEAKED:")
)
leaked = [m for m in leaked_line[len("LEAKED:"):].split(",") if m]
assert not leaked, f"import hephaestus leaked forbidden modules: {leaked}"
```

**2. Static import-grep test.** Walk the library tree, skip the product
subpackage itself, and flag any direct import of the product layer. This proves
the arrow points only one way (`automation → library`, never the reverse).

```python
from pathlib import Path
import hephaestus

LIB_ROOT = Path(hephaestus.__file__).parent
violations = []
for py in LIB_ROOT.rglob("*.py"):
    if "automation" in py.relative_to(LIB_ROOT).parts:
        continue  # the product layer may import the library; skip it
    for lineno, line in enumerate(py.read_text(encoding="utf-8").splitlines(), 1):
        s = line.strip()
        if s.startswith(("from hephaestus.automation", "import hephaestus.automation")):
            violations.append(f"{py.relative_to(LIB_ROOT)}:{lineno}: {s}")
assert not violations, "library imports product layer:\n" + "\n".join(violations)
```

**3. Gate the heavy deps behind an optional extra.** In `pyproject.toml`, the
product layer's dependencies install only via `pkg[automation]`:

```toml
[project.optional-dependencies]
automation = ["pydantic>=2", ...]
```

The base `import pkg` surface stays lean; `pip install pkg[automation]` pulls
the product deps.

**4. The `fcntl` stdlib transitive-load trap (key gotcha).** `fcntl` cannot be
in the forbidden list. Python stdlib `pathlib` transitively loads `fcntl` on
POSIX, so asserting `import pkg` doesn't load `fcntl` gives a
platform-dependent false failure. The contract is about modules the package's
code imports **directly** (`curses`, `pydantic`), not stdlib transitive loads.
Keep the ADR Consequences section and the test docstring consistent — remove
`fcntl` from both so the documentation matches the actual assertion.

**5. Doc / test / config consistency (review findings).**

- ADR enumerated facts must match reality: the ADR listed seven console scripts
  including a non-existent `hephaestus-audit-prs`; the actual count is six.
  Verify enumerated facts against the codebase before claiming them.
- Don't add redundant deps to the optional extra: `tzdata` was already a base
  dependency for library code, so it did not belong in `[automation]`.
- Place the new tests under the mirrored path `tests/unit/validation/`, not
  `tests/unit/` root, per the test-structure-mirrors-package requirement.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --- | --- | --- | --- |
| In-process import-surface check | Asserted forbidden modules absent from `sys.modules` inside the pytest process | pytest preloads `pydantic`, so `sys.modules` is already polluted → assertion meaningless / false-passing | Run the check in a fresh interpreter via `subprocess.run([sys.executable, "-c", ...])` and parse a printed marker |
| Forbid `fcntl` in the surface assertion | Added `fcntl` to the leaked-module list | stdlib `pathlib` transitively loads `fcntl` on POSIX → platform-dependent false failure | Only forbid modules the package imports directly (`curses`, `pydantic`); exclude stdlib transitive loads |
| `tzdata` in `[automation]` extra | Listed `tzdata` under the optional automation extra | `tzdata` was already a base dependency for library code → redundant | Don't duplicate base deps into optional extras; audit the base list first |
| Tests at `tests/unit/` root | Placed new boundary tests in `tests/unit/` directly | Project requires the test tree to mirror package structure (`validation/`) | Place enforcement tests under the mirrored subdir, e.g. `tests/unit/validation/` |
| ADR listed seven scripts | ADR enumerated console scripts including non-existent `hephaestus-audit-prs` | Drifted from reality (six scripts) → review caught it | Verify enumerated facts in ADRs against the actual codebase before claiming them |

## Results & Parameters

**Outcome:** ProjectHephaestus PR #997 (issue #711) merged green on 2026-06-12.
The `hephaestus.automation` product layer is now documented in
`docs/adr/0001-automation-library-boundary.md`, gated behind the
`[automation]` optional extra, and enforced by two regression tests under
`tests/unit/validation/`.

**Parameters / knobs:**

| Parameter | Value used | Notes |
| --- | --- | --- |
| Forbidden modules | `curses`, `pydantic`, `pydantic.*`, `pkg.product.*` | Modules the package imports *directly*; never stdlib transitive loads |
| Excluded from forbidden list | `fcntl` | `pathlib` loads it on POSIX — would cause platform-dependent false failure |
| Import-surface isolation | `subprocess.run([sys.executable, "-c", code], check=True, capture_output=True, text=True)` | Fresh interpreter; parse the `LEAKED:` line from stdout |
| Grep skip rule | `"automation" in py.relative_to(LIB_ROOT).parts` | Product layer may import library; skip it |
| Optional extra | `[project.optional-dependencies] automation = [...]` | Heavy deps install only via `pkg[automation]` |
| Test location | `tests/unit/validation/` | Mirror the package structure, not `tests/unit/` root |

**Two short test bodies (verbatim).** Import-surface check:

```python
code = (
    "import sys\n"
    "before = set(sys.modules)\n"
    "import hephaestus  # noqa: F401\n"
    "after = set(sys.modules)\n"
    "new = after - before\n"
    "leaked = sorted(m for m in new if m == 'curses' or m == 'pydantic' "
    "or m.startswith('pydantic.') or m.startswith('hephaestus.automation'))\n"
    "print('LEAKED:' + ','.join(leaked))\n"
)
result = subprocess.run([sys.executable, "-c", code], check=True, capture_output=True, text=True)
# parse the LEAKED: line, assert empty
```

Static grep core:

```python
LIB_ROOT = Path(hephaestus.__file__).parent
for py in LIB_ROOT.rglob("*.py"):
    if "automation" in py.relative_to(LIB_ROOT).parts:
        continue
    for lineno, line in enumerate(py.read_text(encoding="utf-8").splitlines(), 1):
        s = line.strip()
        if s.startswith(("from hephaestus.automation", "import hephaestus.automation")):
            violations.append(...)
assert not violations
```
