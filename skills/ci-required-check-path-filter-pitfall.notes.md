# Raw plan excerpt — ci-required-check-path-filter-pitfall

Source: HomericIntelligence/ProjectHermes issue #562 implementation plan (plan written, never
executed or merged). Captured 2026-06-19. This is the raw, repo-specific reasoning behind the
transferable skill; the skill itself is generic.

## The trap (headline)

The issue asked: "run a Docker build only on PRs that touch the Dockerfile." The obvious
implementation is a workflow-level `on.pull_request.paths:` filter. But the target workflow is
`_required.yml`, which appears to be wired as a required status check (inferred from the filename
and `pull_request: branches:[main]`, NOT confirmed via the branch-protection API).

If a workflow is a required status check and you add a workflow-level `paths:` filter, then on any
PR that does NOT touch the filtered paths the whole workflow is skipped. GitHub does not synthesize
a passing status for a workflow that never ran, so the required context never reports. The PR is
stuck at "Expected — Waiting for status to be reported" and is un-mergeable. Therefore the literal
issue request cannot be satisfied with a `paths:` block on the required workflow.

## Chosen design

- Add a `dockerfile-smoke-build` job to `_required.yml` that runs UNCONDITIONALLY (cheap,
  self-contained), inserted AFTER `readonly-fs-smoke` and BEFORE `security-dependency-scan`
  (anchor on names, not the line numbers `:281`/`:283`/`:359` which were read once and will drift).
- `runs-on: ubuntu-24.04`, single-arch host `linux/amd64` — the pixi workspace is `linux-64` and
  cannot build `linux/arm64`, so no multi-arch matrix.
- `docker buildx build --load -t <img>:smoke .` — BLOCKING. No `continue-on-error: true`, because
  the repo has a forbid-suppressions guard + regression test that fail CI on it (and a build gate
  should be blocking anyway).
- Keep the digest-pinned `FROM` as-is. Do NOT rewrite it to an `mcr.microsoft.com/mirror/...`
  base to dodge Docker Hub rate limits, because that changes the image digest → changes the
  shipped artifact. The MCR-mirror trick is for UNPINNED bases only.
- `docker/setup-buildx-action@8d2750c... # v3` SHA copied from `publish.yml:5`/`:28` (not
  independently verified upstream).

## Why no `paths:` block (must be stated so reviewer doesn't read it as a miss)

The issue asked for path scoping; the plan deliberately does NOT add a workflow-level `paths:`
block, because doing so on a required workflow would brick unrelated PRs. The always-run design is
the trade-off. If `_required.yml` turns out NOT to be a required check, a `paths:` filter would be
acceptable and the always-run design is needlessly conservative.

## The five most uncertain assumptions (verify these)

1. UNVERIFIED that `_required.yml` is actually a required status check in branch protection.
   Inferred from the filename and trigger, NOT confirmed via
   `gh api repos/:owner/:repo/branches/main/protection`. The entire argument rests on this.
2. UNVERIFIED line numbers — `_required.yml:281`/`:283`/`:359`, `publish.yml:5`/`:28`,
   `Dockerfile:5,14`. Read once; brittle. Anchor on job NAMES.
3. The action SHA `docker/setup-buildx-action@8d2750c... # v3` was COPIED from publish.yml, not
   verified against the upstream tag.
4. `docker buildx` availability on `ubuntu-24.04` runners assumed (true as of 2026); setup action
   included for safety but not validated on the actual runner image.
5. Docker Hub anonymous-pull rate limits on shared runner IPs — acknowledged but NOT mitigated
   (no auth, no mirror, because the base is digest-pinned). Reviewer should weigh accepting the
   flake vs adding registry auth.

## External things relied on WITHOUT direct verification

- GitHub workflow JSON schema URL (`https://json.schemastore.org/github-workflow`) — taken from
  the repo's own schema-validation job, not fetched.
- `check-jsonschema` assumed installable.
- Branch-protection config not queried.
- Upstream action tags not cross-checked.

## R1 re-plan — the #1 risk materialized (2026-06-19)

R1 of the ProjectHermes #562 plan finally VERIFIED the keystone assumption. Branch protection was
queried:

```bash
gh api repos/HomericIntelligence/ProjectHermes/branches/main/protection \
  --jq '.required_status_checks.contexts'
# -> ["Secret Scanning (gitleaks)","justfile-check"]
```

The docker-build job is NOT among the required contexts. Therefore the R0 keystone premise —
"the workflow is a required check, so a `paths:` filter would brick unrelated PRs" — was FALSE.
A skipped, path-filtered workflow does NOT block merge here. The reviewer NOGO'd R0 (grade D)
precisely because it built on this unverified-and-false premise.

### Corrected pattern — dedicated path-filtered workflow

Because the check is NOT required, the correct, KISS, requirement-matching design is a dedicated
workflow that path-filters on the Dockerfile (this also matches the issue's literal ask):

```yaml
# .github/workflows/docker-build.yml  (a NON-required workflow → safe to path-filter)
name: docker-build
on:
  pull_request:
    paths:
      - 'Dockerfile'
      - 'docker/**'
      - '.dockerignore'
jobs:
  docker-build:
    runs-on: ubuntu-24.04        # single-arch host linux/amd64 (pixi linux-64)
    steps:
      - uses: actions/checkout@<sha>
      - uses: docker/setup-buildx-action@<sha>
      - run: docker buildx build --load -t hermes:smoke .   # BLOCKING, no continue-on-error
```

Still `unverified` overall — R1 remained a plan, never merged/executed — but the "is it actually
a required check?" question was answered empirically, and the answer flipped the design.
