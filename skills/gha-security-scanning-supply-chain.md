---
name: gha-security-scanning-supply-chain
description: "Use when: (1) adding CodeQL SAST to TypeScript/JavaScript workflows or Semgrep/Gitleaks to any PR pipeline, (2) CI security scans only trigger on push to main — not PRs — and need promotion to PR gates, (3) Gitleaks SARIF parsing uses grep instead of jq causing always-fail required checks, (4) enforcing pinned SHA-based action versions instead of mutable tags, (5) auditing or porting curl|bash installers with SHA-256 verification, (6) a GHA job fails at 'Set up job' due to unresolved transitive action dependency, (7) adding Bandit SAST as a required CI check for Python/pixi projects, (8) triaging and remediating CodeQL PR alerts when gh reports a check-run id instead of a workflow run id, (9) planning a SARIF -> GitHub Code Scanning (Security tab) upload via upload-sarif (gitleaks/trivy/codeql) and need a planning-stage verification checklist."
category: ci-cd
date: 2026-06-19
version: "1.4.0"
user-invocable: false
history: gha-security-scanning-supply-chain.history
verification: verified-local
tags:
  - codeql
  - code-scanning
  - semgrep
  - gitleaks
  - sarif
  - sast
  - secrets-scanning
  - dependency-scanning
  - pip-audit
  - npm-audit
  - dependabot
  - supply-chain
  - sha-pinning
  - curl-bash
  - installer
  - sha256-verification
  - github-actions
  - trivy
  - pixi
  - dockerfile
  - bandit
  - python-sast
  - nosec
  - weak-hashing
  - command-injection
  - upload-sarif
  - code-scanning-upload
  - security-tab
  - if-always
  - least-privilege
  - planning
---

# GitHub Actions Security Scanning and Supply-Chain Hardening

## Overview

| Field | Value |
|-------|-------|
| Date | 2026-06-19 |
| Objective | Set up security scanning (CodeQL/Semgrep/Gitleaks SAST + secrets + Bandit Python SAST), harden CI supply-chain (action SHA pinning, dependency scanning), and pin/verify curl\|bash installers with SHA-256 |
| Outcome | Consolidated guidance for security gate setup, scan-trigger gaps, SARIF parsing fixes, action SHA pinning, transitive-pin diagnosis, installer trust-model hardening, Bandit SAST integration for Python/pixi projects, CodeQL PR alert remediation, and planning-stage verification for SARIF -> GitHub Code Scanning (Security tab) uploads via `upload-sarif` |
| Verification | verified-local |

## When to Use

- Setting up CodeQL SAST for the first time in a TypeScript/JavaScript project, or adding Semgrep/Gitleaks to a PR pipeline
- Security scans only trigger on `push: branches: [main]` — not on PRs (pre-merge gates are missing)
- `continue-on-error: true` on a Semgrep or Gitleaks scan step masks real failures
- Gitleaks SARIF parsing uses POSIX `grep` instead of `jq`, causing a required check to always fail
- A `security-report` required check never passes, blocking all PR auto-merges
- GitHub Actions `uses:` references use mutable tags (`@v8`, `@v0.9.4`) instead of pinned commit SHAs
- A Dockerfile/workflow installs tools via unverifiable `curl|sh`, npm, or pixi without a version pin
- A GHA job fails at "Set up job" with `Unable to resolve action` for a transitive dependency you do not reference
- Adding `curl|bash` installers, or porting/hardening existing ones with SHA-256 verification and multi-platform support
- Adding automated dependency vulnerability scanning (pip-audit/npm audit + Dependabot)
- Isolating `security-events: write` permission from base required checks
- Adding Bandit SAST as a required CI check for Python/pixi projects (medium+ severity, JSON report artifact)
- `gh pr checks` shows a failing CodeQL identifier but `gh run view` cannot find it because the
  identifier is a check-run id, not a workflow run id
- CodeQL flags weak sensitive-data hashing, command-line injection, or similar findings that need
  code fixes plus targeted regression tests
- Performing a security code review where static-analysis output is noisy with false positives
- Planning a change that uploads a scanner's SARIF output (gitleaks/trivy/codeql) to the GitHub
  Code Scanning (Security) tab via `github/codeql-action/upload-sarif`, especially when the scan
  step fails the build on findings (`--exit-code 1`)

## Verified Workflow

### Quick Reference

```bash
# Audit unpinned action refs (search ALL of .github/, not just workflows/)
grep -rn "uses:.*@v[0-9]" .github/

# Resolve action tag to commit SHA (handle lightweight + annotated tags)
RESULT=$(gh api repos/OWNER/REPO/git/ref/tags/vX.Y.Z --jq '.object | {sha,type}')
TYPE=$(echo "$RESULT" | jq -r '.type'); SHA=$(echo "$RESULT" | jq -r '.sha')
[ "$TYPE" = "tag" ] && SHA=$(gh api repos/OWNER/REPO/git/tags/$SHA --jq '.object.sha')

# Fix Gitleaks SARIF parser (replace fragile grep with jq)
jq '[.runs[].results[]] | length == 0' results.sarif | grep -q true

# Find curl|sh / wget|sh installers
grep -rn "curl\|wget" .github/workflows/*.yml | grep "|.*sh\b\|bash\b"

# Validate workflow YAML
python3 -c "import yaml; yaml.safe_load(open('.github/workflows/codeql.yml'))" && echo OK

# Inspect a failing CodeQL check-run id from gh pr checks
gh api "repos/<owner>/<repo>/check-runs/<check_run_id>" \
  --jq '{name,conclusion,details_url,html_url}'
gh api "repos/<owner>/<repo>/check-runs/<check_run_id>/annotations" --paginate
gh api "repos/<owner>/<repo>/code-scanning/alerts?pr=<pr>&tool_name=CodeQL" --paginate
```

### Detailed Steps

#### A. Security scanning setup (CodeQL SAST + npm audit + Gitleaks gate)

**CodeQL — isolate `security-events: write` in its own workflow** (least privilege; one failing job
must not block all security checks). File `.github/workflows/codeql.yml`:

```yaml
name: CodeQL
on:
  push: { branches: [main] }
  pull_request: { branches: [main] }
  schedule:
    - cron: "27 3 * * 2"   # weekly, off-peak
permissions:
  contents: read
  security-events: write
jobs:
  analyze:
    runs-on: ubuntu-latest
    timeout-minutes: 360
    strategy:
      fail-fast: false
      matrix:
        language: ["typescript"]
    steps:
      - uses: actions/checkout@a5ac7e51b41094c7467395007f7e897ffd472b1c  # v4.1.6
      - uses: github/codeql-action/init@4e828ff8a76ab34a99dd1f01ba9ca34eb10ebddad  # v3.27.5
        with:
          languages: ${{ matrix.language }}
          queries: security-extended,security-and-quality
      - uses: github/codeql-action/autobuild@4e828ff8a76ab34a99dd1f01ba9ca34eb10ebddad  # v3.27.5
      - uses: github/codeql-action/analyze@4e828ff8a76ab34a99dd1f01ba9ca34eb10ebddad  # v3.27.5
        with:
          category: "/language:typescript"
```

**npm audit — production-only, advisory job** in the base required-checks workflow:

```yaml
  security-audit:
    runs-on: ubuntu-latest
    timeout-minutes: 10
    steps:
      - uses: actions/checkout@a5ac7e51b41094c7467395007f7e897ffd472b1c  # v4.1.6
      - uses: actions/setup-node@60edb5dd545a775178fac7f3a11fc4209779e326  # v4.0.2
        with: { node-version: "20", cache: "npm" }
      - run: npm ci
      - run: npm audit --omit=dev --audit-level=high
```

`--omit=dev` drops dev-only CVEs (typescript, ts-node); `--audit-level=high` cuts low/moderate noise.
Keep it a separate job so pre-existing transitive CVEs (e.g. `@dagger.io/dagger` → protobufjs/uuid)
are observable without blocking the pipeline.

**Gitleaks — PR-gated, main advisory** (direct binary install for conditional `--exit-code`):

```yaml
  security-scan:
    runs-on: ubuntu-latest
    timeout-minutes: 10
    steps:
      - uses: actions/checkout@a5ac7e51b41094c7467395007f7e897ffd472b1c  # v4.1.6
        with: { fetch-depth: 0 }   # full history for git-log scanning
      - name: Run Gitleaks scan
        run: |
          set -euo pipefail
          VERSION="v8.30.1"
          wget -q "https://github.com/gitleaks/gitleaks/releases/download/${VERSION}/gitleaks_${VERSION#v}_linux_x64.tar.gz"
          echo "79a3ab579b53f71efd634f3aaf7e04a0fa0cf206b7ed434638d1547a2470a66e  gitleaks_${VERSION#v}_linux_x64.tar.gz" | sha256sum --check
          tar -xzf "gitleaks_${VERSION#v}_linux_x64.tar.gz"
          # PR gates (exit 1); main is advisory (exit 0). Keep this comment so the
          # conditional is not removed by future maintainers.
          EXIT_CODE=0
          [ "${{ github.event_name }}" == "pull_request" ] && EXIT_CODE=1
          ./gitleaks detect --source=. --verbose --exit-code="$EXIT_CODE"
```

The `gitleaks/gitleaks-action` wrapper does NOT expose conditional `--exit-code`; use the direct
binary. Always SHA-256-verify the download. Omit `--no-git` so the full branch history is scanned.

#### A2. Upload scanner SARIF to GitHub Code Scanning (Security tab) — planning checklist

When planning a change that pipes a scanner's SARIF output into the GitHub Code Scanning / Security
tab via `github/codeql-action/upload-sarif`, verify these before writing the workflow. This list was
built from a plan-only review (read the workflow, did not run actionlint or execute CI) — treat each
item as something to CONFIRM, not assume.

```yaml
# Target shape for a gitleaks SARIF -> Security tab upload, in a job that runs untrusted
# repo content (the scan). security-events: write is scoped to THIS job, not workflow-wide.
gitleaks-scan:
  runs-on: ubuntu-latest
  permissions:
    contents: read
    security-events: write   # per-job, mirror an existing least-privilege job in the same repo
  steps:
    - uses: actions/checkout@<SHA>  # v4
    - name: Run gitleaks (fails build on findings)
      run: ./gitleaks detect --source=. --report-format sarif --report-path gitleaks.sarif --exit-code 1
    - name: Upload gitleaks SARIF to code scanning
      # LOAD-BEARING: the scan step uses --exit-code 1, so without `if: always()` this step is
      # SKIPPED exactly when there ARE findings — the Security tab would then never receive them.
      if: always() && hashFiles('gitleaks.sarif') != ''
      uses: github/codeql-action/upload-sarif@<repo-existing-SHA>  # reuse the SHA already pinned in-repo
      with:
        sarif_file: gitleaks.sarif
        category: gitleaks   # keep findings distinct from CodeQL/Trivy in the same tab
```

**Planning-stage verification checklist (confirm each before/at implementation):**

1. **`if: always()` is load-bearing when the scan uses `--exit-code 1`.** A SARIF scan that fails the
   build on findings will SKIP every later step unless that step uses `if: always()`. The upload-sarif
   step MUST be `if: always() && hashFiles('<file>.sarif') != ''`, otherwise findings never reach the
   Security tab *precisely when there are findings*. This is the single highest-risk assumption — verify
   it first.
2. **`security-events: write` must be scoped per-job, not workflow-wide.** When a job runs untrusted
   repo content (a scan), elevating the whole workflow leaks the write scope to every job. Mirror an
   existing least-privilege job in the same repo as the pattern source rather than hoisting the
   permission to the top level.
3. **Reuse the `codeql-action` SHA already pinned elsewhere in the same repo** (e.g. an existing
   `init`/`analyze` step) instead of introducing a new pin or a mutable `@v3` tag — one auditable SHA
   across the repo. Confirm the SHA maps to a real release; do not trust a copied comment blindly.
4. **`category:` keeps tool findings distinct** (e.g. `category: gitleaks`) so gitleaks alerts do not
   collide with CodeQL/Trivy alerts in the same Security tab.

**Confirm-don't-assume list (each of these was unverified at plan time and a reviewer should check):**

- Line numbers cited in a plan (read directly from the file) do NOT equal actionlint/CI verification.
  A plan that only reads the workflow stays `verified-local` at best — never claim `verified-ci` until
  the modified workflow actually runs in CI.
- A `codeql-action` SHA copied from another workflow step (e.g. `sanitizers.yml`) is trusted to map to
  the commented release tag, but verify it against GitHub's tag:
  `gh api repos/github/codeql-action/git/refs/tags/<tag> -q '.object.sha'`.
- `upload-sarif` resolving a relative `sarif_file:` from the workspace root is the expected behavior
  (consistent with how artifact steps reference the same path), but confirm against the action docs if
  the file lives outside the workspace root.
- The `actions/upload-artifact` major version assumed "already in the repo" may be stale — re-confirm
  the actual pinned major before reusing it (`@v7` does not exist; latest is v4/v5).

#### B. Close scan-trigger / masking gaps in existing workflows

**Add a PR trigger** so security runs pre-merge, not only after:

```yaml
on:
  pull_request:
  push: { branches: [main] }
  workflow_dispatch:
```

**Remove `continue-on-error` from scan steps only** — keep it on SARIF upload/artifact/reporting
steps. Removing it from upload steps silently breaks reporting.

#### C. Fix Gitleaks SARIF false-positive blocking a required check

Two bugs make `security-report` always fail:

```bash
# Bug 1 — POSIX grep \s is literal backslash-s, never matches even an empty array.
# WRONG:  grep -q '"results":\s*\[\]' results.sarif
# RIGHT:  jq '[.runs[].results[]] | length == 0' results.sarif | grep -q true

# Bug 2 — a bare ❌ gate catches false positives from Bug 1.
# WRONG:  grep -q "❌" report.md
# RIGHT:  ! grep -qE "^- ❌ Secret Scanning:|^- ❌ Docker Image Scanning:" report.md
```

Fix `.gitleaks.toml` for v8 — single-bracket `[allowlist]` (a map), not `[[rules.allowlist]]`
(array-of-tables = slice → crash `'Rules[0].AllowList' expected a map, got 'slice'`):

```toml
[allowlist]
description = "Documentation and example files"
paths = ['''k8s/secrets.yaml''', '''docs/KUBERNETES_DEPLOYMENT.md''', '''tests/.*''']
```

Fix the parser first to see real findings, then add the allowlist — both in the same PR.

#### CodeQL PR alert triage and remediation

When `gh pr checks` reports a failing CodeQL identifier, do not assume it is a workflow run id.
GitHub can show a **check-run id** in the PR checks table; `gh run view <id>` will fail or inspect
the wrong object. Query the check-run and CodeQL alerts directly:

```bash
gh api "repos/<owner>/<repo>/check-runs/<check_run_id>" \
  --jq '{name,status,conclusion,started_at,completed_at,details_url,html_url}'
gh api "repos/<owner>/<repo>/check-runs/<check_run_id>/annotations" --paginate
gh api "repos/<owner>/<repo>/code-scanning/alerts?pr=<pr>&tool_name=CodeQL" --paginate
```

Read the rule id, path, line, state, and most recent instance before editing. The alerts API also
shows when older alerts are fixed while newer alerts remain open, which prevents declaring the
security gate done after only the first finding disappears.

For `py/weak-sensitive-data-hashing` on user/login identifiers:

- Replace MD5 with SHA-256 when the value is a non-secret salted tracking identifier and policy
  requires SHA-2.
- Add regression tests proving deterministic output for the same salt/input pair and a 64-character
  hexadecimal digest.
- Do **not** use bare SHA-256 for low-entropy secrets or passwords. Use a password hashing or KDF
  primitive such as Argon2, bcrypt, scrypt, or PBKDF2 according to the project's policy.

For `py/command-line-injection` around a generic subprocess wrapper:

- Reject an empty command before any subprocess call.
- Convert arguments to strings and reject any argument containing a NUL byte.
- Select executables from hard-coded literals, for example an `if`/`elif` ladder or dict allowlist
  of scheduler commands; do not pass through arbitrary `argv[0]`.
- Reconstruct the safe argv from the selected literal executable plus validated arguments, then call
  `subprocess.run`.
- Add tests proving unsupported executables are rejected before `subprocess.run` is called.

After pushing the fix, treat CodeQL and the normal validate/test job as separate gates: CodeQL can
be fixed while validate still fails for an unrelated CI-environment difference.

### Detailed Steps: scanner version bumps and pin discovery

#### Bumping a pinned scanner version

When you bump a pinned scanner binary (e.g. Gitleaks) in a security workflow, the version string,
download URL, and SHA-256 in the YAML are NOT the only places that pin lives. The test suite that
asserts the workflow is correctly pinned holds its own copy of those constants, and tests will then
silently point at the *old* hash if you forget to update them.

```bash
# 1. Find the latest stable release
gh release list --repo gitleaks/gitleaks --limit 5

# 2. Fetch the official SHA-256 (linux x64) from the release checksums file
VERSION="v8.30.1"; VER="${VERSION#v}"
curl -fsSL "https://github.com/gitleaks/gitleaks/releases/download/${VERSION}/gitleaks_${VER}_checksums.txt" \
  | grep "linux_x64.tar.gz"

# 3. Apply version + SHA update in the workflow (use sed, not Edit — pre-commit hook
#    blocks the Edit tool on .github/workflows/*.yml)
OLD="8.18.0"; NEW="8.30.1"
OLD_SHA="6e19050a3ee0688265ed3be4c46a0362487d20456ecd547e8c7328eaed3980cb"
NEW_SHA="79a3ab579b53f71efd634f3aaf7e04a0fa0cf206b7ed434638d1547a2470a66e"
sed -i \
  "s/v${OLD}/v${NEW}/g; s/gitleaks_${OLD}/gitleaks_${NEW}/g; s/${OLD_SHA}/${NEW_SHA}/g" \
  .github/workflows/security.yml

# 4. CRITICAL — also update the test constants, or the tests still assert the OLD hash:
#    GITLEAKS_VERSION, GITLEAKS_TARBALL, EXPECTED_SHA256
#    in tests/workflows/test_security_workflow.py

# 5. Verify no old strings remain anywhere (workflow AND tests)
grep -rn "${OLD}\|${OLD_SHA}" .github/workflows/security.yml tests/workflows/test_security_workflow.py
```

The version bump is only complete when both the workflow and `tests/workflows/test_security_workflow.py`
reference the new version, tarball name, and SHA-256. Step 5 must come back empty.

#### Discovering the correct pin via git history

When you need to pin a `--tag`/`--version` flag (e.g. switching a Dockerfile from
`cargo install <tool>` to `curl ... | bash -s -- --tag <ver>`) but do not know which version the
project was previously building, recover it from git history instead of guessing:

```bash
# 1. List every commit that touched the Dockerfile (--all covers branches/tags)
git log --oneline --all -- Dockerfile

# 2. Inspect the Dockerfile at the relevant commit and read the version off the
#    prior cargo install (or pip/npm) invocation
git show <commit>:Dockerfile | grep cargo
```

Use the version recovered from `cargo install` as the `--tag` pin so behavior is unchanged across
the migration. Do NOT pin to "latest" — that reintroduces the floating-version supply-chain risk.

#### D. Pin GitHub Actions to commit SHAs

Search ALL of `.github/` (composite actions under `.github/actions/*/action.yml` are frequently
missed). Resolve tags with the lightweight/annotated handling from Quick Reference, then:

```yaml
# BEFORE
uses: prefix-dev/setup-pixi@v0.9.4
# AFTER
uses: prefix-dev/setup-pixi@a0af7a228712d6121d37aba47adf55c1332c9c2e  # v0.9.4
```

Use `sed -i` (not the Edit tool) for workflow edits — pre-commit security hooks block interactive
edits of `.github/workflows/*.yml`.

#### E. Diagnose transitive action-pin failures

When a job fails at "Set up job" with `Unable to resolve action <action>@<ver>` and that action is
NOT in your workflows, the pin lives inside a wrapper/composite action:

```bash
curl -fsSL "https://raw.githubusercontent.com/aquasecurity/trivy-action/v0.30.0/action.yml" | grep -nE 'uses:'
```

**Two-strikes-and-drop:** try the latest wrapper release; if still failing, inspect that release's
`action.yml`; after 2 failures drop the step, open a tracking issue, move on. Do NOT mask with
`continue-on-error: true`.

#### F. Add dependency scanning (pip-audit + Dependabot, pixi projects)

```yaml
# .github/dependabot.yml  (zero CI-minutes; runs on GitHub infra)
version: 2
updates:
  - package-ecosystem: pip
    directory: "/"
    schedule: { interval: weekly }
```

```toml
# pixi.toml — pip-audit is PyPI-only, so use pypi-dependencies NOT dependencies
[feature.lint.pypi-dependencies]
pip-audit = ">=2.7"
```

Use a `pixi-lint-*` cache key so lint and dev caches do not collide.

#### G. Pin and verify curl|bash installers (SHA-256, multi-platform)

Reference implementation — pin versions + verify SHA-256 + portable platform/sha detection:

```bash
#!/bin/bash
set -euo pipefail

readonly PIXI_VERSION="0.34.0"
readonly PIXI_SHA256_LINUX_X86_64="fbdec98dff8b522c4ceb12d76e3fdc177b55620a33451b350c94eae37b3803c8"
readonly PIXI_SHA256_LINUX_AARCH64="037f2513419127a3c19c129c9396973a146beee1231404f4f0d4699d2e3101d1"
readonly PIXI_SHA256_DARWIN_X86_64="fa44bc52aa20350cefcd00938ea2269d172c00a0de9a0159d7d80e75b3495a73"
readonly PIXI_SHA256_DARWIN_AARCH64="dc4b686d97d095687e6ef7ac0107863d1ae8a2d4d15374db9540971133f1c07d"

_sha256_cmd() {                      # Linux: sha256sum; macOS: shasum -a 256
    if command -v sha256sum >/dev/null 2>&1; then echo "sha256sum"
    elif command -v shasum >/dev/null 2>&1; then echo "shasum -a 256"
    else return 1; fi
}

_detect_platform() {                 # NOTE: Darwin reports arm64; normalize to aarch64
    case "$(uname -s):$(uname -m)" in
        Linux:x86_64)  echo "linux-x86_64"   ;;
        Linux:aarch64) echo "linux-aarch64"  ;;
        Darwin:x86_64) echo "darwin-x86_64"  ;;
        Darwin:arm64)  echo "darwin-aarch64" ;;
        *) return 1 ;;
    esac
}

download_and_verify() {              # args: expected_sha url out
    local expected_sha="$1" url="$2" out="$3" sha_cmd actual
    sha_cmd="$(_sha256_cmd)" || { echo "ERROR: no sha256 available" >&2; return 2; }
    curl --proto '=https' --tlsv1.2 -fsSL -o "$out" "$url" || return 1
    actual="$($sha_cmd "$out" | awk '{print $1}')"   # string-compare, not --check (portable)
    if [ "$actual" != "$expected_sha" ]; then
        echo "ERROR: SHA-256 mismatch for $out" >&2; rm -f "$out"; return 1
    fi
}

# Replace `curl https://get.pixi.sh | bash` with:
download_and_verify "$PIXI_SHA256_LINUX_X86_64" \
  "https://github.com/prefix-dev/pixi/releases/download/v${PIXI_VERSION}/pixi-${PIXI_VERSION}-linux-x86_64.tar.gz" \
  /tmp/pixi.tar.gz
tar -xzf /tmp/pixi.tar.gz -C /opt/pixi && rm -f /tmp/pixi.tar.gz
```

For tools that cannot be pinned without breaking usability, document a TRUST MODEL inline (tool +
issue ref + built-in integrity mechanism + trust root):

```bash
# TRUST MODEL — npm/claude-code: npm verifies SHA-512 on every install.
# Trust root: registry.npmjs.org TLS + npm signed metadata.
npm install -g --save-exact @anthropic-ai/claude-code@2.1.42
```

Fail fast (print manual URL + `exit 1`) on unsupported distros instead of silently falling back to
`curl|sh`. For tools with a version flag, pin it: `just` → `--tag 1.14.0`; Dockerfile npm →
`npm install -g <pkg>@X.Y.Z`. Test the security property functionally: call `download_and_verify`
with a wrong hash and assert non-zero exit + file cleanup.

#### I. Add Bandit SAST as a required CI check (Python/pixi projects)

Bandit writes the JSON report **before** exiting non-zero on findings. The exit propagates to the
step (failing the job), while the artifact remains on disk. Use a single invocation — no `|| true`,
no duplicate scan.

```yaml
security-sast-scan:
  name: security/sast-scan
  runs-on: ubuntu-24.04
  steps:
    - uses: actions/checkout@<SHA>  # v4
    - uses: prefix-dev/setup-pixi@<SHA>  # v0.9.x
      with:
        pixi-version: v0.67.2
        cache: true
    - name: Run Bandit SAST scan (medium+ severity, emit JSON report)
      run: pixi run python -m bandit -ll --ini .bandit -r src/<pkg> -f json -o bandit.json
    - name: Upload Bandit JSON report
      if: always() && hashFiles('bandit.json') != ''
      uses: actions/upload-artifact@330a01c490aca151604b8cf639adc76d48f6c5d4  # v5.0.0
      with:
        name: bandit-report
        path: bandit.json
        retention-days: 90
```

Key decisions:

- **`if: always() && hashFiles('bandit.json') != ''`** — preserves triage data on both pass and fail.
- **`pixi run python -m bandit`** — invoke via `python -m bandit` rather than `pixi run bandit` when
  adding flags beyond what the pixi task embeds (see Failed Attempts).
- **`actions/upload-artifact@v5.0.0`** — pin to full SHA. `@v7` does not exist on GitHub.com.
  Verify any tag with: `gh api repos/actions/upload-artifact/git/refs/tags/v5.0.0 -q '.object.sha'`
- **`.bandit` INI** — start with no `skips` list. Only add skips when a real finding requires it
  (YAGNI). Do NOT pre-emptively skip B101 (assert_used).
- **Inline `# nosec`** for real false positives — prefer site-specific suppression over widening
  the global `skips` list. Include the rule ID and one-line rationale:
  ```python
  working_dir: str = "/tmp"  # nosec B108 — ephemeral agent working directory
  ```

When adding a new package under `src/<name>/`, also update the `-r` target in the `bandit` task in
`pixi.toml` and the `files:` regex in `.pre-commit-config.yaml`.

#### H. Security code review with false-positive filtering

Two-phase agents: Phase 1 (single agent) lists candidates with confidence 1-10, surfacing only ≥7
and excluding DoS/secrets-on-disk/rate-limiting/memory-safety/test-only/regex-injection. Phase 2
(one agent per finding) validates real exploitability from untrusted input. Report only confidence
≥8 AND TRUE POSITIVE; otherwise output `No security vulnerabilities identified above the confidence
threshold.`

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Combined all scanners in one workflow | CodeQL + npm audit + Gitleaks in a single workflow | One failing job blocks all checks; `security-events:write` leaks to other steps | Isolate CodeQL (privileged) in its own workflow; per-job scope the rest |
| Single-workflow grep for unpinned tags | Searched only `.github/workflows/` | Missed composite actions under `.github/actions/` | Scope grep to ALL of `.github/` |
| Removed all `continue-on-error` | Stripped it from every security step | SARIF upload/artifact steps legitimately need it; reporting breaks | Only remove it from scan steps, never from upload/reporting |
| POSIX grep on SARIF | `grep -q '"results":\s*\[\]'` | `\s` is literal backslash-s; never matches | Use `jq` for JSON/SARIF; never POSIX grep on structured data |
| Bare ❌ failure gate | `grep -q "❌" report.md` | Any ❌ anywhere (incl. parser false positives) fails the check | Gate on specific line prefixes `^- ❌ Secret Scanning:` |
| Parser fix without allowlist | Fixed SARIF parser but no `.gitleaks.toml` allowlist | Parser then correctly reports findings in docs/k8s placeholders | Fix parser first to see real findings, then add allowlist in same PR |
| `[[rules.allowlist]]` in gitleaks v8 | Double-bracket TOML | Array-of-tables = slice; v8 expects a map → crash | Use single `[allowlist]` at top level |
| Edit tool on workflow YAML | Edited `.github/workflows/*.yml` | Pre-commit security hook blocks the Edit tool | Use `sed -i` for workflow edits |
| Gitleaks `--exit-code 1` on all branches | Gated main pushes too | Violates #86 runbook; pre-commit already covers local | Conditional exit code: gate PRs, keep main advisory |
| `gitleaks/gitleaks-action` wrapper | Used the action wrapper | Does not support conditional `--exit-code` | Use direct binary install for full flag control |
| `--no-git` / `--log-opts=HEAD~1..HEAD` | Limited Gitleaks to working dir / PR diff | Misses secrets in prior branch commits | Default full git-log mode with `fetch-depth: 0` |
| npm audit without `--omit=dev` | Default scope | Dev-only transitive CVEs fail PRs; not code-quality issues | `--omit=dev --audit-level=high` for production-only, actionable risk |
| `[feature.lint.dependencies]` for pip-audit | Put PyPI-only pkg in conda deps | pip-audit is PyPI-only | Use `[feature.ENV.pypi-dependencies]` |
| Re-pinning `trivy-action` 3 times | Repeatedly re-pinned a broken transitive | Internal setup-trivy missing; wrong tag format; downstream OOM | Two-strikes-and-drop: drop step + file tracking issue |
| Placeholder SHA hashes | Shipped `<fill from GitHub>` placeholders | Blocks review; unresolved at impl time | Fetch real hashes first; regression-test `^[0-9a-f]{64}$` |
| Hardcoded `sha256sum` | No fallback | macOS lacks GNU coreutils (uses `shasum`) | Runtime-detect via `_sha256_cmd()` |
| `sha256sum --check` reliance | Used `--check` flag | Output spacing varies across tools | Extract with `awk '{print $1}'` and string-compare |
| Unnormalized uname platform | Used raw `uname -m` | Apple Silicon returns `arm64`, not `aarch64`; lookup fails | Normalize `arm64`→`aarch64` at detection |
| Silent curl\|sh distro fallback | Fell back to curl\|sh on unsupported distro | Silent security downgrade with no signal | Fail fast: print manual URL + exit 1 |
| String-only security tests | Tested for `download_and_verify` text only | Function never validated end-to-end | Functional test: call with bad hash, assert non-zero exit + cleanup |
| NATS as verification reference | Modeled after NATS installer | NATS pins versions but does NOT verify SHA-256 | gitleaks CI step is the real reference (download + verify + run) |
| Single-agent identify+filter review | One agent does both phases | Anchors on its own Phase 1 output | Separate identification from validation with independent agents |
| Bumped Gitleaks version in workflow only | Updated version/URL/SHA in `security.yml` but not the tests | `test_security_workflow.py` still asserted the OLD `EXPECTED_SHA256`, so tests pointed at the stale hash | On a scanner version bump also update `GITLEAKS_VERSION`, `GITLEAKS_TARBALL`, `EXPECTED_SHA256` in `tests/workflows/test_security_workflow.py` |
| Guessed the `--tag` pin version | Picked a plausible recent version when migrating Dockerfile off `cargo install` | Wrong version changed tool behavior across the migration | Recover the exact prior version from git history: `git log --oneline --all -- Dockerfile` then `git show COMMIT:Dockerfile \| grep cargo` |
| Pixi task with embedded args + extra CLI args | `bandit = "bandit -ll --ini .bandit -r src/telemachy"` invoked as `pixi run bandit -f json -o bandit.json` | Arg doubling: `bandit: error: unrecognized arguments: src/telemachy` | Use `pixi run python -m bandit -ll --ini .bandit -r src/<pkg>` for invocations that need extra flags; keep pixi task as a bare entry point or omit extra flags at call site |
| Pre-emptive skip of B101 in `.bandit` | Added `skips = B101` before any asserts existed in `src/` | YAGNI — adds a suppression rule with zero benefit; flagged in review | Start `.bandit` with no `skips`; only add suppressions when an actual finding requires it |
| `actions/upload-artifact@v7` | Pinned upload artifact action to `@v7` | Tag `v7` does not exist on GitHub.com (latest is v4/v5); workflow fails at "Set up job" | Pin to full SHA for v5.0.0: `actions/upload-artifact@330a01c490aca151604b8cf639adc76d48f6c5d4 # v5.0.0`; verify tags with `gh api repos/actions/upload-artifact/git/refs/tags/v5.0.0 -q '.object.sha'` |
| Global `.bandit` skip for false positive | Widened `skips = B108` for a single hardcoded `/tmp` default | Suppresses B108 globally across all files; any future real hardcoded path would be silently missed | Use inline `# nosec B108 — ephemeral agent working directory` at the specific site only |
| Treating a CodeQL check-run id as a workflow run id | Ran `gh run view <check_run_id>` from the value shown by `gh pr checks` | The id belonged to a check-run, so the workflow-run API did not expose the alert details | Use `gh api repos/<owner>/<repo>/check-runs/<check_run_id>` and the matching annotations/alerts APIs |
| Hash replacement without data classification | Replaced MD5 mechanically without deciding whether the material was a tracking id or a password/secret | SHA-256 is acceptable for non-secret salted IDs under SHA-2 policy, but not for low-entropy secrets | Classify the data first: SHA-256 for salted non-secret identifiers, password hashing/KDF for secrets |
| Sanitizing a generic subprocess wrapper after command selection | Validated argument strings but still accepted arbitrary executables | CodeQL still had a path from caller-controlled command names to `subprocess.run` | Choose the executable from a hard-coded allowlist before reconstructing argv |
| Omitting `if: always()` on upload-sarif when scan uses `--exit-code 1` | Added an `upload-sarif` step after a gitleaks step that exits 1 on findings, with no `if:` guard | The scan step fails the job on findings, so the upload step is SKIPPED exactly when there ARE findings — the Security tab silently receives nothing | Always use `if: always() && hashFiles('<file>.sarif') != ''` on the upload-sarif step so findings reach the tab even when the scan fails the build |
| Elevating `security-events: write` workflow-wide | Set `security-events: write` at the top-level workflow `permissions` instead of on the scan job | The scan job runs untrusted repo content, so workflow-wide elevation leaks the write scope to every other job | Scope `security-events: write` per-job on the scan job only; mirror an existing least-privilege job in the same repo as the pattern source |
| Mutable `@v3` tag for codeql-action upload-sarif | Pinned `github/codeql-action/upload-sarif@v3` instead of reusing the repo's existing pinned SHA | Reintroduces a floating-version supply-chain risk and creates a second, divergent codeql-action reference in the same repo | Reuse the exact `codeql-action` SHA already pinned elsewhere in the repo (e.g. its `init`/`analyze` steps); verify with `gh api repos/github/codeql-action/git/refs/tags/<tag> -q '.object.sha'` |

## Results & Parameters

### Gitleaks version reference

| Field | Value |
|-------|-------|
| Version (latest stable) | v8.30.1 (2026-06-03) / v8.30.0 (2026-03-15) |
| linux_x64 SHA256 | `79a3ab579b53f71efd634f3aaf7e04a0fa0cf206b7ed434638d1547a2470a66e` |
| Checksums URL | `https://github.com/gitleaks/gitleaks/releases/download/<VER>/gitleaks_<ver>_checksums.txt` |
| Exit code (PR / main) | 1 (gate) / 0 (advisory) |
| Scan mode | full git history (`fetch-depth: 0`, no `--no-git`) |

### Action SHA reference

| Action | Version | Commit SHA |
|--------|---------|------------|
| `actions/checkout` | v4.1.6 | `a5ac7e51b41094c7467395007f7e897ffd472b1c` |
| `actions/setup-node` | v4.0.2 | `60edb5dd545a775178fac7f3a11fc4209779e326` |
| `github/codeql-action/*` | v3.27.5 | `4e828ff8a76ab34a99dd1f01ba9ca34eb10ebddad` |
| `prefix-dev/setup-pixi` | v0.9.4 | `a0af7a228712d6121d37aba47adf55c1332c9c2e` |
| `actions/github-script` | v8 | `ed597411d8f924073f98dfc5c65a23a2325f34cd` |
| `actions/upload-artifact` | v5.0.0 | `330a01c490aca151604b8cf639adc76d48f6c5d4` |

### CodeQL / npm audit configuration

| Setting | Value | Reason |
|---------|-------|--------|
| CodeQL queries | `security-extended,security-and-quality` | Security + quality coverage |
| CodeQL workflow | isolated `codeql.yml` | Scope `security-events: write` |
| npm audit flags | `--omit=dev --audit-level=high` | Production-only, actionable CVEs |
| Node install | `npm ci` (v20) | Locked, reproducible |

### CodeQL PR remediation reference

| Finding | Preferred pattern | Regression test |
|---------|-------------------|-----------------|
| Check-run id from `gh pr checks` | Query `check-runs/<check_run_id>`, `check-runs/<check_run_id>/annotations`, and `code-scanning/alerts?pr=<pr>&tool_name=CodeQL` | Confirm rule id, path, line, and open/fixed state before editing |
| Weak hashing for non-secret salted IDs | Replace MD5 with SHA-256 when policy requires SHA-2 | Same salt/input is deterministic; digest length is 64 hex characters |
| Low-entropy secret/password hashing | Use a password hashing/KDF primitive, not bare SHA-256 | Verify project-approved parameters and migration behavior |
| Command-line injection in subprocess wrapper | Select executable from a hard-coded allowlist, validate args, reject NUL bytes, reconstruct argv | Unsupported executable is rejected before `subprocess.run` is called |

### Installer SHA-256 values (verified from GitHub releases)

```
pixi   v0.34.0 linux-x86_64:   fbdec98dff8b522c4ceb12d76e3fdc177b55620a33451b350c94eae37b3803c8
pixi   v0.34.0 darwin-aarch64: dc4b686d97d095687e6ef7ac0107863d1ae8a2d4d15374db9540971133f1c07d
dagger v0.13.3 linux-x86_64:   787307925b10c0b9b04c0fd814716abe339c53b6aa250a8ba25321a934d14a67
just   v1.36.0 linux-x86_64:   bc7c9f377944f8de9cd0418b11d2955adebfa25a488c0b5e3dd2d2c0e9d732da
```

### Installer version flags by tool

| Tool | Version flag | Example |
|------|-------------|---------|
| `just` | `--tag` | `--tag 1.14.0` |
| `pixi` | env `PIXI_VERSION` | `PIXI_VERSION=0.65.0 curl ... \| bash` |
| `rustup` | `--default-toolchain` | `--default-toolchain 1.75.0` |

### Bandit configuration reference

| Setting | Value | Reason |
|---------|-------|--------|
| Severity threshold | `-ll` (medium+) | Low-severity findings are noise in most projects |
| Report format (CI) | `-f json -o bandit.json` | Machine-readable; upload as artifact; parseable on pass AND fail |
| INI file | `--ini .bandit` | Centralizes config; scoped to project `targets` + `skips` |
| Initial `skips` list | *(empty)* | YAGNI — only add when a real finding requires suppression |
| False-positive suppression | `# nosec B<ID>  # <rationale>` inline | Site-specific; auditable; `.bandit` skips stay clean |
| Pixi invocation (bare task) | `pixi run bandit` | Only when the pixi task embeds all needed flags |
| Pixi invocation (extra flags) | `pixi run python -m bandit -ll --ini .bandit -r src/<pkg>` | Use when adding `-f`, `-o`, or other flags beyond the task default |
| Artifact upload condition | `if: always() && hashFiles('bandit.json') != ''` | Preserves triage data on both pass and fail |
| Artifact retention | `retention-days: 90` | Sufficient for triage; keeps storage low |

### jq command reference (SARIF)

```bash
jq '[.runs[].results[]] | length == 0' results.sarif   # zero results?
jq '[.runs[].results[]] | length' results.sarif        # count findings
jq '[.runs[].results[].ruleId] | unique' results.sarif # rule IDs
```

### Transitive pin reference

| Pinned version | Result |
|----------------|--------|
| `aquasecurity/trivy-action@v0.30.0` | Fails: internal setup-trivy@v0.2.2 missing |
| `aquasecurity/trivy-action@0.19.0` | Fails: tag missing (no leading v) |
| Drop step + open tracking issue | Unblocked; correct call |

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectProteus | Issue #23 — CodeQL + npm audit + PR-gated Gitleaks | merged 2026-06-03, auto-merge |
| ProjectHephaestus | Issue #744, PR #935 — installer SHA-256 pinning (pixi/dagger/just) | 13 regression + 47 shell tests passing |
| ProjectOdyssey | Issue #3143, PR #3315 — security scan gap fixes | scan triggers + masking |
| ProjectOdyssey | Issue #3939, PR #4835 — Gitleaks version upgrade | version + SHA |
| ProjectOdyssey | Issue #3342, PR #3971 — composite action SHA pinning | full `.github/` scope |
| ProjectOdyssey | Issue #3941, PR #4837 — curl\|sh → pixi replacement | supply-chain |
| ProjectScylla | Issue #650, PR #717 — npm Dockerfile pinning | exact-version pins |
| ProjectKeystone | PR #451 — Gitleaks SARIF false-positive fix | jq parser |
| ProjectOdyssey | Issue #755, PR #869 — pip-audit + Dependabot | dependency scanning |
| ProjectAgamemnon | PR #400 — transitive trivy pin failure | two-strikes-and-drop |
| ProjectTelemachy | Issue #157 — Bandit SAST as required CI check (pixi project, `_required.yml`) | verified-local (2026-06-19) |
| Sanitized PR session | CodeQL weak hashing + command injection remediation after a rebase | verified-ci (2026-06-19): CodeQL and validate gates green |
| ProjectAgamemnon | Issue #269 — plan to upload gitleaks SARIF to the Code Scanning tab in `_required.yml` | verified-local (2026-06-19): plan-only — workflow read directly, NOT run through actionlint/CI; planning-stage `upload-sarif` checklist captured |
