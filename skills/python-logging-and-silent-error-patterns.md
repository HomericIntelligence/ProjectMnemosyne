---
name: python-logging-and-silent-error-patterns
description: "Diagnose and fix Python logging configuration bugs and silent-error anti-patterns. Use when: (1) log lines show duplicated context prefixes or empty delimiters like [//], (2) get_logger() adds duplicate StreamHandlers on repeated calls, (3) KeyError on custom %(field)s format placeholders, (4) LoggerAdapter.process() mutates the caller's extra dict, (5) a function silently swallows ValueError and falls back to a default instead of raising, (6) a string-typed enum is not normalized in-place so downstream middleware fails-open, (7) a Python CLI flag is silently prefix-matched by argparse causing a silent no-op, (8) __repr__ produces untruncated output inconsistent with __str__."
category: debugging
date: 2026-05-19
version: "1.0.0"
user-invocable: false
history: python-logging-and-silent-error-patterns.history
tags:
  - python
  - logging
  - deduplication
  - handlers
  - filter-placement
  - LoggerAdapter
  - silent-failure
  - POLA
  - fail-open
  - argparse
  - repr-truncation
---

# Python Logging and Silent Error Patterns

## Overview

| Field | Value |
| ------- | ------- |
| **Theme** | Python logging configuration bugs and silent-error / fail-open anti-patterns |
| **Scope** | Duplicate log handlers, mutated context dicts, wrong filter placement, silent ValueError swallowing, fail-open auth defaults, argparse prefix-matching, repr inconsistency |
| **Diagnostic strategy** | Find where errors or context are silently dropped; the fix is always to guard or re-raise |
| **Languages** | Python 3.10+ (logging patterns); Go examples in auth section |

## When to Use

- Log output contains the same context field twice per line, or outside-scope lines show `[//]` or `[/]`
- `get_logger("name")` called multiple times produces duplicate log lines
- `KeyError: 'custom_field'` when using custom `%(field)s` placeholders in format strings
- A `LoggerAdapter` subclass overrides `process()` and calls `extra.update()` on the caller's dict, leaking context between calls
- A function catches `ValueError` and silently falls back to a default format instead of raising
- Auth middleware's switch has a `default:` branch that calls `next.ServeHTTP` (fail-open), combined with un-normalized string-typed enum from env var
- A Python CLI in CI has been failing silently — after removing `|| true` or `continue-on-error`, argparse exits with code 2 due to prefix-matched flag abbreviations
- A class has truncated `__str__` but unguarded `__repr__`, causing performance issues on large objects

## Verified Workflow

### Quick Reference

| Pattern | Root Cause | One-line Fix |
| --------- | ------------ | -------------- |
| Duplicate context in log lines | Filter injects AND f-string prefixes | Remove manual f-string prefixes; use composite tag from filter |
| `[//]` when no context set | Format field always renders | Build composite `log_context_tag`; empty string when no context |
| Duplicate StreamHandlers | `if not logger.handlers` guard is all-or-nothing | Check each handler type independently (isinstance or registry) |
| `KeyError` on `%(field)s` | Filter attached to logger, not handler | `for h in logging.getLogger().handlers: h.addFilter(f)` |
| `process()` mutates caller dict | `extra.update(self._context)` in-place | `kwargs["extra"] = {**kwargs.get("extra", {}), **context}` |
| Silent ValueError fallback | `except ValueError: fmt = "json"` | Remove try/except; let ValueError propagate |
| Fail-open auth | Enum not normalized in-place + default falls through | Normalize field in Validate; add explicit `default: 401` |
| argparse silent no-op | `--require` prefix-matches `--requirement` | Use full flag name; set `allow_abbrev=False` in own code |
| `__repr__` untruncated | Loop over all elements, no threshold | Mirror `__str__` truncation with named constants |

---

### 1. Duplicate Log Context and `[//]` Artifact

**Symptom**: log lines show context twice (e.g., `[T5/12/1]` from format AND `[T5/12/run_01]` from f-string), or show `[//]` when no context is set.

**Fix**: move all context rendering into the filter as a single composite tag.

```python
# In ContextFilter.filter():
def filter(self, record):
    tier_id = getattr(_context, "tier_id", "")
    subtest_id = getattr(_context, "subtest_id", "")
    run_num = getattr(_context, "run_num", None)

    if tier_id or subtest_id or run_num is not None:
        parts = [tier_id, subtest_id]
        if run_num is not None:
            parts.append(str(run_num))
        record.log_context_tag = " [" + "/".join(parts) + "]"
    else:
        record.log_context_tag = ""
    return True
```

```python
# Format string — use the composite tag, not individual fields:
format="%(asctime)s [%(levelname)s] [%(threadName)s]%(log_context_tag)s %(name)s: %(message)s"
#                                     ^^^ threadName not thread (avoids raw memory address)
```

Remove all manual `[tier/sub/run]` f-string prefixes from log call sites.

---

### 2. Duplicate Handlers in `get_logger()`

**Symptom**: calling `get_logger("name")` twice produces two `StreamHandler` lines per log statement; or a file handler is silently skipped on the second call.

Two verified approaches — choose based on complexity:

#### Approach A: isinstance-based inspection (simpler, no external state)

```python
import os, sys, logging

def get_logger(name: str, log_file: str | None = None) -> logging.Logger:
    logger = logging.getLogger(name)

    # FileHandler IS a subclass of StreamHandler — must exclude it
    has_console = any(
        isinstance(h, logging.StreamHandler) and not isinstance(h, logging.FileHandler)
        for h in logger.handlers
    )
    if not has_console:
        logger.addHandler(logging.StreamHandler(sys.stdout))

    if log_file:
        resolved = os.path.abspath(log_file)
        has_file = any(
            isinstance(h, logging.FileHandler) and h.baseFilename == resolved
            for h in logger.handlers
        )
        if not has_file:
            logger.addHandler(logging.FileHandler(log_file))

    logger.propagate = False
    return logger
```

#### Approach B: Module-level registry (better for custom handler types)

```python
_configured_loggers: dict[str, set[str]] = {}

def get_logger(name: str, log_file: str | None = None) -> logging.Logger:
    logger = logging.getLogger(name)
    configured = _configured_loggers.setdefault(name, set())

    if "console" not in configured:
        logger.addHandler(logging.StreamHandler(sys.stdout))
        configured.add("console")

    if log_file and log_file not in configured:
        logger.addHandler(logging.FileHandler(log_file))
        configured.add(log_file)

    logger.propagate = False
    return logger
```

Test cleanup for Approach B:

```python
@pytest.fixture(autouse=True)
def _clean_logging_registry():
    yield
    for name in list(_configured_loggers):
        if name.startswith("test."):
            _configured_loggers.pop(name, None)
            logging.getLogger(name).handlers.clear()
```

---

### 3. Filter Placement — `KeyError` on Custom Format Fields

**Symptom**: `KeyError: 'tier_id'` or `ValueError: Formatting field not found in record` at runtime despite a `ContextFilter` that sets `record.tier_id`.

**Root cause**: filter was added to the logger (`addFilter`), not the handler. Formatters run inside `Handler.emit()`, which is called after `Handler.filter()`. Filters on the *logger* run before handler dispatch but inject into the record *before* the handler's own filter runs — in multi-threaded Python 3.14t builds this timing can be unreliable; in any version, attaching to the handler is the canonical, guaranteed approach.

```python
# WRONG
logging.getLogger().addFilter(ContextFilter())

# RIGHT — attach to every handler
for handler in logging.getLogger().handlers:
    handler.addFilter(ContextFilter())
```

Pipeline order:

```
Logger.handle()
  -> Logger.filter(record)
  -> Logger.callHandlers()
     -> Handler.handle(record)
        -> Handler.filter(record)   ← inject fields here
        -> Handler.emit(record)
           -> Formatter.format(record)  ← %(field)s resolved here
```

**Integration test pattern** — must use `handle()`, NOT `format()`:

```python
def test_handler_pipeline():
    handler = logging.StreamHandler()
    handler.addFilter(ContextFilter())
    handler.setFormatter(logging.Formatter("[%(tier_id)s] %(message)s"))
    record = logging.LogRecord(
        name="test", level=logging.INFO,
        pathname="", lineno=0, msg="hello", args=(), exc_info=None,
    )
    handler.handle(record)  # runs filter -> emit -> format; must not raise
```

---

### 4. `LoggerAdapter.process()` Mutating Caller Dict

**Symptom**: context from one log call leaks into the next; caller's `extra` dict is modified after `logger.info(...)`.

```python
# BEFORE (buggy — mutates caller's dict in-place):
def process(self, msg, kwargs):
    extra = kwargs.get("extra", {})
    extra.update(self._context)        # modifies the dict the caller passed in
    kwargs["extra"] = extra
    return msg, kwargs

# AFTER (safe — creates new dict, holds lock while reading context):
def process(self, msg: Any, kwargs: Any) -> tuple[Any, Any]:
    with self._context_lock:
        context = self._context.copy()
    kwargs["extra"] = {**kwargs.get("extra", {}), **context}
    return msg, kwargs
```

Regression test:

```python
def test_process_does_not_mutate_caller_extra(self) -> None:
    logger = get_logger("test.no_mutate", context={"ctx_key": "ctx_val"})
    caller_extra: dict[str, str] = {"request_id": "abc"}
    original_extra = caller_extra.copy()
    logger.process("msg", {"extra": caller_extra})
    assert caller_extra == original_extra
```

---

### 5. Silent Error Suppression (POLA Violations)

**Symptom**: `save_data(data, "file.csv")` silently creates a JSON file; `load_data()` raises `ValueError` correctly but the save side does not.

**Pattern**: any `try/except SomeError: fallback_value` that swallows an exception from a helper and returns a "default" instead of propagating.

```python
# BEFORE (anti-pattern)
try:
    fmt = _detect_format(filepath, format_hint)
except ValueError:
    fmt = "json"   # silent fallback — produces wrong output format

# AFTER (correct)
fmt = _detect_format(filepath, format_hint)   # let ValueError propagate
```

Detection heuristic:

```bash
# Find try/except blocks that catch and swallow ValueError without re-raising
grep -B1 -A2 "except ValueError" src/ --include="*.py" -rn | grep -v "raise"
```

---

### 6. Fail-Open Auth — Case-Mismatched Enum

**Symptom**: setting `ATLAS_AUTH_MODE=Bearer` (title-case) returns HTTP 200 to unauthenticated callers; `bearer` (all-lowercase) correctly returns HTTP 401.

**Two interacting bugs**:

1. `Config.Validate` lowercases into a *local* switch tag — the struct field remains mixed-case.
2. Auth middleware `default:` branch falls through to `next.ServeHTTP` instead of returning 401.

```go
// FIX 1: normalize the field IN PLACE
func (c *Config) Validate(logger *slog.Logger) error {
    c.AuthMode = strings.ToLower(strings.TrimSpace(c.AuthMode)) // mutate the field
    switch c.AuthMode {
    case "bearer": /* ... */
    case "basic":  /* ... */
    case "none":   /* ... */
    default:
        return fmt.Errorf("unknown mode %q", c.AuthMode)
    }
}
```

```go
// FIX 2: fail-closed default in middleware
switch mode {
case AuthNone:   // explicit pass-through
case AuthBasic:  /* check or 401 */
case AuthBearer: /* check or 401 */
default:
    http.Error(w, "Unauthorized", http.StatusUnauthorized)
    return
}
next.ServeHTTP(w, r)
```

Apply both fixes together — Validate normalization closes the known path; middleware fail-closed defends against future refactors.

This pattern generalizes to any env-var-derived string enum: `LOG_LEVEL=Debug`, feature flags, cache modes, throttling modes.

---

### 7. argparse Ambiguous Flag Silent No-Op

**Symptom**: A Python CLI in CI silently does nothing. After removing `|| true` or `continue-on-error`, it exits with code 2 (argparse error).

**Root cause**: argparse `allow_abbrev=True` (default since Python 3.5) expands prefix-matching flag abbreviations silently. `--require aider-chat` expands to `--requirement aider-chat` (expecting a file path), fails to open the file, exits 2, and a `|| true` wrapper hides the failure for weeks.

```bash
# Diagnose: strip suppression wrapper, run bare
<tool> <args>
# Read stderr — look for "--<expanded-flag>" in the error message

# Confirm: search --help for prefix collision
<tool> --help 2>&1 | grep -E "^\s*--<short-prefix>"

# Audit codebase for similar risk:
grep -rn -E '\b(pip-audit|pytest|mypy|ruff|sphinx-build|gunicorn|uvicorn)\b.*--[a-z]{3,5}\b' \
  .github/ scripts/ tests/ 2>/dev/null
```

For your own argparse code:

```python
parser = argparse.ArgumentParser(allow_abbrev=False)  # forces full flag names
```

Key rule: for consumed CLIs (pip-audit, pytest, mypy, etc.), always use the full flag name. Never abbreviate.

---

### 8. `__repr__` Truncation Consistency

**Symptom**: `repr(obj)` on a large tensor/array produces an extremely long string; `str(obj)` is already truncated with NumPy-style `...`.

**Fix**: mirror the same threshold check and named constants in `__repr__`:

```python
TRUNCATE_THRESHOLD = 1000
SHOW_ELEMENTS = 3

def __repr__(self):
    # ... build prefix ...
    if len(self) > TRUNCATE_THRESHOLD:
        head = [str(self[i]) for i in range(SHOW_ELEMENTS)]
        tail = [str(self[i]) for i in range(len(self) - SHOW_ELEMENTS, len(self))]
        data = ", ".join(head) + ", ... " + ", ".join(tail)
    else:
        data = ", ".join(str(self[i]) for i in range(len(self)))
    return f"<prefix>, data=[{data}])"
```

Use named constants (not hardcoded literals) so both methods stay in sync.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| Remove filter, add manual prefixes everywhere | Strip ContextFilter; add `[tier/sub/run]` to every log call site | Hundreds of call sites; not scalable | Use filters for cross-cutting concerns; keep message strings context-free |
| Conditional format string with `%(tier_id)s` | Static format string with per-field placeholders | `logging.Formatter` does not support conditional sections; always renders `[//]` when fields empty | Build the conditional composite field in the Filter; emit a single `log_context_tag` |
| `os.setpgrp()` for signal handling | Creates new process group for the parent | Detaches from terminal's foreground group; Ctrl+C no longer reaches the process | Child processes use `start_new_session=True`; parent does not need its own group |
| `if not logger.handlers` guard | All-or-nothing check before adding any handler | Blocks adding file handler on second call; does not distinguish handler types | Check each handler type independently via isinstance or a string-keyed registry |
| `type(h)` without attribute inspection | Check `type(h) is FileHandler` for deduplication | Does not distinguish two FileHandlers for different paths | Compare `h.baseFilename` (absolute path) against `os.path.abspath(log_file)` |
| `isinstance(h, StreamHandler)` without FileHandler exclusion | Count any StreamHandler as a console handler | `FileHandler` is a subclass of `StreamHandler`; file handlers are counted as console, preventing console from being added | Always use `isinstance(h, StreamHandler) and not isinstance(h, FileHandler)` |
| Rely on `propagate=True` (default) | Let parent logger handle output | Parent + child both emit when both have handlers | Set `logger.propagate = False` on any logger that owns its own handlers |
| Test filter with `handler.format(record)` | Call format directly to test field injection | `format()` does not invoke filters; fields are injected in `handle() -> filter() -> emit() -> format()` | Always test through `handler.handle()` for integration tests |
| Filter on logger only | `logging.getLogger().addFilter(ContextFilter())` | In Python 3.14t free-threaded builds with ThreadPoolExecutor, injection was unreliable | Attach filter to each handler for guaranteed field injection before formatting |
| `extra.update(self._context)` in LoggerAdapter | Update the caller-provided dict in-place | Mutates the dict object the caller still holds; context keys persist across calls | Use spread: `{**kwargs.get("extra", {}), **context}` for a fresh dict every call |
| Lowercase switch tag only (Go auth) | `switch mode := strings.ToLower(c.AuthMode); mode` — lowercase local, not field | Downstream middleware reads the un-normalized field; mixed-case bypasses exact typed const comparison | Normalize the struct field itself (`c.AuthMode = strings.ToLower(...)`) |
| Fix middleware default only (Go auth) | Made default branch fail-closed; left Validate as-is | Valid mixed-case config now passes Validate but 401s every request | Both fixes required: Validate normalizes (so configs work); middleware fail-closed is defense-in-depth |
| Re-add `\|\| true` after seeing bare CLI fail | Suppression re-added after deterministic argparse exit-2 was observed | Banned by ci-cd-forbid-suppressions guard; hides the same bug again | When removing a suppression surfaces a deterministic error, fix the underlying invocation |
| `pip-audit -r aider-chat` (short form) | Short form `-r` of `--requirement` passed with package name | `-r` expects a requirements file path; same underlying bug, different spelling | Fix is not renaming the flag; understand what the tool actually does |
| Using hardcoded literals in `__repr__` | Copied threshold value `1000` as a literal instead of a named constant | Will diverge from `__str__` if the threshold changes | Use named constants shared between `__repr__` and `__str__` |
| Skip `__repr__` tests assuming `__str__` covers it | `__str__` test suite provided coverage | `__repr__` output includes shape and numel prefix; format assertions differ | Mirror the `__str__` test file but adjust expected strings for `__repr__` format |

## Results & Parameters

### Log output before/after (context deduplication)

```
# Before:
2026-03-18 20:10:16 [INFO] [T:136414484813504] [//] scylla.e2e.runner: Experiment completed
2026-03-18 20:10:16 [INFO] [T:136414484813504] [T5/12/1] scylla.e2e.state_machine: [T5/12/run_01] dir_structure_created -> worktree_created (2.8s)

# After:
2026-03-18 20:10:16 [INFO] [MainThread] scylla.e2e.runner: Experiment completed
2026-03-18 20:10:16 [INFO] [Thread-1] [T5/12/1] scylla.e2e.state_machine: dir_structure_created -> worktree_created (2.8s)
```

### Handler deduplication behavior

```python
logger1 = get_logger("app")                       # 1 StreamHandler
logger2 = get_logger("app")                       # still 1 StreamHandler
logger3 = get_logger("app", log_file="app.log")   # 1 StreamHandler + 1 FileHandler
logger4 = get_logger("app", log_file="app.log")   # still 1 StreamHandler + 1 FileHandler
```

### Approach selection for handler deduplication

| Criterion | Approach A (isinstance) | Approach B (registry) |
| ----------- | ------------------------ | ---------------------- |
| External state | None | Module-level dict |
| Test cleanup | No cleanup needed | Must clear registry between tests |
| Custom handler types | Requires isinstance for each type | Just add a string key |
| Simplicity | Simpler for standard handlers | Better for complex handler setups |

### argparse audit regex

```bash
grep -rn -E '\b(pip-audit|pytest|mypy|ruff|sphinx-build|gunicorn|uvicorn|black|isort|coverage)\b.*--[a-z]{3,5}\b' \
  .github/ scripts/ tests/ 2>/dev/null
```

### `__repr__` truncation invariants

- `numel <= 1000`: all elements shown, no `...`
- `numel > 1000`: first 3 + `...` + last 3
- `numel == 0`: `data=[]` with no errors
- `...` appears only in the `data=[...]` section, not in shape/dtype prefix

## Verified On

| Project | Context | Details |
| --------- | --------- | --------- |
| ProjectScylla | PR #1516 — ContextFilter filter placement fix | 4926 tests pass, 77.74% coverage |
| ProjectScylla | Logging dedup session 2026-03-18 | 171 unit + 6 log_context tests pass |
| ProjectHephaestus | Issue #32 — PR #70 | get_logger registry approach, 389 tests pass |
| ProjectHephaestus | Issue #54 — PR #98 | isinstance approach for file handler, 438 tests pass |
| ProjectHephaestus | Issue #60 — PR #118 | ContextLogger.process mutation fix, 15/15 tests pass |
| ProjectHephaestus | Issue #53 — PR #97 | save_data() silent JSON fallback removed, 435 tests pass |
| HomericIntelligence/ProjectArgus | Atlas v0.2.0 → v0.2.1 | Case-mismatch fail-open auth fixed, regression tests in CI |
| HomericIntelligence/AchaeanFleet | PR #656 + issue #655 | argparse prefix-match no-op fixed; 57 CVEs surfaced |
| ProjectOdyssey | PR #4858, Issue #4038 | `__repr__` truncation, 11 test cases added |
