---
name: ci-cd-karma-playwright-chromium-launcher
description: "Run Karma Angular tests in GitHub Actions with Playwright-managed Chromium instead of relying on system Chrome. Use when: (1) CI lacks a reliable Chrome binary, (2) you need deterministic Chromium setup for headless Karma jobs."
category: ci-cd
date: 2026-04-22
version: "1.0.0"
user-invocable: false
verification: verified-local
tags: [ci-cd, github-actions, playwright, karma, chromium]
---

# Karma Playwright Chromium Launcher

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-04-22 |
| **Objective** | Make GitHub Actions frontend unit tests use Playwright-installed Chromium instead of depending on system Chrome discovery. |
| **Outcome** | Successful locally. Karma continued using the Chrome launcher API, but the actual browser binary came from Playwright Chromium through `CHROME_BIN`. |
| **Verification** | verified-local |

Verified locally only — CI validation was pending during capture.

## When to Use

- An Angular/Karma workflow fails because GitHub Actions runner Chrome sandboxing or browser discovery is inconsistent.
- You want a deterministic Chromium install path in CI without depending on `google-chrome`, `chromium`, or `chromium-browser` being preinstalled.
- You need a headless Karma launcher that is clearly tied to Playwright-managed Chromium for reproducible frontend tests.

## Verified Workflow

### Quick Reference

```bash
# CI step
npm install --no-save playwright
npx playwright install --with-deps chromium

chrome_bin=$(node -e "console.log(require('playwright').chromium.executablePath())")
cat > "$RUNNER_TEMP/chrome-headless-radiance" <<'EOF'
#!/usr/bin/env bash
exec "$chrome_bin" --no-sandbox --disable-dev-shm-usage "$@"
EOF
chmod +x "$RUNNER_TEMP/chrome-headless-radiance"
echo "CHROME_BIN=$RUNNER_TEMP/chrome-headless-radiance" >> "$GITHUB_ENV"

npm test -- --watch=false --browsers=PlaywrightChromiumHeadless
```

### Detailed Steps

1. Install `playwright` in the CI job and download Chromium with `npx playwright install --with-deps chromium`.
2. Resolve the Playwright Chromium executable path from Node instead of probing system Chrome locations.
3. Wrap that executable in a small shell script that adds `--no-sandbox` and `--disable-dev-shm-usage`.
4. Export the wrapper path through `CHROME_BIN` so Karma’s Chrome launcher API uses the Playwright binary.
5. Rename the Karma custom launcher to something explicit like `PlaywrightChromiumHeadless` so the workflow contract reflects the real browser source.
6. Keep in mind that Karma logs may still say `Starting browser ChromeHeadless` because the underlying launcher implementation comes from `karma-chrome-launcher`.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| System Chrome discovery | Looked up `google-chrome`, `chromium`, or `chromium-browser` on the runner | This depends on runner image state and reintroduced exactly the environment variability the fix was trying to remove | Install and own the browser dependency inside the job |
| Keeping the old launcher contract | Left the workflow and CI contract tests pinned to `ChromeHeadless` strings | The repo’s own CI contract tests then failed even though the browser source changed correctly | Update test contracts and workflow text together when renaming CI launchers |
| Treating “Playwright” as a full Karma launcher replacement | Expected the runtime logs to stop mentioning `ChromeHeadless` entirely | Karma still uses the Chrome launcher plugin under the hood, so only the binary source changed | Distinguish between launcher API name and actual browser binary source |

## Results & Parameters

Observed stable setup:

```text
Browser provider: Playwright-installed Chromium
Karma launcher name: PlaywrightChromiumHeadless
Env var bridge: CHROME_BIN
Required flags:
- --no-sandbox
- --disable-dev-shm-usage
```

Useful validation commands:

```bash
npm test -- --watch=false --browsers=PlaywrightChromiumHeadless \
  --include src/services/radiance_run_service.spec.ts \
  --include src/components/radiance_source_input/radiance_source_input.spec.ts \
  --include src/components/visualizer/worker/graph_processor.spec.ts \
  --include src/components/visualizer/worker/graph_layout.spec.ts

pytest -q tests/backend/test_ci_contract.py
```

Expected local signal:

```text
TOTAL: 10 SUCCESS
pytest: 6 passed
```

## Verified On

| Project | Context | Details |
| --------- | --------- | --------- |
| Radiance | PR #110 rebase + frontend CI browser change | Rebased against `origin/master`, resolved workflow conflict in favor of Playwright Chromium, and updated the CI contract to match |
