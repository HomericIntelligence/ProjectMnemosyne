---
name: debugging-diagnose-before-fixing-stale-blocker-claims
description: "When you inherit a claim that a deploy/build is broken 'because of X and Y' (a missing role/module, a missing dependency/collection), treat the claim as a HYPOTHESIS and run cheap READ-ONLY diagnostics before fixing anything: confirm the suspect component is REAL (a named role/module dir, not just a string/variable/template reference), confirm it is on the ACTIVE path (enabled/imported/reachable — a requirement from a DISABLED feature is not a live blocker), and confirm the GENERATED/rendered config artifact actually exists and is current. A wholly-missing generated artifact frequently masquerades as a deep code defect; regenerating it via the project's config/render target often makes the symptom vanish. Use when: (1) prior notes/memory assert a build or deploy is blocked by specific code-level causes, (2) the symptom involves a config/settings file the project generates or renders, (3) suspect components are gated behind enable/disable flags, (4) a grep matches a name and you are about to assume the named component exists."
category: debugging
date: 2026-06-22
version: "1.0.0"
user-invocable: false
verification: verified-local
tags: [diagnostics, read-only, stale-claims, inherited-notes, generated-config, enable-flags, red-herring, deploy, render, regenerate, active-path]
---

# Diagnose Before Fixing: Verify Stale "It's Broken Because X" Claims

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-06-22 |
| **Objective** | Stop wasting effort "fixing" inherited blocker claims that are stale or off the active code path; find the real blocker first. |
| **Outcome** | Read-only diagnostics proved two claimed code-level blockers were red herrings; the real blocker was a wholly-missing generated config file that regenerating fixed. |
| **Verification** | verified-local — diagnostics and regeneration were run and observed locally. |

## When to Use

- You inherit a note/memory/handoff that says "the deploy/build is broken because of X and Y" (a missing role/module, a missing dependency or collection).
- The symptom touches a config/settings file that the project **generates or renders** rather than commits by hand.
- Suspect components are gated behind **enable/disable flags** and you have not confirmed they are actually enabled.
- A grep matched a name and you are about to assume "a component named N exists" — when it may just be a variable, a template field, or a similarly-named-but-different component.
- The claim crosses a time/session boundary (notes written earlier may have gone stale after other changes landed).

## Verified Workflow

### Quick Reference

```bash
# 1. Scope by what is ENABLED. A requirement from a disabled component is NOT a live blocker.
grep -rnE '<enable_flag_pattern>\s*:\s*(true|false)' <rendered-config> | sort | uniq -c
grep -rniE '<enable_flag_pattern>.*true' <rendered-config>    # only the live ones

# 2. Confirm the "missing" component is REAL, not just a string/variable/template reference.
grep -rn '<component-name>' <roles-or-modules-dir>/ <entrypoints-dir>/
ls -d <components-dir>/<component-name>     # does a real role/module DIR exist?

# 3. Confirm the GENERATED artifact exists and is current; if absent, REGENERATE first.
ls -l <path-to-generated-config>            # does the rendered file even exist?
<project-config-or-render-target>           # e.g. `make config` / `just render` / project task
ls -l <path-to-generated-config>            # re-check, then re-test the ORIGINAL symptom

# 4. Only now apply remaining fixes; label disabled-component fixes as "insurance, not critical path."
```

### Detailed Steps

1. **Enumerate what is ENABLED.** Grep the rendered config for enable flags set to true vs false. If the suspect component is disabled, deprioritize it — its requirements were never evaluated on the active path. (In the source session, of 134 enable flags exactly 1 was true; both suspect components were disabled.)
2. **Confirm the named "missing" component is real.** Run `grep -rn <name> <roles-or-modules-dir>/ <entrypoints-dir>/` and `ls -d <component-dir>`. Distinguish a real role/module directory from mere variable interpolation in a config template or a differently-named real component that happens to share a substring.
3. **Confirm the generated artifact exists and is current.** If the rendered settings/config file is absent from disk, regenerate it via the project's config/render target FIRST, then re-check the original symptom — it often disappears entirely. A missing generated file is a far more common cause than a deep code defect.
4. **Apply remaining fixes last.** Anything that only matters to a currently-disabled component is at most insurance. Label it explicitly as "not on the critical path" so it does not block the actual goal.
5. **Correct the durable note/memory** that carried the stale claim, so the next session does not re-inherit the same dead hypothesis.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| ------- | -------------- | ------------- | -------------- |
| Trust the inherited note | Took the inherited note "deploy is broken: missing role + role needs crypto lib" at face value and prepared to add the crypto dependency and stub the missing role. | Diagnostics showed the "missing role" was never imported (just variable/template references plus a differently-named real role), and both suspect roles were DISABLED in config — neither was on the active path. | Verify a claimed blocker is REAL and on the ACTIVE path before fixing it; inherited notes go stale. |
| Assume a code-level defect | Assumed a code-level defect was blocking the deploy and started planning code changes. | The actual blocker was simply that the GENERATED config file was missing from disk; regenerating it produced a valid config and the symptom vanished. | A missing generated/rendered artifact masquerades as a code defect — check the artifact exists / is current BEFORE diving into code. |

## Results & Parameters

Generalizable principles (the heart of this skill):

1. **Inherited "it's broken because X" notes are HYPOTHESES, not facts** — especially across time/sessions. They go stale.
2. **Run cheap READ-ONLY diagnostics before fixing**: confirm the artifact exists, confirm the suspect component is on the ACTIVE path (enabled/imported/reachable), and grep to see whether the named thing is a real component or just a string/variable reference.
3. **A missing GENERATED/rendered artifact frequently masquerades as a deeper code defect.** Check "does the generated file even exist / is it current?" before diving into roles/modules/dependencies. Regenerating it may resolve the whole thing.
4. **Scope by what is ENABLED.** Count enabled vs disabled feature flags; a requirement from a disabled component is not a live blocker. Fixes for disabled components are at most "insurance" — label them as such and do not let them block the goal.
5. **A grep that matches a name does not mean a component exists.** Distinguish "a role/module named N exists" from "the string N appears" (it may be a variable, a template field, or a similarly-named-but-different component).

Worked example (sanitized):

```text
Inherited claim : "deploy chain broken — (a) missing role, (b) a role needs a crypto library"
Diagnostic (a)  : grep + ls showed no role by that name; references were variable interpolation
                  in a config TEMPLATE plus a real, differently-named role. Nothing imported it.
Diagnostic (b)  : both suspect roles were DISABLED (1 of 134 enable flags was true) — off active path.
Real blocker    : the rendered settings/config file did not exist on disk.
Resolution      : ran the project's `config` render target → valid file produced → vault decrypted fine.
                  Both "code-level blockers" were a misdiagnosis of "the generated config was absent."
```

## Related Skills

- `placeholder-config-deploy-render-footgun` — a DIFFERENT generated-config failure mode: unresolved `${VAR}`/placeholder values leaking into configs consumed RAW by a daemon. That skill is about a config that IS rendered but carries an unresolved placeholder; THIS skill is about diagnosing stale "it's broken" claims and a config that is wholly MISSING/un-rendered. Read both — they cover complementary generated-config pitfalls.
- `stale-plan-already-resolved` — detecting that an inherited plan is stale because the fix already landed; complementary "verify current state before acting" discipline.

## Verified On

| Project | Context | Details |
| ------- | ------- | ------- |
| (generic) | Deploy-chain triage where inherited notes named code-level blockers | Read-only diagnostics + regenerating a missing rendered config resolved the symptom. |
