# planning-refactor-risk-review Notes

Raw learning captured from a ProjectHephaestus planning session for GitHub issue #1396.

The implementation plan proposed adding a shared helper:

```python
log_file_path(state_dir, prefix, issue_number, *, iteration=None)
```

in `hephaestus/automation/_review_utils.py` and migrating repeated per-issue automation log path constructions to it.

Important preservation points:

- The plan relied on a grep-style inventory:

  ```bash
  rg -n 'state_dir / f.*\.log|self\.state_dir / f.*\.log' hephaestus/automation -g '*.py'
  ```

- The plan also relied on file/line references from the then-current ProjectHephaestus checkout, but those exact line numbers and complete-call-site coverage were not directly re-verified during learn capture.
- The plan assumed `_review_utils.py` is the right home for a generic log path helper because it already hosts shared review automation utilities. Reviewers should verify that introducing a log-path helper there does not create undesirable coupling for non-review modules like implement, learn, planner, follow-up, or CI driver flows.
- The plan assumed the helper preserves all existing filenames, including dynamic prefixes and iteration suffixes, while leaving parse diagnostics (`.parse-error.log`) and non-canonical logs unchanged. Reviewers should focus on accidental filename drift and missed suffix conventions.
- The plan intentionally rejected adding an `issue_log()` context manager because write mechanics differ across sites. Reviewers should check that migration remains path-only and does not change write semantics, metadata capture, timeout handling, stdout handling, or caller-provided paths.
- The verification plan included focused pytest targets, Ruff check/format, and a custom scan for bypassed canonical issue logs. These were planned, not executed as part of the planning session.
- No GitHub issue #1396 body, current files, or external APIs were directly verified during the learn request. Treat details that depend on live repo state as unverified and reviewer-facing risks.
