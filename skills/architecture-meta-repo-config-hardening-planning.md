---
name: architecture-meta-repo-config-hardening-planning
description: "How to plan a config-security-hardening fix in a read-mostly docs/config meta-repo (Odysseus) that has NO test framework — config correctness is verified ONLY by `just validate-configs` (`nomad fmt -check` + `yamllint`) and the `_required.yml` lint job, so a planner must NOT invent a pytest/test scaffold; the durable pattern is a shell-grep guard recipe wired into `just ci` AND the lint job so it runs even when the binary (e.g. `nomad`) is absent on the runner. Security stanzas belong IN the canonical config under `configs/` with secrets provisioned at RUNTIME via documented deploy steps (precedent: NATS server.conf documents TLS cert provisioning rather than embedding certs); per CLAUDE.md principle 4, flipping a flag in the canonical file propagates to all hosts that copy/symlink it. Use when: (1) an audit/issue flags a fail-open infra default (e.g. Nomad `bind_addr = 0.0.0.0` with no `acl { enabled = true }`), (2) you are about to reach for pytest in a repo whose `just ci`/`pixi.toml` declares no test harness, (3) you plan to add a grep-based guard regex over an HCL/YAML config and must confirm the anchor matches `nomad fmt`/`yamllint`-canonicalized output, (4) you must decide whether a security flag ships enabled-by-default in the canonical config or commented-out with a documented enablement step, given the repo is 'read-mostly' and pins known-good integration points, (5) the plan asserts config-stanza syntax / tool behavior from training/vendor docs without running the tool against the actually-pinned version, (6) enabling the flag could break existing token-less `nomad status` calls in `just` recipes and the e2e harness."
category: architecture
date: 2026-06-20
version: "1.1.0"
history: architecture-meta-repo-config-hardening-planning.history
user-invocable: false
verification: unverified
tags:
  - planning-methodology
  - meta-repo
  - odysseus
  - config-hardening
  - security-finding
  - canonical-config
  - validate-configs
  - shell-grep-guard
  - guard-recipe
  - just-ci
  - required-yml
  - no-test-harness
  - nomad-acl
  - runtime-secrets
  - enabled-by-default-vs-commented-out
  - unverified-assumptions
  - regression-risk
  - yagni
  - dry
  - pola
  - right-size-the-fix
  - issue-severity
  - circular-verification
  - guard-pattern-misapplication
  - nogo-revision-delta
---

# Planning Config-Security-Hardening Fixes in a Read-Mostly Meta-Repo

> ⚠️ **UNVERIFIED — PLAN ONLY.** This skill captures a *planning* pattern produced
> for Odysseus issue #196 (Nomad `configs/nomad/server.hcl` binds `0.0.0.0` with no
> `acl { enabled = true }`). No files were written, no recipe was added, and `nomad fmt`
> / `yamllint` / `just ci` were never run against the actually-pinned Nomad version.
> Every config-stanza-syntax, tool-behavior, and regression claim below is an assumption
> drawn from training/vendor knowledge. Treat the workflow as a proposal to be verified,
> not as a record of executed and confirmed work. The lessons are durable; the specifics
> (ACL stanza, grep anchor) are illustrative and MUST be re-checked on disk.

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-06-20 |
| **Objective** | Plan a config-security-hardening fix in Odysseus (issue #196: Nomad binds `0.0.0.0`, no ACL stanza) |
| **Outcome** | Plan produced (enable security flag in canonical config + `just`/CI grep guard + runtime-bootstrap docs) — **NOT implemented**; no files written, no validators run |
| **Verification** | unverified |
| **Category** | Architecture / Planning |
| **Related Issues** | #196 |

The durable, reusable lesson is **NOT about Nomad ACLs**. It is about the planning
assumptions and risks that recur for the *class* of "harden a fail-open infra default in
a docs/config meta-repo with no test suite."

---

## When to Use

Use this skill when any of the following triggers apply:

1. An audit/issue flags a **fail-open infrastructure default** in a canonical config —
   e.g. Nomad `bind_addr = "0.0.0.0"` with no `acl { enabled = true }`, anonymous auth,
   `admin/admin`, a disabled-by-default authz flag.
2. You are about to reach for **pytest/jest by reflex** in a repo whose `just ci` /
   `pixi.toml` / `pyproject.toml` declares **no test harness**.
3. You plan to add a **grep-based guard regex** over an HCL/YAML config and must confirm
   the anchor matches the **canonicalized** (`nomad fmt` / `yamllint`) output.
4. You must decide whether a security flag ships **enabled-by-default in the canonical
   config** or **commented-out with a documented enablement step**, in a repo that is
   "read-mostly" and pins known-good integration points.
5. The plan asserts **config-stanza syntax or tool behavior from training/vendor docs**
   without running the tool against the version actually pinned in the deploy runbook.
6. Enabling the flag could **break existing token-less calls** (e.g. `nomad status`
   without an ACL token) in `just` recipes and the e2e harness.

---

## Verified Workflow

> ⚠️ This is a **Proposed Workflow**. It was *not* executed or verified. Validate every
> step (especially config-stanza syntax, the grep anchor, and the regression surface)
> against the on-disk repo and the actually-pinned tool version before acting.

### Quick Reference

| Step | Decision | Anti-pattern to avoid |
|------|----------|------------------------|
| Detect verification surface | Use `just validate-configs` (`nomad fmt -check` + `yamllint`) + `_required.yml` lint | Inventing a pytest/test scaffold |
| Add the guard | Shell-grep recipe wired into `just ci` **AND** the `_required.yml` lint job | Wiring only into a recipe that needs `nomad` (skipped when binary absent) |
| Place the security flag | IN the canonical config under `configs/` | Embedding secrets/certs/tokens in HCL |
| Provision secrets | At RUNTIME via documented deploy steps (deployment.md / add-new-host.md) | Hard-coding a bootstrap token in the repo |
| Scope the change | Ask: enabled-by-default vs. commented-out-with-doc | Flipping a flag that breaks token-less recipes/e2e silently |

1. **Detect the verification surface FIRST — there is no test framework.** Odysseus root
   has no pytest/jest. Config correctness is verified ONLY by `just validate-configs`
   (`nomad fmt -check` + `yamllint`, justfile:258-266) and the `_required.yml` lint job.
   Do **NOT** invent a test scaffold. The durable pattern is a **shell-grep guard recipe**
   (e.g. `just check-nomad-acl`) wired into `just ci` **and** the `_required.yml` lint
   job — so it runs even when `nomad` is **absent** on the CI runner (the lint job has no
   Nomad binary; a recipe that shells out to `nomad` would skip there).

2. **Put the security stanza IN the canonical config; provision secrets at RUNTIME.**
   Per CLAUDE.md principle 4, `configs/` are canonical and hosts copy/symlink from them,
   so flipping a flag in the canonical file propagates to all hosts. **Precedent:**
   `configs/nats/server.conf` *documents* TLS cert provisioning (lines 6-11) rather than
   embedding certs. Follow it: enable the flag in HCL, document the runtime secret step
   (e.g. `nomad acl bootstrap`) in `deployment.md` and `add-new-host.md`. Never embed a
   token/cert in the repo.

3. **If you add a grep guard, anchor it against CANONICALIZED output.** A regex like
   `^\s*acl\s*\{` must match what `nomad fmt` actually emits — `fmt` may render `acl {`
   on its own line or normalize spacing. Verify the anchor against post-`fmt` formatting,
   not against the hand-written draft.

4. **Resolve the enabled-by-default-vs-commented-out scoping question IN THE PLAN.** The
   change is security-correct but operationally disruptive: turning on the flag without
   also distributing/automating tokens to existing recipes (token-less `nomad status`
   calls, e2e scripts, add-new-host) can break a working deployment. Because Odysseus is
   "read-mostly" and pins known-good integration points, explicitly decide and justify:
   enable-by-default in the canonical config, or ship commented-out with a documented
   enablement step. A risk merely *listed* does not count — resolve it in the plan body.

5. **Flag every unverified assumption for the reviewer.** Separate what you VERIFIED on
   disk (file paths, justfile line ranges, existing recipes) from what you ASSERTED from
   training/vendor docs (stanza syntax for the pinned version, tool reformat behavior,
   the bootstrap flow). See Results & Parameters for the verbatim list.

6. **Right-size the fix to issue severity + repo posture (NOGO→revision heuristic).** The
   first #196 plan was NOGO'd (grade D) for over-building. For a MINOR finding on a
   read-mostly meta-repo that pins known-good integration points:
   - Prefer the **smallest config+docs change**; do NOT introduce new recipes, CI steps,
     or test scaffolds. The guard-pattern skill is seductive but its trigger is "an
     un-guarded invariant that SILENTLY LOSES A SIGNAL" — a visible 4-line config flag is
     not that. Don't auto-apply it because "invariant" / "CI gate" appear in the prose.
   - Rely on the **EXISTING gate** (`just validate-configs` = `nomad fmt -check` +
     `yamllint`, justfile:258-266, already run in `_required.yml:48-58`). If a guard truly
     is needed, CI should CALL the recipe, never copy grep logic into the workflow YAML.
   - When a change is **operationally breaking** (a security flag in a config that hosts
     `cp`), document the runtime dependency at EVERY site that copies the artifact
     (server.hcl's own comment + deployment.md Step 5d + add-new-host.md Step 6) rather
     than deferring it to a single prose paragraph.
   - **Label verification by what it proves.** Presence-grep proves the string is there,
     not that the agent boots with it. For a config whose real failure mode is operational,
     give a separate operator-side runtime check and flag it as NOT a CI guarantee.

---

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Invent a pytest scaffold | Adding a `tests/` dir + `pytest` to verify the HCL change | Odysseus root has no test harness; `just ci`/`pixi.toml` declare none, so the test would never run in CI ("green by absence") | Detect the verification surface first: `just validate-configs` + `_required.yml` lint are the ONLY gates; add a shell-grep guard, not a test scaffold |
| Guard only in a nomad-dependent recipe | Wiring `check-nomad-acl` into a recipe that shells out to `nomad` | The `_required.yml` lint runner has no `nomad` binary, so the guard silently skips on CI | Wire the grep guard into `just ci` AND the `_required.yml` lint job so it runs binary-free |
| Embed the bootstrap token in HCL | Putting an ACL token / secret directly in the canonical config | Secrets in the repo leak and violate the canonical-config precedent | Enable the flag in `configs/`; provision the secret at RUNTIME via documented deploy steps (precedent: NATS server.conf TLS cert provisioning, lines 6-11) |
| Anchor grep on the hand-written draft | `^\s*acl\s*\{` matched against the un-formatted HCL | `nomad fmt` may reformat spacing / put `acl {` on its own line, so the anchor can miss post-fmt output | Anchor the guard regex against `nomad fmt`-canonicalized output, not the draft |
| List the regression risk in a note | Flagging "ACLs need tokens" only in a Learnings/docs note | Enabling ACLs makes every token-less `nomad status` call (in `just` recipes + e2e harness) and client registration fail — a real regression left unresolved | Resolve the enabled-by-default-vs-commented-out scope decision in the plan BODY, including token distribution to existing recipes |
| **(NOGO→revision) YAGNI over-build** | For a MINOR "enable a config flag" issue, the first plan added a NEW `just check-nomad-acl` recipe to guard the invariant | The issue asks to turn ON a flag, not to build an enforcement gate; the `architecture-executable-convention-guard-pattern` skill is seductive but its trigger is "an un-guarded invariant that SILENTLY LOSES A SIGNAL," which a visible 4-line config flag is not | Match enforcement weight to issue severity — a MINOR config-flag issue gets config+docs only; do NOT auto-apply the guard-pattern skill just because the words "invariant" and "CI gate" appear |
| **(NOGO→revision) DRY duplication** | The first plan put the SAME grep logic in TWO places — the `just check-nomad-acl` recipe AND a near-identical step in `.github/workflows/_required.yml` | Self-inflicted duplication the plan itself admitted ("runs the same ACL assertion") | If a guard is truly needed, CI should CALL the justfile recipe (`just validate-configs` is already invoked in CI), never copy the logic into the workflow YAML |
| **(NOGO→revision) POLA / enable-by-default trade-off not weighed** | The first plan flipped ACLs on by default in the canonical config and relegated the operational consequence to doc prose | `docs/runbooks/add-new-host.md:101` does `cp configs/nomad/client.hcl`, so enabling-by-default means the NEXT host bootstrap silently requires a NOMAD_TOKEN nobody provisioned → fails "ACL token not found"; a POLA violation against Odysseus's read-mostly / known-good-pins posture, asserted without weighing the commented-out alternative | When a security flag lives in a canonical config that hosts COPY, enabling it is operationally breaking — either (a) ship it commented-out with a documented enable step, or (b) enable it AND co-locate the mandatory runtime-provisioning step (`nomad acl bootstrap` + token distribution) at EVERY copy site (the config's own comment + every runbook that does `cp`). The revision chose (b): loud at server.hcl's comment, deployment.md Step 5d, add-new-host.md Step 6 |
| **(NOGO→revision) Circular verification (presence-grep as behavior proof)** | The first plan's verification was `just check-nomad-acl` / `validate-configs` / grep | All only confirm the STRING is present and fmt-clean; none proves a `hashicorp/nomad:1.6` agent (pinned, deployment.md:215) actually BOOTS with ACLs on or that clients register — "grep finds the stanza ⇒ it works" is circular; the `acl { enabled = true }` syntax was asserted from training, never run | Label every verification command by exactly WHAT it proves (syntax/format vs runtime behavior); for a config change whose real failure mode is operational, provide a separate operator-side runtime check (`nomad agent -dev -config … && nomad acl bootstrap`) and explicitly flag it as NOT a CI guarantee when the repo's CI runs no agent |

---

## Results & Parameters

The plan for issue #196 proposed: add `acl { enabled = true }` to both `server.hcl` and
`client.hcl`; add a `just check-nomad-acl` grep guard wired into `just ci` and a CI step
in `_required.yml`; document the runtime `nomad acl bootstrap` step in `deployment.md`
and `add-new-host.md`. **None of this was executed or validated.**

### Verified on disk (point-in-time, may drift)

| Claim | Source |
|-------|--------|
| Config correctness verified only by `just validate-configs` (`nomad fmt -check` + `yamllint`) | justfile:258-266 |
| `configs/` are canonical; hosts copy/symlink from them | CLAUDE.md principle 4 |
| NATS config documents TLS cert provisioning rather than embedding certs | `configs/nats/server.conf` lines 6-11 |
| Deploy pins the Nomad agent image | `deployment.md` (`hashicorp/nomad:1.6`) |
| Single-node bootstrap + cross-host client registration | `bootstrap_expect = 1`; client `servers = [...]` |

### Most UNCERTAIN assumptions a reviewer MUST check (verbatim)

These were asserted from training knowledge / HashiCorp docs, NOT verified against a
running Nomad in this session:

* That `acl { enabled = true }` is **valid, fmt-clean HCL for the Nomad agent version
  actually deployed** (`deployment.md` pins `hashicorp/nomad:1.6`). The exact stanza
  syntax and whether `nomad fmt` reformats the spacing was NOT run.
* That **enabling ACLs does not BREAK the existing single-node bootstrap / cross-host
  client registration** flows (`bootstrap_expect = 1`, client `servers = [...]`).
  Enabling ACLs means every API call and client now needs a token, which could break
  existing `just` recipes and the e2e harness that call `nomad status` **without a
  token**. This is a real regression risk the plan flagged only in docs, not validated.
* That the **grep-based guard regex** (`^\s*acl\s*\{`) correctly matches
  `nomad fmt`-canonicalized output (fmt may render `acl {` on its own line — verify the
  anchor matches post-fmt formatting).

#### Carried forward from the revision (NOGO→revision delta)

After the first plan was NOGO'd (grade D), the tighter revision still carries these
unresolved assumptions — the reviewer should focus here:

* **(a) HCL validity** — `acl { enabled = true }` is valid + fmt-clean HCL for the pinned
  **nomad 1.6** agent (deployment.md:215). Asserted from training, never executed against
  a live 1.6 agent.
* **(b) Token-less recipe regression** — enabling ACLs may break existing `just`/e2e
  recipes that call `nomad status` / `nomad node status` WITHOUT a token. The revision
  documents the token provisioning but does NOT audit those specific recipes.
* **(c) `nomad fmt` presence on the CI runner** — the HCL fmt step is conditional
  (`command -v nomad`), so fmt-canonicalization may be SKIPPED in CI and only `yamllint`
  runs. Whether `nomad` is installed on the runner was not confirmed.

### External sources relied on WITHOUT direct verification

* HashiCorp Nomad ACL documentation / `nomad acl bootstrap` behavior (assumed from
  general knowledge, not run).
* The assumption that **Tailscale provides only network-layer and not workload-layer
  auth** (true, but stated without citing the issue's own evidence).

### Risk the reviewer should focus on

The change is **security-correct but operationally disruptive**. Turning on ACLs without
also providing/automating token distribution to existing recipes (`nomad`-calling `just`
recipes, e2e scripts, add-new-host) can break the working deployment. The safest scoping
question: **should ACLs be enabled-by-default in the canonical config, or shipped
commented-out with a documented enablement step**, given Odysseus is "read-mostly" and
pins known-good integration points?
