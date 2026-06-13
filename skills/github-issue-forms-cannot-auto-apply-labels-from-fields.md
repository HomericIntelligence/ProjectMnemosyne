---
name: github-issue-forms-cannot-auto-apply-labels-from-fields
description: "GitHub issue FORMS (.github/ISSUE_TEMPLATE/*.yml) cannot map a dropdown/input field SELECTION to a label — only the static top-level `labels:` array applies labels at creation time. A captured-but-never-read field is the YAGNI 'field nobody consumes' anti-pattern. The FIX is to pair the field with a body-parsing `on: issues: [opened, edited]` GitHub Actions workflow (a 'tagger') that greps the rendered answer and applies a hard-coded label. Use when: (1) you want an issue-form dropdown (e.g. Severity) to actually drive a label-gated pipeline, (2) a planner NOGO'd a plan that added a form field with no consumer, (3) you need the injection-safe (CWE-94) recipe for reading `github.event.issue.body` in a tagger, (4) you must decide which form fields are auto-consumed vs reference-only, (5) you hit `default:` / relative-link / phantom-label gotchas in an issue form."
category: architecture
date: 2026-06-12
version: "1.0.0"
user-invocable: false
verification: unverified
tags:
  - github-issue-forms
  - issue-template
  - dropdown-no-label
  - body-parsing-tagger
  - actions-injection
  - cwe-94
  - labels-as-state
  - yagni-unconsumed-field
  - on-issues-opened-edited
  - reference-only-fields
  - severity-label
  - idempotent-labels-endpoint
  - planning-learning
  - no-response-no-op
---

# GitHub Issue Forms Cannot Auto-Apply Labels From Fields (And How To Make Them Feed a Pipeline)

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-06-12 |
| **Objective** | Resolve the GitHub-issue-form limitation that a `dropdown`/`input` field SELECTION cannot apply a label. Only the static top-level `labels:` array applies labels at creation. Capturing a field that nothing reads is the YAGNI "field nobody consumes" anti-pattern. The resolution: pair the field with a body-parsing `on: issues: [opened, edited]` tagger Action that greps the rendered answer and applies a hard-coded label — turning a passive field into a real pipeline input. |
| **Outcome** | Planning learning for HomericIntelligence/ProjectHephaestus issue #1210. A revised (R1) plan found the resolution after the R0 plan got a NOGO for adding a severity dropdown with no consumer. The R1 plan specifies an injection-safe tagger modeled on the repo's existing `auto-label-needs-plan.yml`, an honest auto-consumed-vs-reference-only field distinction, and a consumer-workflow parse test. NOT yet executed — no code merged, no CI. |
| **Verification** | `unverified` — plan written and reviewed this session; no implementation run, no CI. The load-bearing body-rendering format assumption (`### <label>` heading + value on the next line) was NOT verified against a live rendered form. |
| **Live observation that motivated this** | R0 plan added a Severity dropdown to the issue form "so a triager could read it"; reviewer NOGO'd it — acknowledging a limitation is not fixing it, and a field nothing automatically reads does not "feed the process." |

## When to Use

- You want an issue-form `dropdown` or `input` (e.g. Severity, Priority) to actually **drive** a label-gated pipeline, not just sit in the body as decoration.
- A plan/PR review NOGO'd a change because it added an issue-form field with **no consumer** ("a human could read it" is not a consumer).
- You need the **injection-safe (CWE-94)** recipe for reading `${{ github.event.issue.body }}` inside a tagger workflow without shell-interpolating attacker-controlled text.
- You must decide, honestly, **which form fields are auto-consumed vs reference-only** — and avoid promising a consumer you aren't building.
- You hit issue-form gotchas: an unverified `default:` key, a relative markdown link that 404s in the new-issue view, or a phantom label seeded in the form's `labels:` array.
- You are wiring a tagger that must be safe to re-run on `edited` (idempotent label POST).

**Don't use when:**

- The field is genuinely **reference-only** (e.g. an Epic-parent `#NNN` free-text input). Do NOT parse free-text into pipeline state — that is the drift anti-pattern from `architecture-github-labels-as-state-vocabulary`. Leave it reference-only and document it as such.
- A static top-level `labels:` array already applies the only label you need at creation — no tagger required.
- The repo is a personal scratch project with no label-driven automation — KISS; just read the body by eye.

## Verified Workflow

> **Warning (Proposed Workflow):** This workflow has not been validated end-to-end. Treat as a hypothesis until CI confirms. Verification level: `unverified` — plan written and reviewed, not executed; the body-rendering grep assumption was not checked against a live rendered issue.

### The Core Limitation (Problem Statement)

GitHub issue **forms** (`.github/ISSUE_TEMPLATE/*.yml`, the structured YAML form schema — NOT legacy markdown templates) have exactly one mechanism that applies labels: the **static top-level `labels:` array**, applied verbatim at issue creation. There is **no** schema construct that maps a `dropdown`/`input` field's selected value to a label. A field's answer lands only in the rendered issue **body** as text. So:

- A captured-but-unread field "feeds" nothing — it is the YAGNI **"field nobody consumes"** anti-pattern.
- To make a field input drive a pipeline you must **add a consumer**: a body-parsing Action.

### Quick Reference

```yaml
# ── (1) The form field: required:false, NO default: → unselected renders "_No response_" ──
# .github/ISSUE_TEMPLATE/bug_report.yml  (excerpt)
  - type: dropdown
    id: severity
    attributes:
      label: Severity                    # becomes the "### Severity" body heading
      options:
        - "minor"
        - "major"
        - "critical"
    validations:
      required: false                    # unselected => "_No response_" => tagger no-ops
```

```yaml
# ── (2) The consumer: a body-parsing tagger, injection-safe (CWE-94) ──
# .github/workflows/auto-label-severity.yml
name: auto-label-severity
on:
  issues:
    types: [opened, edited]             # edited re-run is safe — labels POST is idempotent

permissions:
  contents: read
  issues: write                          # least privilege — labels endpoint only

jobs:
  tag:
    runs-on: ubuntu-latest
    steps:
      - name: Apply severity label from rendered form body
        env:
          GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
          ISSUE_NUMBER: ${{ github.event.issue.number }}   # server-controlled integer
          ISSUE_BODY: ${{ github.event.issue.body }}        # bind to env — NEVER inline in run:
          REPO: ${{ github.repository }}
        run: |
          # Validate the issue number is numeric before it ever reaches gh api.
          case "$ISSUE_NUMBER" in ''|*[!0-9]*) echo "bad issue number" >&2; exit 1 ;; esac

          # Read body ONLY via printf|grep against LITERAL hard-coded option strings.
          # The field's `label:` renders as a "### Severity" heading; the answer follows.
          block="$(printf '%s' "$ISSUE_BODY" | grep -A2 -iE '^### *Severity' || true)"

          # POST a CONSTANT label name — never a value derived from user text.
          label=""
          case "$block" in
            *critical*) label="severity:critical" ;;
            *major*)    label="severity:major" ;;
            *minor*)    label="severity:minor" ;;
          esac

          if [ -n "$label" ]; then
            gh api -X POST "/repos/$REPO/issues/$ISSUE_NUMBER/labels" -f "labels[]=$label"
          fi
          # "_No response_" (unselected) matches nothing → no label → safe no-op.
```

### Detailed Steps

1. **Pair the field with a tagger in the SAME change.** Adding a form field without its consumer is exactly the NOGO. If you add the dropdown, add the body-parsing Action in the same PR — or don't add the field.

2. **Understand the rendering contract (load-bearing assumption).** GitHub renders a `dropdown`/`input` answer in the issue body as a markdown section: the field's `label:` becomes a `### <Label>` heading, and (after a blank line) the selected/entered value text follows. The tagger greps that block (`grep -A2 -iE '^### *Severity'`) and matches against hard-coded option strings. **This format was NOT verified against a live rendered form this session** — verify it before relying on it (see Results).

3. **Be injection-safe (CWE-94).** Bind `${{ github.event.issue.body }}` to an `env:` var; NEVER interpolate it into the `run:` shell script. Read it only via `printf '%s' "$ISSUE_BODY" | grep ...` against LITERAL hard-coded option strings. On a match, POST a **CONSTANT** label name (`severity:minor`), never text derived from the user's answer. Validate `$ISSUE_NUMBER` is numeric (`case "$ISSUE_NUMBER" in ''|*[!0-9]*) exit 1 ;; esac`) before `gh api`. This mirrors the repo's existing `auto-label-needs-plan.yml`.

4. **Make the label POST idempotent and `edited`-safe.** The labels endpoint no-ops if the label is already present, so listening on `[opened, edited]` is safe — re-runs add nothing.

5. **Use `required: false` and OMIT `default:`.** An unselected dropdown renders as `_No response_` in the body, which the tagger treats as a safe no-op (no label). This sidesteps both the unverified form-schema `default:` key AND filing friction (no forced selection).

6. **Distinguish auto-consumed vs reference-only fields HONESTLY.** A Severity dropdown CAN be auto-labeled by a tagger. An Epic-parent `#NNN` free-text **input** should stay **reference-only** — do NOT parse free-text into pipeline state (that is the drift anti-pattern in `architecture-github-labels-as-state-vocabulary`). Document each field's status; don't promise a consumer you aren't building.

7. **Verify every seeded label and every link before shipping.** Run `gh label list` to confirm every label in the form's top-level `labels:` array (and every label the tagger POSTs) actually exists. Use absolute `https://github.com/<owner>/<repo>/blob/main/...` URLs in `markdown` blocks — relative links 404 in the new-issue view.

8. **Test the risky mechanic, not the field shape.** A test that only asserts the form's own field shape is self-referential. ALSO parse-validate the consumer workflow YAML and assert the body is never shell-interpolated: e.g. assert that `"${{ github.event.issue.body }}"` does NOT appear anywhere in the substring after `run:`. Test the integration, not the self-consistency.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| 1 | Mapped a dropdown selection to a label directly in the issue-form YAML schema | No such construct exists — issue forms apply labels ONLY via the static top-level `labels:` array at creation. The field answer lands only as body text. | The form cannot auto-label from a field. To label from a selection you MUST add a body-parsing consumer Action. |
| 2 | Shipped a Severity dropdown with NO consumer ("a triager could read it") | NOGO: acknowledging a limitation is not fixing it; a field nothing automatically reads does not "feed the process." It is the YAGNI "field nobody consumes" anti-pattern. | Add the body-parsing tagger in the SAME change, or don't add the field. |
| 3 | `default: <index>` on the issue-form dropdown | Unverified against the GitHub form schema AND self-contradicts `required: true` (a defaulted field is never empty, so "required" is meaningless). | Omit `default:`; use `required: false`. An unselected dropdown renders `_No response_`, a safe tagger no-op. |
| 4 | Relative markdown link (`../../docs/foo.md`) in the form's `markdown` block | 404s — links in the rendered NEW-ISSUE form resolve against the issue-creation URL, not the repo file tree. | Use an absolute `https://github.com/<owner>/<repo>/blob/main/...` URL (matches the repo's `config.yml` convention). |
| 5 | Seeded `needs-triage` in the form's top-level `labels:` array without checking it exists | Seeds a phantom label — GitHub silently creates/ignores it and the intended automation never keys off a real label. | Verify EVERY seeded (and tagger-POSTed) label via `gh label list` first. |
| 6 | Interpolated `${{ github.event.issue.body }}` directly into the tagger's `run:` shell script | GitHub Actions injection (CWE-94): attacker-controlled body text breaks out of the shell command. | Bind the body to an `env:` var; read it only via `printf|grep` against LITERAL option strings; POST a CONSTANT label name. |
| 7 | Parsed a free-text Epic-parent `#NNN` input into pipeline state | Free-text parsing into state drifts and is fragile (the anti-pattern from `architecture-github-labels-as-state-vocabulary`). | Keep free-text inputs REFERENCE-ONLY; only auto-consume closed-set fields (dropdowns) into hard-coded labels. |
| 8 | Wrote a test that only asserted the form's own field shape | Self-referential — it proves the YAML says what the YAML says, not that the risky integration is safe. | ALSO parse-validate the consumer workflow YAML; assert the body is never shell-interpolated after `run:`. Test the mechanic. |

## Results & Parameters

### What Worked (verified during planning)

- **Grounded every label/line claim in live `gh label list`** rather than assuming a label exists.
- **Copied the injection-safe pattern from the existing `auto-label-needs-plan.yml`** — env-bound event data, numeric `$ISSUE_NUMBER` validation, typed `gh api` POST to the labels endpoint.
- **Confirmed `parents[3]` resolves to repo root** in the test harness (reviewer confirmed — no off-by-one).
- **Confirmed the `docs/ROADMAP.md` path/line range** (it is under `docs/`, NOT a repo-root `ROADMAP.md`).

### Auto-Consumed vs Reference-Only (Honest Field Classification)

| Field kind | Example | Consumer? | Treatment |
|------------|---------|-----------|-----------|
| Closed-set dropdown | Severity (`minor`/`major`/`critical`) | YES — body-parsing tagger maps the selection to a hard-coded `severity:*` label | Auto-consumed; verify the labels exist; ship the tagger in the same change |
| Free-text input | Epic-parent `#NNN` | NO — do NOT parse free text into state | REFERENCE-ONLY; document as such; do not promise a consumer |
| Static top-level `labels:` | `bug` applied at creation | N/A — applied by GitHub directly | No tagger needed; still verify the label exists |

### Verification-Design Learning

A static test that only asserts the form's own field shape is **self-referential**. ALSO:

1. Parse-validate the **consumer workflow** YAML.
2. Assert the body is **never shell-interpolated**: e.g. confirm `"${{ github.event.issue.body }}"` does NOT appear in the substring after `run:`.

Test the risky integration mechanic, not just self-consistent field assertions.

### Uncertain Assumptions (Un-Executed — Flag for the Implementer/Reviewer)

- **The exact GitHub body-rendering format** (`### <label>` heading + value on a following line) is the load-bearing assumption the tagger's grep depends on. It was **NOT verified against a live rendered form** this session. If GitHub renders dropdown answers differently (inline, or a different heading depth), the grep silently matches nothing and applies no label. This **fails safe** (no wrong label) but leaves the feature **inert**. **Recommendation:** the implementer should verify the format against one real rendered issue before relying on it.
- The form-schema `default:` key behavior is unverified — the plan deliberately omits `default:` and uses `required: false` to avoid depending on it.

### Cross-References

- **`architecture-github-labels-as-state-vocabulary`** — the body-parsing tagger applies labels-as-state; the same injection-safe `on: issues` workflow discipline applies. Also the source of the "don't parse free-text into pipeline state" drift anti-pattern that keeps the Epic-parent input reference-only.
- **`monorepo-subproject-gitignore-and-github-template-gotchas`** — related `.github/ISSUE_TEMPLATE` and template-placement gotchas for monorepo subprojects.

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectHephaestus | Issue #1210 — R1 (revised) planning session | Plan written and reviewed; resolution (body-parsing tagger paired with the form field, injection-safe, honest field classification, consumer-workflow parse test) specified but NOT executed — no code merged, no CI. `unverified`. |
| ProjectHephaestus | R0 NOGO that motivated the resolution | R0 plan added a Severity dropdown with no consumer ("a triager could read it"); reviewer NOGO'd it — a field nothing automatically reads does not feed the process. |
