---
name: ci-github-actions-secrets-context-unavailable-job-if
description: "Fix actionlint error: context 'secrets' is not allowed here — available contexts are github, inputs, needs, vars. Use when: (1) job-level if: condition references secrets.SOME_SECRET, (2) you want to skip a job when a secret is absent, (3) actionlint rejects the workflow with 'context secrets is not allowed here'."
category: ci-cd
date: 2026-04-28
version: "1.0.0"
user-invocable: false
verification: verified-local
tags: [github-actions, secrets, vars, actionlint, job-if, context]
---

# GitHub Actions: secrets Context Unavailable in Job-Level if:

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-04-28 |
| **Objective** | Gate a CI job on the presence of a secret (e.g. skip deploy when AGAMEMNON_URL is not set) |
| **Outcome** | Successful — switched from `secrets.AGAMEMNON_URL` to `vars.AGAMEMNON_URL` (repository variable) for the job-level gate; secret value passed via `env:` as always |
| **Verification** | verified-local — actionlint passes after fix |

## When to Use

- actionlint reports: `context "secrets" is not allowed here. available contexts are "github", "inputs", "needs", "vars"`
- A job `if:` condition checks `secrets.SOME_SECRET != ''` to conditionally skip the job
- You want to make a deploy/apply job a no-op when credentials aren't configured
- Upgrading a workflow to satisfy actionlint checks

## Verified Workflow

### Quick Reference

```yaml
# WRONG — secrets context not available in job-level if:
jobs:
  deploy:
    if: ${{ secrets.MY_SECRET != '' }}
    env:
      MY_SECRET: ${{ secrets.MY_SECRET }}

# CORRECT OPTION A — use vars (repository variable) for the gate
# URL/non-sensitive config → repository variable; key/token → repository secret
jobs:
  deploy:
    if: ${{ vars.DEPLOY_URL != '' }}
    env:
      DEPLOY_URL: ${{ vars.DEPLOY_URL }}
      API_KEY: ${{ secrets.API_KEY }}
```

### Detailed Steps

1. Identify what you're gating on. Ask: is this value sensitive?
   - **URL / hostname / flag** (not sensitive) → use a **repository variable** (`vars.X`); variables ARE allowed in job-level `if:`
   - **API key / token / password** (sensitive) → cannot gate on it in `if:`; use a step-level workaround (see below)

2. **Option A — Repository variable gate** (preferred for non-sensitive values):
   - Go to repo **Settings → Variables → Actions** and add `MY_URL` as a repository variable
   - In workflow: `if: ${{ vars.MY_URL != '' }}`
   - Still pass the actual secret via `env:` for the steps that need it:
     ```yaml
     if: ${{ vars.AGAMEMNON_URL != '' }}
     env:
       AGAMEMNON_URL: ${{ vars.AGAMEMNON_URL }}
       AGAMEMNON_API_KEY: ${{ secrets.AGAMEMNON_API_KEY }}
     ```

3. **Option B — Step-level gate for sensitive secrets** (when you can't use vars):
   - Run a `check-secret` step that sets an output, then `if: steps.check.outputs.has-secret == 'true'` on subsequent steps:
     ```yaml
     steps:
       - name: Check secret presence
         id: check
         run: |
           if [[ -n "${{ secrets.MY_SECRET }}" ]]; then
             echo "has-secret=true" >> "$GITHUB_OUTPUT"
           fi
       - name: Deploy
         if: steps.check.outputs.has-secret == 'true'
         run: ./deploy.sh
     ```
   - Note: this approach does NOT skip the whole job — just the downstream steps.

4. Document the split in a comment so future maintainers don't revert to secrets in `if:`:
   ```yaml
   # Gate on vars.AGAMEMNON_URL (repository variable, not secret) — the URL
   # is not sensitive and secrets context is unavailable in job-level if:.
   # Set AGAMEMNON_URL as a repository *variable* (Settings > Variables) and
   # AGAMEMNON_API_KEY as a repository *secret* to enable reconciliation.
   if: ${{ vars.AGAMEMNON_URL != '' }}
   ```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| `if: ${{ secrets.AGAMEMNON_URL != '' }}` | Gate deploy job on secret presence | actionlint error: `context "secrets" is not allowed here. available contexts are "github", "inputs", "needs", "vars"` | `secrets` context is only available in `env:` and `with:` — not in `if:` at job level |
| `if: ${{ secrets.AGAMEMNON_URL }}` (truthy check, no `!= ''`) | Shorter form | Same actionlint error — context restriction applies regardless of expression form | Use `vars` for the gate; pass secret via `env:` |

## Results & Parameters

**Exact actionlint error message**:
```
.github/workflows/apply.yml:22:13: context "secrets" is not allowed here.
available contexts are "github", "inputs", "needs", "vars".
see https://docs.github.com/en/actions/learn-github-actions/contexts#context-availability
```

**GitHub Actions context availability table** (relevant subset):

| Context | Job `if:` | Step `if:` | `env:` | `with:` |
|---------|-----------|------------|--------|---------|
| `github` | yes | yes | yes | yes |
| `vars` | yes | yes | yes | yes |
| `secrets` | no | no | yes | yes |
| `needs` | yes | yes | yes | yes |

**Two-variable pattern** (URL as variable, key as secret):
- Add `AGAMEMNON_URL` to **Settings → Variables → Actions** (not Secrets)
- Keep `AGAMEMNON_API_KEY` in **Settings → Secrets → Actions**
- Workflow gates on `vars.AGAMEMNON_URL != ''`; key is passed via `env: AGAMEMNON_API_KEY: ${{ secrets.AGAMEMNON_API_KEY }}`

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| Myrmidons | fix/ci-precommit-parity — apply.yml gated on AGAMEMNON_URL presence | 2026-04-28 |
