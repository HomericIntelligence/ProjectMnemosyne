---
name: planning-dependent-issue-unverified-upstream
description: "Plan an issue whose dependency it builds on is unconfirmed locally — and AVOID the trap of writing 'if the dependency did X else Y' conditional fallbacks. A dependent issue's upstream is almost always ALREADY MERGED and READABLE; reading it collapses every fork into one verified fact. Use when: (1) planning an issue that depends on / blocks another issue (e.g. B adds a Dockerfile on top of A's server skeleton), (2) you are tempted to write conditional fallbacks or hardcode the upstream's module path / function signature / directory layout into your plan, (3) an issue body's code snippets reference a base image / module path / file layout created by a not-yet-read dependency, (4) the local submodule is pinned to an older SHA on a detached HEAD so the dependency's output is not in the working tree."
category: architecture
date: 2026-06-20
version: "1.1.0"
user-invocable: false
verification: unverified
history: planning-dependent-issue-unverified-upstream.history
tags:
  - planning
  - dependent-issue
  - merged-dependency
  - upstream-interface
  - verify-before-planning
  - eliminate-fallbacks
  - no-conditional-forks
  - assumptions
  - milestone
---

# Planning a Dependent Issue: Read the Merged Dependency, Eliminate the Forks

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-06-20 |
| **Objective** | Re-plan ProjectArgus issue #153 (atlas M1 Dockerfile/embed) which DEPENDS on #152 (the Go module + chi server skeleton), after the first plan got a NOGO (grade C) for forking on unverified dependency output and contingently planning cross-boundary files |
| **Outcome** | PLAN ONLY — never executed. The durable learning is a CORRECTION of prior advice: do NOT write conditional fallbacks; READ the merged dependency code (it is almost always already merged) and replace every fork with one verified path. |
| **Verification** | unverified (plan only — no docker build or CI ran; the gh/git inspection commands below WERE run and are real) |

> **Correction of prior guidance.** v1.0.0 of this skill (and the related `atlas-dashboard-dockerfile-embed-distroless` skill, ProjectMnemosyne PR #2685) advised "front-load dependency verification AND provide inline fallbacks." This session proved the *second half is a trap*: conditional fallbacks look concrete to a reviewer but encode WRONG assumptions (wrong module path, wrong base image, illegal embed location) that pass review and then fail at implementation time. The dependency is almost always already merged and readable — read it and DELETE the forks.

## When to Use

- You are planning an issue that explicitly depends on (or blocks) another issue, and the dependency's concrete output (module path, exported signatures, directory layout, existing handlers/assets) is not in your local working tree.
- You catch yourself about to write "if the dependency created X, do A; otherwise do B" — a conditional fallback — into a plan.
- The issue body's own code snippets reference a base image tag, a module path, a `//go:embed` location, or a file layout that the dependency was supposed to create. (These snippets are EXAMPLES written before the dependency merged — verify them, don't transcribe them.)
- The local submodule is pinned to an older SHA on a detached HEAD, so `find . -name '*.go'` is empty or stale — making it tempting (and wrong) to treat the dependency's interface as unknowable.

## Verified Workflow

> **Warning:** This is a planning-discipline workflow derived from a plan that was not executed end-to-end. The verification COMMANDS (gh/git inspection) were run and are real; the downstream build was not.

### Quick Reference

```bash
# 1. The dependency is almost always ALREADY MERGED. Find its PR and head branch:
gh pr list --repo HomericIntelligence/ProjectArgus --state merged \
  --search "152 in:body OR 152 in:title" \
  --json number,title,headRefName
# -> PR #160, headRefName feat/issue-152-atlas-bootstrap

# 2. Read the merged file tree DIRECTLY from the remote branch, even if the
#    local submodule is pinned to an older SHA on a detached HEAD:
cd infrastructure/ProjectArgus && git fetch origin
git ls-tree -r --name-only origin/feat/issue-152-atlas-bootstrap | grep '^dashboard/'

# 3. Read the actual files that decide your plan — do NOT guess:
git show origin/feat/issue-152-atlas-bootstrap:dashboard/go.mod        # real module path + go/toolchain version
git show origin/feat/issue-152-atlas-bootstrap:dashboard/internal/server/routes.go   # existing routes / healthz body
git show origin/feat/issue-152-atlas-bootstrap:dashboard/cmd/argus-dashboard/main.go # real server.New signature

# 4. Replace EVERY "if the dependency did X else Y" fork with ONE verified fact + ONE concrete path.
#    NO inline fallbacks. If something already exists (atlas.css, /healthz), it is OUT OF SCOPE — do not recreate it.
```

### Detailed Steps

1. **Find the merged dependency PR first.** Run `gh pr list --repo <repo> --state merged --search "<dep#> in:body OR <dep#> in:title" --json number,title,headRefName`. A dependent issue's upstream is almost always already merged; this gives you the PR number and the head branch to read.
2. **Read the merged tree from the remote branch, not the local checkout.** `git fetch origin` then `git ls-tree -r --name-only origin/<headRefName>` shows the dependency's real file layout even when the local submodule is pinned to an older SHA on a detached HEAD. The on-disk working tree is NOT evidence of what merged.
3. **Read every file your plan depends on with `git show origin/<branch>:path`.** Module path and Go/toolchain version come from `:go.mod`; existing routes/handlers from `:internal/server/routes.go`; constructor signatures from `:cmd/.../main.go`. These are facts, not the issue's prose.
4. **Replace every conditional fork with one verified path — write NO inline fallbacks.** A fallback ("create atlas.css if missing", "add /healthz if absent") looks concrete but is a guess. Reading the merged code told us atlas.css already exists (62 lines → out of scope, do NOT recreate) and /healthz already exists but returns the WRONG body (plain `"ok"` vs the required `{"status":"ok"}` JSON — a "create if missing" fallback would have missed the exists-but-wrong case entirely). One fact, one path.
5. **Verify the issue body's own code snippets against the merged code.** Issue prose is written before the dependency merges, so its base image tag, module path, and embed location are EXAMPLES. Here: the issue said `golang:1.22-alpine`, but go.mod declares `go 1.23.0` + `toolchain go1.24.2` (1.22 fails the build → must be `golang:1.24-alpine`); the issue said `//go:embed web` in `main.go`, but `web/` lives at `dashboard/web/` and main.go at `dashboard/cmd/argus-dashboard/`, and Go's `//go:embed` cannot reference parent dirs (`../../web` is illegal) — the embed file must be co-located: `dashboard/web/embed.go` (package `web`, exporting `web.Static`).
6. **Keep cross-boundary scope out.** Anything the dependency already produced (atlas.css, /healthz, a server `Assets` field) belongs to the dependency. Contingently planning to create it is P2/YAGNI scope bleed and was a MAJOR NOGO finding. The merged tree is the authority on what is already done.
7. **Label the plan `unverified` and keep the honesty gate.** The git/gh inspection commands were run and are real, but no docker build or CI ran. Mark the plan `unverified`; do not claim a build passed.

> **Heading note:** the repository validator (`scripts/validate_plugins.py`) hard-requires the literal `## Verified Workflow` heading. The COMMANDS above were genuinely run; the downstream build was not, per the warning under the heading.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| 1 | Fallback: hardcode module path `github.com/HomericIntelligence/ProjectArgus/dashboard` and the `-X version.Version=` ldflags path from it. | The REAL module (from `git show <branch>:dashboard/go.mod`) is `github.com/HomericIntelligence/atlas`; the ldflags `-X` path was wrong and the build would set nothing. | Read `:go.mod` for the module path; never derive it from the repo name or the issue prose. |
| 2 | Fallback: use builder `golang:1.22-alpine` (the issue's literal text). | go.mod declares `go 1.23.0` + `toolchain go1.24.2`; `golang:1.22` FAILS the build. | The builder base image MUST satisfy go.mod's `go`/`toolchain` directives — verify against `:go.mod`, not the issue snippet (`golang:1.24-alpine`). |
| 3 | Fallback: `//go:embed web` in `main.go` (per the issue prose). | `web/` is at `dashboard/web/` and main.go at `dashboard/cmd/argus-dashboard/`; Go's `//go:embed` cannot reference parent dirs, so `../../web` is illegal and uncompilable. | The embed file must be CO-LOCATED with the embedded dir: `dashboard/web/embed.go` (package `web`, exporting `web.Static`). Verify the layout from `git ls-tree -r <branch>`. |
| 4 | Fallback: "add the /healthz handler if it is missing." | `/healthz` already existed but returned plain text `"ok"`; the acceptance criterion required `{"status":"ok"}` JSON. The "if missing" fallback misses the exists-but-WRONG case. | Read `:routes.go`; plan to FIX the existing handler's body, not conditionally add a handler. |
| 5 | Fallback: "create a minimal atlas.css if it is missing." | `atlas.css` already existed (62 lines, produced by the dependency). Recreating it is cross-boundary scope bleed (a MAJOR NOGO finding). | What the dependency already shipped is OUT OF SCOPE; the merged tree (`git ls-tree`) is the authority — do not recreate it. |

## Results & Parameters

- **Status:** Planning-discipline methodology distilled from RE-PLANNING ProjectArgus issue #153 after a NOGO (grade C). Plan never executed; gh/git inspection commands were run and are real.
- **The trap corrected:** conditional "if the dependency did X else Y" fallbacks. They look concrete to a reviewer but encode wrong assumptions (module path, base image, embed location) that pass review and fail at implementation time.
- **The fix:** the dependency is almost always already merged — read it (`gh pr list --search`; `git ls-tree -r origin/<branch>`; `git show origin/<branch>:path`) and replace every fork with one verified fact + one concrete path. Verify the issue body's own snippets against the merged code; they are pre-merge examples.
- **Concrete commands that worked this session:** `gh pr list --repo HomericIntelligence/ProjectArgus --state merged --search "152 in:body OR 152 in:title" --json number,title,headRefName` (→ PR #160, branch `feat/issue-152-atlas-bootstrap`); `git fetch origin && git ls-tree -r --name-only origin/<branch> | grep '^dashboard/'`; `git show origin/<branch>:dashboard/go.mod` / `:routes.go` / `:main.go`.
- **NOGO findings the re-plan fixed:** (1) "stage handoff" — steps conditional on unverified dependency output handed the implementer a decision tree of forks; (2) "P2/YAGNI cross-boundary scope" — contingently planning files (atlas.css, /healthz, server Assets) that belong to the dependency.
- **Reinforced (secondary):** builder image must satisfy go.mod `go`/`toolchain`; `//go:embed` parent-path restriction; `git describe` in a Dockerfile fails when `.dockerignore` excludes `.git` (use `--build-arg VERSION`).
- **Companion skill:** `atlas-dashboard-dockerfile-embed-distroless` covers the concrete Dockerfile/embed/distroless mechanics of the same issue.
