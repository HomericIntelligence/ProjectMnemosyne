# Skill: gitattributes-setup

| Field | Value |
|-------|-------|
| Date | 2026-02-22 |
| Objective | Add `.gitattributes` for cross-platform line-ending normalization |
| Outcome | Success — PR #968 merged, no renormalization needed |
| Project | ProjectScylla (HomericIntelligence/ProjectScylla) |

## When to Use

- Repository supports multiple platforms (Linux, macOS, Windows)
- No `.gitattributes` exists at repo root
- Pre-commit hooks handle line-endings but git-level normalization is missing
- Issue symptoms: spurious diffs, merge conflicts, CI failures due to CRLF/LF mismatch

## Verified Workflow

1. **Check if `.gitattributes` exists**
   ```bash
   ls .gitattributes 2>&1 || echo "does not exist"
   ```

2. **Create `.gitattributes`** with this standard template:
   ```gitattributes
   # Normalize line endings for all text files
   * text=auto

   # Python source files — explicit LF
   *.py text diff=python eol=lf

   # YAML, TOML, Markdown — explicit LF
   *.yaml text eol=lf
   *.yml text eol=lf
   *.toml text eol=lf
   *.md text eol=lf

   # Shell scripts — LF (required for execution)
   *.sh text eol=lf

   # Windows batch — CRLF
   *.bat text eol=crlf
   *.cmd text eol=crlf

   # Binary files — no text processing
   *.png binary
   *.jpg binary
   *.pdf binary
   *.gz binary
   *.zip binary
   ```

3. **Run renormalization** to detect any existing files with wrong line endings:
   ```bash
   git add --renormalize .
   git diff --cached --name-only
   ```
   - If files appear: review and commit them as part of the same PR
   - If no files: existing repo is already consistent (common for Linux-native repos)

4. **Verify attributes** against success criteria:
   ```bash
   git check-attr text -- <any>.py   # should return: text: set
   git check-attr eol -- <any>.py    # should return: eol: lf
   git check-attr diff -- <any>.py   # should return: diff: python
   ```

5. **Stage and run pre-commit**:
   ```bash
   git add .gitattributes
   pre-commit run --files .gitattributes
   ```

6. **Commit with conventional commit format**:
   ```
   feat(vcs): add .gitattributes for line-ending normalization and diff drivers
   ```

## Failed Attempts

- **Skill tool invocation** was denied in `don't-ask` permission mode. Used direct `git`/`gh` CLI commands instead — this is the correct fallback when Skills are unavailable.

## Results & Parameters

### Standard `.gitattributes` for Python/cross-platform repos

The template above is suitable for projects with:
- Python source (`.py`) — uses `diff=python` for better hunk headers
- Config files (YAML, TOML) — LF normalized
- Docs (Markdown) — LF normalized
- Shell scripts — LF (required for execution on Unix)
- Windows batch — CRLF (required for Windows execution)

### Verification commands
```bash
# Confirm text attribute is set for a Python file
git check-attr text -- scylla/cli/main.py

# Check all attributes at once
git check-attr -a -- scylla/cli/main.py

# Detect files that would be renormalized
git add --renormalize . && git diff --cached --name-only
```

### PR template used
```markdown
## Summary
- Add `.gitattributes` at repo root for cross-platform line-ending consistency
- `* text=auto` catch-all baseline
- Explicit `eol=lf` for Python, YAML, TOML, Markdown, shell scripts
- `diff=python` for better Python diff hunk headers
- `eol=crlf` for Windows batch files
- Binary marking for image, PDF, archive files

## Test plan
- [ ] `git add --renormalize .` produces no unexpected changes
- [ ] `git check-attr text -- <file>.py` returns `text: set`
- [ ] Pre-commit hooks pass
```
