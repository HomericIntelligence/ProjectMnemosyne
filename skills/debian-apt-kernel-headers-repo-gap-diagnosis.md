---
name: debian-apt-kernel-headers-repo-gap-diagnosis
description: "Diagnose apt-get install --only-upgrade linux-headers-amd64 failing with an unmet-dependency / held-broken-packages error on Debian/PureOS, and distinguish a genuine upstream repository publish gap from a local hold/pin misconfiguration. Use when: (1) apt reports 'Depends: linux-headers-<version> but it is not installable', (2) apt says 'you have held broken packages' but apt-mark showhold is empty, (3) linux-headers-amd64 cannot upgrade even though linux-image-amd64 upgraded fine."
category: debugging
date: 2026-07-04
version: "1.0.0"
user-invocable: false
verification: verified-local
tags:
  - apt
  - apt-get
  - apt-cache
  - dpkg
  - linux-headers
  - kernel
  - debian
  - pureos
  - unmet-dependencies
  - homelab
---

# Debian apt Kernel Headers Repository Gap Diagnosis

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-07-04 |
| **Objective** | Diagnose `apt-get install --only-upgrade linux-headers-amd64` failing with an unmet-dependency error on a Debian/PureOS homelab server (kernel 4.19.0-24-amd64) |
| **Outcome** | Successful diagnosis — confirmed a genuine upstream repository publish gap (distro had not yet published the versioned headers package matching the newest kernel ABI), not a local hold/pin problem |
| **Verification** | verified-local — diagnosed and confirmed via live `apt-cache policy`/`dpkg -l`/`apt-mark showhold` output on the affected host |

## When to Use

- `apt-get install --only-upgrade linux-headers-amd64` (or a plain `apt-get upgrade`) fails with `Depends: linux-headers-<version>-<arch> but it is not installable`
- apt also prints `E: Unable to correct problems, you have held broken packages.` even though nothing was manually held
- You need to decide whether this is a local misconfiguration (hold, pin, broken sources.list) worth "fixing" immediately, or a genuine gap in the distro's published packages that will self-resolve
- `linux-image-amd64` appears to already be at the latest candidate version while `linux-headers-amd64` is stuck

## Verified Workflow

### Quick Reference

```bash
uname -r                                          # confirm the running kernel's exact ABI string
apt-cache policy linux-headers-amd64              # compare Installed vs Candidate version
apt-cache policy linux-headers-$(uname -r)        # THE key check: if "Candidate: (none)", the exact
                                                   # versioned package genuinely does not exist in any
                                                   # configured repo -- smoking gun for an upstream gap
dpkg -l | grep -E 'linux-(image|headers)'         # list all installed kernel image/header packages --
                                                   # confirms whether -amd64 (image) is already current
                                                   # even though -headers-amd64 (meta) is stuck
apt-mark showhold                                 # rule out a manual hold
```

### Detailed Steps

1. **Confirm the running kernel's exact ABI string:**

   ```bash
   uname -r
   # e.g. 4.19.0-24-amd64
   ```

2. **Check the meta-package's dependency chain.** `linux-headers-amd64` is a meta-package
   that always depends on an exact versioned headers package matching the currently
   installed/target kernel ABI (e.g. `linux-headers-4.19.0-24-amd64`), not a generic
   "any headers" dependency:

   ```bash
   apt-cache policy linux-headers-amd64
   ```

3. **Run the decisive check** — query `apt-cache policy` for the *exact* versioned package
   name that the meta-package depends on:

   ```bash
   apt-cache policy linux-headers-$(uname -r)
   ```

   - If this returns a real `Candidate:` version with a populated version table, the
     problem is local (priority/pin/sources.list) — investigate `apt-cache policy` output
     and `/etc/apt/preferences.d/`.
   - If this returns `Installed: (none)` / `Candidate: (none)` with an **empty** version
     table, the package has genuinely never been published to any configured repo. This
     is proof of an upstream gap, not a local problem.

4. **Cross-check the actual kernel image version**, not just the headers meta-package:

   ```bash
   dpkg -l | grep -E 'linux-(image|headers)'
   ```

   If `linux-image-amd64` (or the specific versioned image package) is already at the
   latest candidate version, the real, security-relevant kernel binary is already fully
   patched — only the (lower-stakes) compile-time headers metapackage is stuck one
   revision behind. This distinction determines priority: a stuck kernel *image* is
   urgent (unpatched running kernel); a stuck headers package alone is not.

5. **Rule out a manual hold or pin** before concluding it's an upstream gap:

   ```bash
   apt-mark showhold
   ```

   Empty output plus no pinning file rules out the "local misconfiguration" hypothesis
   entirely, leaving "upstream hasn't published the matching headers package yet" as the
   only remaining explanation.

6. **Resolution — do not force it.** Headers are only needed to compile out-of-tree/DKMS
   kernel modules (e.g. VirtualBox, some GPU/wifi drivers) and carry no runtime security
   exposure on their own. Do NOT:
   - manually download/install a mismatched `.deb` for a different kernel ABI revision
   - hold or remove `linux-headers-amd64`
   - add unofficial/third-party repos to chase the missing package

   Instead, leave it and retry a plain `apt-get update && apt-get upgrade` after the
   distro's next point release — the repo typically backfills the missing headers package
   within days. Always separately confirm `linux-image-amd64` is current before
   deprioritizing this (Step 4) — if the image itself were ALSO stuck, this would be a
   much higher-priority unpatched-kernel situation instead of a cosmetic headers gap.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Assumed local hold/pin problem | Suspected `apt-mark hold` or an `/etc/apt/preferences.d/` pin was blocking the upgrade, based on the alarming "you have held broken packages" wording | `apt-mark showhold` returned empty and no pinning override existed — there was nothing local to unhold or unpin | The "held broken packages" message is generic apt phrasing for any unresolved dependency, not proof of an actual `apt-mark hold`; always verify with `apt-mark showhold` before assuming a local hold |
| Read `apt-cache policy linux-headers-amd64` only | Checked only the meta-package's policy output, which shows a plausible-looking Candidate line for the meta-package itself | The meta-package's own candidate always resolves fine; the failure is buried one level down in its versioned dependency, which is invisible unless queried directly | Always run `apt-cache policy` against the *exact* versioned package name from the error message (`linux-headers-$(uname -r)`), not just the meta-package |

## Results & Parameters

**Environment:** Debian/PureOS homelab server, kernel `4.19.0-24-amd64`

**Failing command:**

```bash
apt-get update && apt-get install --only-upgrade -y linux-headers-amd64
```

**Observed error:**

```text
The following packages have unmet dependencies:
 linux-headers-amd64 : Depends: linux-headers-4.19.0-24-amd64 but it is not installable
E: Unable to correct problems, you have held broken packages.
```

**Decisive diagnostic output:**

```text
$ apt-cache policy linux-headers-4.19.0-24-amd64
linux-headers-4.19.0-24-amd64:
  Installed: (none)
  Candidate: (none)
  Version table:
```

**Cross-check confirming the kernel image was already current:**

```text
$ dpkg -l | grep -E 'linux-(image|headers)'
ii  linux-image-amd64   4.19+105+deb10u19   amd64   Linux for 64-bit PCs (meta-package)
ii  linux-headers-4.19.0-23-amd64   ...      (one revision behind; -24 headers not published)
```

**Root cause:** the distro's security repo (PureOS's `amber-security`) had published and
installed the newer `linux-image-amd64` kernel ABI revision (`-24`, at candidate version
`4.19+105+deb10u19`) but had not yet published a matching versioned
`linux-headers-4.19.0-24-amd64` package for that same ABI revision — an incomplete
point-release publish on the distro/repo side, not a local misconfiguration.

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| apollo (homelab) | PureOS/Debian server, 2026-07-04 | Confirmed via live `apt-cache policy`/`dpkg -l`/`apt-mark showhold`; no fix applied — left to self-resolve on next point release |
