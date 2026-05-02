---
name: liza-state-yaml-timestamp-normalization
description: "Repair a broken `.liza/state.yaml` after a YAML serializer rewrites RFC3339 timestamps into space-separated datetimes that the Liza CLI cannot parse. Use when: (1) `liza validate`, `liza status`, or `liza resume` fail with `cannot parse ... as \"T\"`, (2) `.liza/state.yaml` was rewritten by PyYAML or another generic YAML emitter, (3) the workspace is otherwise intact but all Liza commands fail on timestamp parsing."
category: debugging
date: 2026-04-07
version: "1.0.0"
user-invocable: false
verification: verified-local
tags:
  - liza
  - yaml
  - timestamp
  - state
  - recovery
  - pyyaml
---

# Liza State YAML Timestamp Normalization

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-04-07 |
| **Objective** | Restore a Liza workspace after `.liza/state.yaml` timestamps were serialized in a format the Liza parser rejects |
| **Outcome** | Successful -- normalized every affected timestamp back to RFC3339 and restored `liza validate`, `liza status`, and `liza resume` |
| **Verification** | verified-local |

## When to Use

- `liza validate`, `liza status`, `liza resume`, or `liza start` fail with errors like `cannot parse " 17:21:30..." as "T"`
- A script rewrote `.liza/state.yaml` using `yaml.safe_dump()` or another serializer that converted `2026-04-07T17:21:30Z` into `2026-04-07 17:21:30+00:00`
- The workspace contents look intact, but every Liza CLI command fails before doing any real work

## Verified Workflow

### Quick Reference

```bash
python3 - <<'PY'
from pathlib import Path
import re

path = Path(".liza/state.yaml")
text = path.read_text()
text = re.sub(
    r'(\d{4}-\d{2}-\d{2}) (\d{2}:\d{2}:\d{2}(?:\.\d+)?)(Z|[+-]\d{2}:\d{2})',
    r'\1T\2\3',
    text,
)
path.write_text(text)
PY

liza validate
liza status --detailed
```

### Detailed Steps

1. Confirm the failure is a timestamp parse error, not a semantic state error:

   ```bash
   liza validate
   ```

2. Inspect the reported value in `.liza/state.yaml`. If it has a space between the date and time instead of `T`, the file format is the problem:

   ```bash
   rg -n '2026-.* [0-9]{2}:[0-9]{2}:[0-9]{2}' .liza/state.yaml
   ```

3. Normalize all affected timestamps in place. Handle both UTC values and local offsets such as `-07:00`:

   ```bash
   python3 - <<'PY'
   from pathlib import Path
   import re

   path = Path(".liza/state.yaml")
   text = path.read_text()
   text = re.sub(
       r'(\d{4}-\d{2}-\d{2}) (\d{2}:\d{2}:\d{2}(?:\.\d+)?)(Z|[+-]\d{2}:\d{2})',
       r'\1T\2\3',
       text,
   )
   path.write_text(text)
   PY
   ```

4. Re-run validation before resuming or starting agents:

   ```bash
   liza validate
   ```

5. Only after validation passes, resume the workspace or rerun your Liza command:

   ```bash
   liza resume
   liza status --detailed
   ```

### Root Cause

Liza expects RFC3339-style timestamps in `.liza/state.yaml`, for example `2026-04-07T17:21:30Z` or `2026-04-07T11:38:50-07:00`. Generic YAML emitters such as PyYAML can silently rewrite those scalars as `2026-04-07 17:21:30+00:00`. The timestamp is still human-readable, but Liza's parser rejects it because it requires the literal `T` separator.

### Guardrail

If you need to patch `.liza/state.yaml`, prefer minimal text edits that preserve existing timestamp formatting. Avoid round-tripping the whole file through `yaml.safe_dump()` unless you are prepared to normalize timestamps afterward.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| Normalizing only `+00:00` timestamps | Replaced `YYYY-MM-DD HH:MM:SS+00:00` with `YYYY-MM-DDTHH:MM:SSZ` | Local timestamps such as `2026-04-07 11:38:50.820435-07:00` still broke the parser | Use one regex that handles both `Z`/UTC and signed offsets |
| Running `liza resume` before re-validating | Tried to resume immediately after partial repair | Liza failed on the next malformed timestamp and the workspace stayed down | Always run `liza validate` first so you catch every parse error in one pass |
| Rewriting the whole YAML via `yaml.safe_dump()` | Cleared one stale field and wrote the whole state back out | PyYAML changed timestamp formatting across the file, introducing new parser errors | For live Liza state, serializer convenience is not worth the format drift risk |

## Results & Parameters

### Regex

```python
r'(\d{4}-\d{2}-\d{2}) (\d{2}:\d{2}:\d{2}(?:\.\d+)?)(Z|[+-]\d{2}:\d{2})'
```

### Expected Before/After

| Before | After |
| -------- | ------- |
| `2026-04-07 17:21:30.117542+00:00` | `2026-04-07T17:21:30.117542+00:00` |
| `2026-04-07 11:38:50.820435-07:00` | `2026-04-07T11:38:50.820435-07:00` |

### Success Criteria

- `liza validate` returns `VALID`
- `liza status --detailed` reads the workspace again
- `liza resume` or the next operational command succeeds without timestamp parse errors

## Verified On

| Project | Context | Details |
| --------- | --------- | --------- |
| Radiance | Live Liza workspace recovery after direct state edits | Restored a broken `.liza/state.yaml` that had 281 timestamps rewritten into space-separated form |
