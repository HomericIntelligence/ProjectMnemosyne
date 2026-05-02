# Session Notes: dockerfile-cargo-free-regression

## Context

- **Issue**: ProjectOdyssey #3351 — Add Dockerfile static regression test for cargo-free build
- **Follow-up from**: #3152 (removed cargo from Dockerfiles in favor of pre-built `just` binary)
- **Branch**: `3351-auto-impl`
- **PR**: ProjectOdyssey #3991

## Raw Session Timeline

1. Read `.claude-prompt-3351.md` — task is to add static tests preventing `cargo` re-introduction
2. Explored `tests/foundation/` for existing test patterns
3. Confirmed `Dockerfile` line 37 had a comment: `# Install just tool (pre-built binary, much faster than cargo install)`
4. Confirmed `Dockerfile.ci` had zero `cargo` references
5. Wrote `tests/foundation/test_dockerfile_cargo_free.py` with two test methods, parametrized over both Dockerfiles
6. Added `no-cargo-in-dockerfile` pygrep hook to `.pre-commit-config.yaml`
7. First test run: **FAILED** — `test_cargo_install_not_present[Dockerfile]` matched the comment on line 37
8. Fixed by rewriting comment to: `# Install just tool (pre-built binary, avoids cargo build-from-source)`
9. Second test run: **4/4 PASSED**
10. Committed (pre-commit ran ruff formatter which reformatted assert messages from parenthesized to inline f-string)
11. Pushed, created PR, enabled auto-merge

## File Locations (ProjectOdyssey)

- Test: `tests/foundation/test_dockerfile_cargo_free.py`
- Hook: `.pre-commit-config.yaml` (inside first `local` repo block)
- Fixed comment: `Dockerfile:37`

## Ruff Formatting Note

Ruff reformatted the assert messages from:

```python
assert match is None, (
    f"Found 'cargo' in apt-get install in {dockerfile.name}: {match.group()!r}"
)
```

to:

```python
assert match is None, f"Found 'cargo' in apt-get install in {dockerfile.name}: {match.group()!r}"
```

The pre-commit hook caught this and modified the file; a second `git add` + `git commit` was needed.
