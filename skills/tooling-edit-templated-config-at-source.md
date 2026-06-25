---
name: tooling-edit-templated-config-at-source
description: "When a config file is regenerated from a template by a build/deploy step, editing the generated file gets silently overwritten. Use when: (1) your edits to a config file disappear after running a setup/config step, (2) a tool renders config from a Jinja/template + variable defaults, (3) a deploy reads a value that was set but comes through empty."
category: tooling
date: 2026-06-22
version: "1.0.0"
user-invocable: false
verification: verified-local
tags: [configuration, templating, jinja, idempotency]
---

# Edit Templated Config at the Source, Not the Generated Artifact

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-06-22 |
| **Objective** | Make a configuration change persist when the config file is a generated artifact rendered from a template plus variable sources |
| **Outcome** | Edits durably survived regeneration once applied to the template AND a variable-defaults layer; editing the generated file alone was silently wiped on the next render |
| **Verification** | verified-local |

A config file that is a GENERATED ARTIFACT — rendered from `<config-template>` plus input variables — is disposable. Editing `<generated-config>` directly works for exactly one run, then the next render of the build/deploy step overwrites it and your change vanishes. The durable change must live in the template and in a variable-defaults layer, not in the output file.

## When to Use

- Your edits to a config file disappear after running a setup/config/deploy step.
- A tool renders config from a Jinja (or similar) template plus variable defaults (extra-vars, `<group-vars-file>`, role defaults).
- A deploy reads a value that was "set" but comes through empty — a list variable referenced by a downstream task arrives as an empty list, so the task runs "successfully" (reports changed) but produces no effect (writes nothing), because the value never survived regeneration.

## Verified Workflow

> **Note:** verified-local. The render + precedence behavior was confirmed locally by running the render step and grepping the regenerated output; not exercised through a full CI deploy.

### Quick Reference

```yaml
# In <config-template> (e.g. a Jinja template), add the missing key using the
# SAME idiom the file already uses for similar values. For a list:
mykey: {{ mykey | default([]) }}
# renders to an inline flow-style list, e.g.:  mykey: ['a', 'b', 'c']
# which is valid, iterable YAML (loop / with_items can walk it).
```

```yaml
# In the variable-defaults layer (<group-vars-file>, e.g. group_vars/all, or role
# defaults), define the same variable so it is NEVER undefined:
mykey:
  - a
  - b
  - c
```

```bash
# Verify end to end: re-run the render step, then grep the regenerated output,
# then confirm the downstream consumer sees a NON-EMPTY value.
grep -n 'mykey' <generated-config>      # key present with real values, not []
```

Ansible variable precedence (lowest → highest), so you know which source wins:

```text
role defaults  <  group_vars  <  host_vars  <  play/role vars  <  extra-vars
```

Put durable defaults at a LOW-precedence layer (role defaults / `<group-vars-file>`); put explicit per-run overrides at a HIGHER one (extra-vars).

### Detailed Steps

1. **Determine whether the file you are editing is generated.** Tells: a template file exists whose output path is exactly the config you edited; a "config"/"render"/"generate" step copies a template into place; the file header says "do not edit / run X to populate."
2. **Edit the TEMPLATE, not the output.** Add the missing key to `<config-template>` using the same templating idiom the file already uses for similar values — e.g. for a list, `mykey: {{ mykey | default([]) }}`, verified to render to an inline flow-style list like `['a', 'b']` (valid, iterable YAML).
3. **Add the variable as a DEFAULT in the variable-defaults location** (`<group-vars-file>` such as `group_vars/all`, or role defaults) so the variable is never undefined. This breaks the chicken-and-egg case where `<generated-config>` already lost the value, leaving nothing to render from.
4. **For the immediate run, also set the value in `<generated-config>`** (belt-and-suspenders) — but understand that the template + defaults are what make it durable; the generated edit alone is throwaway.
5. **Confirm the precedence order** so you know which source wins: in Ansible it is extra-vars > play/role vars > host_vars > group_vars > role defaults. Durable defaults go at a low-precedence layer; explicit overrides at a higher one.
6. **Verify end to end:** run the render step, then grep the regenerated `<generated-config>` for the key, then confirm the downstream consumer sees a non-empty value — not just that the render reported success.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| Edit the generated file | Edited `<generated-config>` directly and re-ran the deploy | The config step re-rendered the file from its template and wiped the edit; the downstream list variable came through empty | Edit the template AND add a default — not the generated file, which is disposable |
| Trust task status | Assumed "task reported changed = it worked" | The task iterated an empty list, so it changed nothing meaningful while still reporting changed/ok | Verify the actual side effect (file contents / mounts / output), not just the task status |
| Render template in isolation | Tested the template render with only a few vars set | The render failed on an unrelated 'undefined variable' from the many other refs in the template | Render with the full variable set (or trust the real render step that supplies them) and isolate only the specific line you added |

## Results & Parameters

### Configuration

```yaml
# Templated list idiom — renders to a valid, iterable inline YAML list:
key: {{ key | default([]) }}
# -> key: ['a', 'b', 'c']
```

### Expected Output

- After re-running the render step, `grep` of `<generated-config>` shows the key populated with real values (e.g. `['a', 'b', 'c']`), not an empty `[]`.
- The downstream consumer (loop / with_items / mount task) sees a non-empty value and produces a real side effect.

### Durable-config rule of thumb

The change must live in **(a) the template AND (b) a defaults layer**. The generated file is disposable — never the source of truth.

## Verified On

| Project | Context | Details |
| --------- | --------- | --------- |
| (generic) | Config file rendered from a Jinja template + variable defaults; edits to the generated file were wiped on re-render; fixed by editing the template and adding a defaults-layer entry | This skill |

## References

- [placeholder-config-deploy-render-footgun](placeholder-config-deploy-render-footgun.md)
- [planning-generated-doc-from-source-headers](planning-generated-doc-from-source-headers.md)
