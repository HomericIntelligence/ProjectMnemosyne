---
name: tooling-ansible-core-upgrade-legacy-playbooks
description: "How to run a legacy Ansible 2.9 project on modern ansible-core (2.13). Use when: (1) a Dockerized Ansible toolchain ships ansible 2.9 and Mitogen aborts with 'too old', (2) you hit 'couldn't resolve module/action' for alternatives/docker_image/htpasswd after upgrading, (3) playbooks error on vars_prompt 'when' or command 'warn'."
category: tooling
date: 2026-06-22
version: "1.0.0"
user-invocable: false
verification: verified-local
tags: [ansible, ansible-core, mitogen, collections, upgrade]
---

# Run Legacy Ansible 2.9 Playbooks on Modern ansible-core (2.13)

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-06-22 |
| **Objective** | Make a legacy Ansible 2.9 playbook suite run under a modern ansible-core inside a Docker-based runner, with minimal code changes. |
| **Outcome** | Legacy roles run unchanged on `ansible-core==2.13.13`; Mitogen 0.3.x works again; short module names resolve via installed collections; two small playbook syntax adjustments (`warn:` and `vars_prompt` `when:`) are the only role/playbook edits. |
| **Verification** | `verified-local` — each fix validated in isolation in a throwaway container/test play before the full run. |

## When to Use

- A Dockerized Ansible toolchain ships `ansible 2.9` and Mitogen aborts with: `Your version of Ansible is too old. The oldest version supported by Mitogen is (2, 10).`
- You hit `couldn't resolve module/action` for short module names like `alternatives`, `docker_image`, or `htpasswd` after upgrading ansible-core.
- Playbooks error on `when:` keys under individual `vars_prompt` entries.
- Playbooks error on the `warn:` argument under `command`/`shell` tasks.
- You need to keep a legacy Ansible 2.9 project running with the smallest possible diff to roles.

## Verified Workflow

### Quick Reference

```dockerfile
# Pin ansible-core (last series supporting Python 3.8 control node) and the
# collections that provide the short module names legacy roles use.
ENV ANSIBLE_VERSION 2.13.13
RUN pip install ansible-core==${ANSIBLE_VERSION} \
 && ansible-galaxy collection install \
      "community.general:>=5.0.0,<6.0.0" \
      "community.docker:>=2.0.0,<3.0.0"
```

```text
# Playbook edits (2 kinds, both removals):
#   command/shell:  delete  args: { warn: "no" }   (arg removed in 2.13, no-op)
#   vars_prompt:    delete  when:                   (rejected in 2.13)
# Precedence that makes prompt removal safe:
#   --extra-vars  >  vars_prompt  >  group_vars  >  role defaults
```

### Detailed Steps

#### 1. Upgrade ansible so Mitogen stops aborting

Mitogen 0.3.x requires `ansible-core >= 2.10`. With `ansible 2.9.6`, Mitogen
aborts with `Your version of Ansible is too old. The oldest version supported by
Mitogen is (2, 10).` The fix is to upgrade ansible, not to downgrade Mitogen.

#### 2. Pick the right ansible-core for the base image

On a Python 3.8 base image, the newest ansible-core that installs as a prebuilt
wheel is `2.13.13` (2.13 is the last series supporting Python 3.8 as a control
node). Pin to `ansible-core==2.13.13`.

Note: the community `ansible` bundle uses different version numbers (6.x / 7.x)
and is large and source-heavy. Prefer `ansible-core`.

#### 3. Install the collections that hold the short module names

ansible-core is minimal and omits modules that legacy roles call by SHORT name.
Install the collections that contain them, pinned to the last series compatible
with ansible-core 2.13 / Python 3.8:

```bash
ansible-galaxy collection install \
  "community.general:>=5.0.0,<6.0.0" \
  "community.docker:>=2.0.0,<3.0.0"
```

- `community.general` provides `alternatives`, `locale_gen`, `htpasswd`.
- `community.docker` provides `docker_image`, `docker_compose`.

KEY FINDING: once a collection is on the search path, SHORT module names (e.g.
`alternatives:`) resolve automatically — you do NOT need to rewrite every task to
FQCN, and no `collections:` keyword is required. This keeps role edits at zero.

Collections install to the building user's `~/.ansible/collections`, which is in
the default `COLLECTIONS_PATHS`, so a root-built image finds them.

#### 4. Remove the `warn:` argument from command/shell tasks

2.13 removed the `warn:` arg under `command`/`shell`. Delete those
`args: { warn: "no" }` blocks. The arg only suppressed a now-gone warning, so
removing it changes nothing.

#### 5. Remove `when:` from individual vars_prompt entries

2.9 allowed `when:` on individual `vars_prompt` entries; 2.13 rejects it. Remove
the `when:` keys.

Behavior is preserved when the playbook is invoked with `--extra-vars` from a
config file, because `--extra-vars` has HIGHER precedence than `vars_prompt` — so
the always-shown prompts are overridden by the config values (pressing Enter is
harmless). Verify this precedence with a tiny test play before relying on it.

#### 6. Validate each fix in isolation

Run a throwaway container / test play for each change before the full run, so a
failure points at one variable rather than the whole upgrade.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| Keep `warn:` via 2.12 | Pinned `ansible-core 2.12.10` to retain the `warn:` arg | Wheel build failed a conflict check (stale `ansible 2.9` present) and 2.12 ships source-only on this env | 2.13.x ships prebuilt wheels and installs cleanly; accept removing the 2 `warn:` lines instead |
| Test on bare alpine | Tested module resolution / install on a bare `python:3.8-alpine` | `cffi` / `ansible-core` failed to build (no `gcc` / `libffi-dev`) | The real Dockerfile installs build-deps first; test in a context that mirrors the real build (deps present) or inside the existing image |
| Assumed FQCN required | Assumed short collection module names would NOT resolve without FQCN | They DO resolve once the collection is on the path | Don't rewrite roles to FQCN unnecessarily |

## Results & Parameters

### Dockerfile snippet

```dockerfile
ENV ANSIBLE_VERSION 2.13.13
RUN pip install ansible-core==${ANSIBLE_VERSION} \
 && ansible-galaxy collection install \
      "community.general:>=5.0.0,<6.0.0" \
      "community.docker:>=2.0.0,<3.0.0"
```

After changing a baked-in image, force a rebuild (remove the old tagged image
`<image>:<tag>`) since "build if missing" is a no-op when the image already
exists.

### Version pins

| Component | Pin | Why |
| --------- | ---- | ---- |
| `ansible-core` | `==2.13.13` | Last series supporting Python 3.8 control node; ships prebuilt wheels |
| `community.general` | `>=5.0.0,<6.0.0` | Provides `alternatives`, `locale_gen`, `htpasswd`; last series compatible with ansible-core 2.13 |
| `community.docker` | `>=2.0.0,<3.0.0` | Provides `docker_image`, `docker_compose`; last series compatible with ansible-core 2.13 |
| Mitogen | `0.3.x` | Requires `ansible-core >= 2.10` |

### Variable precedence reminder

```text
--extra-vars  >  vars_prompt  >  group_vars  >  role defaults
```

This is why deleting `vars_prompt` `when:` keys is safe when invoking with
`--extra-vars` from a config file: the config values win, and the now
always-shown prompts are overridden.

### Verification checklist

- [ ] Mitogen no longer aborts (`ansible-core >= 2.10` confirmed)
- [ ] `ansible-core==2.13.13` installs as a wheel on the Python 3.8 base
- [ ] Short module names (`alternatives`, `docker_image`, `htpasswd`) resolve with no FQCN edits
- [ ] No `args: { warn: ... }` blocks remain under `command`/`shell`
- [ ] No `when:` keys remain on individual `vars_prompt` entries
- [ ] `--extra-vars` precedence over `vars_prompt` confirmed with a tiny test play
- [ ] Old image tag removed before rebuild so the new toolchain is actually baked in
