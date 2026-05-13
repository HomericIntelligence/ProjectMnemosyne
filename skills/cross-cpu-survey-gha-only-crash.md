---
name: cross-cpu-survey-gha-only-crash
description: "Fan a GHA-extracted container image out across a tailnet of physical machines spanning multiple CPU generations to narrow a 'GHA-only crash' bug class. Use when: (1) a CI failure reproduces only on GitHub-Actions runners and you suspect CPU-feature mismatch (AVX-512, BMI2, AMX, etc.), (2) you have ssh/Tailscale access to a fleet of personal/lab machines spanning different x86 microarchitectures, (3) you need to falsify a coarse hypothesis like 'any non-AVX-512 CPU triggers it' and narrow to a specific CPU+hypervisor class. Companion to extract-gha-container-image-cache-locally (which produces the image)."
category: debugging
date: 2026-05-12
version: "1.0.0"
user-invocable: false
verification: verified-local
tags: [cpu-feature, avx-512, podman, tailscale, multi-host, ci-debugging, jit, mojo, hyper-v, simd]
---

# Cross-CPU Survey of a GHA-Only Crash

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-05-12 |
| **Objective** | Determine the exact CPU-class boundary of a crash that only reproduces on GitHub-Actions runners, by replaying the same cached container image on a fleet of physically distinct CPUs. |
| **Outcome** | Successful. Surveyed 6 Intel CPUs spanning 2012-2024 (Sandy Bridge-E through Lunar Lake). All ran 0/50 SIGILLs on the same image where GHA crashed ~80%. Falsified the "any non-AVX-512 CPU triggers it" hypothesis and re-pointed the investigation at the GHA runner's AMD EPYC 9V74 (Zen 4) silicon under Hyper-V CPUID masking. |
| **Verification** | verified-local |

## When to Use

- A bug reproduces **only** on GitHub-Actions runners and you've already used [extract-gha-container-image-cache-locally](extract-gha-container-image-cache-locally.md) to obtain the failing image bytes.
- You suspect the crash is CPU-feature-sensitive (illegal-instruction SIGILL, JIT codegen mismatch, SIMD intrinsic crash) and need to pin down which CPU class actually triggers it.
- You have Tailscale (or plain ssh) access to a heterogeneous fleet of personal/lab machines spanning multiple x86 generations — ideally pre-AVX2, AVX2-only, AVX-512-capable, and at least one AMD part.
- A coarse hypothesis like "happens on any non-AVX-512 CPU" or "only on AMD" needs falsification before you escalate upstream.

**Do NOT use when:**
- The bug reproduces on your single dev box — you don't need a survey, you have a direct repro.
- You don't have access to a CPU fleet — investing in this is gated on having ≥3 distinct microarches.
- The crash is in source code that builds differently per host — the whole point is to run **bit-identical container bytes** across hosts.
- The vendor has already accepted the bug and is investigating — surveying is for the falsification phase, not for after a fix is in flight.

## Verified Workflow

### Quick Reference

```bash
# 0. Extract the failing image (companion skill)
gh workflow run extract-cached-image.yml --ref <branch>
RUN_ID=$(gh run list --workflow=extract-cached-image.yml --limit=1 --json databaseId --jq '.[0].databaseId')
gh run watch "$RUN_ID" && gh run download "$RUN_ID"

# 1. Set fleet
TARGETS="aeolus titan epimetheus apollo hermes"
JUMPHOST=epimetheus   # one host with broad lateral ssh access

# 2. Push the tar to the jumphost, then fan out
rsync -avz --partial container-image-*/dev.tar "${JUMPHOST}:~/dev.tar"
for host in $TARGETS; do
  [ "$host" = "$JUMPHOST" ] && continue
  ssh "$JUMPHOST" "scp ~/dev.tar ${host}:~/dev.tar" &
done; wait

# 3. Survey CPU + run reproducer on each host
for host in $TARGETS; do
  ssh "$JUMPHOST" "ssh $host '
    grep -m1 \"model name\" /proc/cpuinfo
    grep -o -E \"avx2|avx512[a-z]*\" /proc/cpuinfo | sort -u | tr \"\n\" \" \"; echo
    podman load -i ~/dev.tar >/dev/null
    cd ~/checkout-dir
    for i in $(seq 1 50); do
      podman run --rm --userns=keep-id \
        -v \"\$(pwd):/workspace:Z\" -w /workspace --ulimit core=-1 \
        projectodyssey:dev \
        bash -c \"pixi run mojo run repro/REPRO.mojo >/dev/null 2>&1; echo exit=\$?\"
    done | sort | uniq -c
  '"
done | tee survey-results.log

# 4. Tabulate (CPU, year, AVX2, AVX-512, Result) -> the deliverable
```

### Detailed Steps

1. **Pre-flight: confirm bit-identical bytes.** Verify the `dev.tar` sha256 against the manifest from the extract skill **before** distributing — you want every host running the exact same image, and a corrupted rsync can silently change one host's bytes.

   ```bash
   sha256sum container-image-*/dev.tar
   cat container-image-*/manifest.txt | grep "tar sha256"
   ```

2. **Pick a jumphost.** Choose one tailnet host that already has lateral ssh access to every target host with key-based auth. Running `scp` and remote ssh from the jumphost is dramatically faster than fanning out from your laptop (which would push the 2.7 GB tar over your home uplink N times). The jumphost only needs the tar once.

3. **Distribute the tar.** Use `rsync --partial` so an interrupted transfer can resume; the tar is large (~2.7 GB uncompressed). Don't compress in flight — the image is already compressed.

4. **Survey each host's `/proc/cpuinfo`** as part of the same ssh session that runs the reproducer, so the CPU metadata and the result are captured atomically and can't drift. Always capture: `model name`, year (look up separately), AVX2 presence, full AVX-512 family flags (`avx512f`, `avx512dq`, `avx512vl`, etc.), and the vendor (`Intel` vs `AuthenticAMD`).

5. **Run the reproducer N times per host.** A single run isn't enough — flaky crashes need ≥50 iterations to produce a meaningful crash rate. Capture exit codes via `echo exit=$?` and pipe through `sort | uniq -c` to get a histogram.

6. **Don't forget the hypervisor layer.** If a host shows surprising results, capture `systemd-detect-virt`, `dmesg | grep -i hypervisor`, and the full `/proc/cpuinfo` flags. On the GHA Azure runner, the silicon is Zen 4 (native AVX-512) but Hyper-V **masks** the AVX-512 CPUID bits — so userspace sees no AVX-512, but the silicon still executes those instructions when LLVM emits them based on CPU-name fingerprinting rather than CPUID probing.

7. **Build the survey table** and drop it into the upstream issue. The table itself is the deliverable — it's what falsifies hypotheses and points the vendor at the right CPU class.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| 1. `ssh-keyscan host` without `-t` | Ran plain `ssh-keyscan <tailnet-host>` to populate known_hosts before the survey | Default `ssh-keyscan` returned only `# host:port SSH-2.0-...` banner comments on Tailscale FQDN hosts, no actual key material. Subsequent ssh sessions failed with `Host key verification failed`. | Always specify key types explicitly: `ssh-keyscan -t ed25519,ecdsa,rsa host`. Plain `ssh-keyscan` without `-t` is unreliable on some SSH server configurations. |
| 2. `tailscale ssh` sharing `~/.ssh/known_hosts` | Assumed populating `~/.ssh/known_hosts` would let `tailscale ssh` connect | `tailscale ssh` reads its own file at `~/.cache/tailscale/ssh_known_hosts` and requires the FQDN form `<host>.<tailnet>.ts.net`. Even with that fixed, it may still refuse `mvillmow@<host>` if the target's `authorized_keys` isn't set up for the tailscale identity. | Either (a) copy the ed25519 entries from `~/.ssh/known_hosts` over to `~/.cache/tailscale/ssh_known_hosts` and use FQDN names, or (b) skip `tailscale ssh` and use plain `ssh` over Tailscale's MagicDNS shortnames instead. |
| 3. `podman run --userns=keep-id` on a docker-only host | Tried to use the exact same invocation on `apollo` (docker, no podman) by aliasing `podman=docker` | Docker doesn't support `--userns=keep-id`. Translating to `docker run -u $(id -u):$(id -g)` got further, but the bind-mounted workspace ownership still mismatched the container user, blocking writes to `.pixi/` cache dirs. | On docker-only hosts, mount the workspace **read-only** into a non-bound workdir (`-v "$(pwd):/src:ro"`), then `cp -r /src/* /tmp/work && cd /tmp/work` inside the container. The container then owns the working copy and pixi can write its cache. |
| 4. rsync'd only the reproducer file | Initial run pushed just `REPRO.mojo` to each host, expecting the container to bring the pixi env | The reproducer needs `pixi run` which needs `pixi.toml` in the current working directory. Without it: `error: could not find pixi.toml or pyproject.toml`. The container provides the env binaries, but pixi needs the project manifest visible at the bind mount. | Either (a) rsync the full repo skeleton (`pixi.toml`, `pixi.lock`, `pyproject.toml`, `shared/` package directory, and the reproducer), or (b) bake the reproducer **into** the image when building, removing the bind-mount dependency entirely. Option (b) is cleaner if you control the image build. |
| 5. `gh run download` blocked by 0-byte placeholder files | A previous run interrupted mid-download left zero-byte placeholder files in the target directory; retrying `gh run download` refused to overwrite | The CLI sees existing files of the same name and skips them silently, so the retry "succeeds" with empty files. | Always `rm -rf <artifact-dir>/` before retrying `gh run download`. Or use `gh run download <id> --dir <fresh-name>` to a brand-new directory. |
| 6. Trusting CPUID flags as ground truth | Initial hypothesis was "this crashes on every non-AVX-512 CPU" because the GHA runner's `/proc/cpuinfo` showed no AVX-512 flags | All 6 surveyed non-AVX-512 Intel CPUs ran 50/50 clean. The GHA runner crashed ~80%. The hypothesis was wrong because CPUID flags can be **masked by the hypervisor** while the underlying silicon still executes the instructions. | When surveying under hypervisors, capture `systemd-detect-virt` and check the vendor + microarchitecture of the actual silicon, not just CPUID flags. Hyper-V on Azure famously masks AVX-512 on AMD Zen 4 silicon. |

## Results & Parameters

### The deliverable: survey table format

This is the format that goes into the upstream bug report. Each row is one physical host; the contrast across rows is what falsifies hypotheses:

```text
| Host         | CPU                                  | Year | AVX2 | AVX-512 | Result      |
| ------------ | ------------------------------------ | ---- | ---- | ------- | ----------- |
| aeolus       | Intel i7-3820 (Sandy Bridge-E)       | 2012 | no   | no      | clean 50/50 |
| titan        | Intel i5-4440 (Haswell)              | 2013 | yes  | no      | clean 50/50 |
| epimetheus   | Intel i5-6600K (Skylake desktop)     | 2015 | yes  | no      | clean 50/50 |
| apollo       | Intel i7-8565U (Whiskey Lake)        | 2018 | yes  | no      | clean 50/50 |
| hermes       | Intel Core Ultra 7 258V (Lunar Lake) | 2024 | yes  | no      | clean 50/50 |
| GHA Azure    | AMD EPYC 9V74 (Zen 4) / Hyper-V      | -    | yes  | masked  | crashes ~80%|
```

Columns to always include:
- **Host**: friendly tailnet name (helps re-running later)
- **CPU**: full model string + microarch codename (codename is what LLVM fingerprints on)
- **Year**: release year of the microarch (helps a reader spot generational ranges)
- **AVX2 / AVX-512**: from `/proc/cpuinfo` flags
- **Result**: `clean N/N` or `crashes X/N` — never just "clean" or "crashes" without the denominator

If any host runs under a hypervisor, add a **Hypervisor** column and capture `systemd-detect-virt` output. Hypervisor CPUID masking is a major source of survey surprises.

### Fleet composition guidance

For maximum hypothesis-falsification power, aim for a fleet that spans:

| Slot | Why it matters |
| --- | --- |
| Pre-AVX2 Intel (Sandy Bridge or older) | Tests "is this purely an SIMD-instruction crash?" |
| AVX2-only Intel (Haswell-Skylake desktop) | Tests "is AVX2 alone enough to trigger?" |
| Modern Intel client (Tiger Lake+, no AVX-512) | Tests "is it new-Intel-no-AVX-512-specific?" |
| AMD Zen 2/3/4 bare-metal | Tests "is it AMD vendor-specific?" |
| Any CPU under a hypervisor (KVM/Hyper-V/VMware) | Tests "is CPUID masking the actual cause?" |

5-6 hosts spread across these slots is typically enough to falsify any "all CPUs of class X" hypothesis or to confirm the bug is narrower than you thought.

### Adjustment matrix

| If you don't have... | Substitute |
| --- | --- |
| Tailscale | Plain ssh over the public internet (slower distribution, same logic). Or run a VPN with WireGuard. |
| Podman on all hosts | Use whichever container runtime each host has; the image bytes are the same, only the invocation differs (see Failed Attempts row 3). |
| ≥5 distinct CPUs | Even 3 distinct microarches is enough to falsify many hypotheses. Lab/cloud rentals (Hetzner, OVH) provide bare-metal access to AMD Zen 2/3/4 for hourly cost. |
| `/proc/cpuinfo` access on a managed host | `lscpu`, `cpuid -1`, or `cat /sys/devices/cpu/caps/*` as fallbacks. |

## Verified On

| Project | Context | Details |
| --------- | --------- | --------- |
| ProjectOdyssey (HomericIntelligence) | modular/modular#6413 bisect, May 2026. Surveyed 6 distinct Intel CPUs (aeolus, titan, epimetheus, apollo, hermes + 1) spanning 2012-2024 via Tailscale. All ran 50/50 clean on the same `dev.tar` extracted from the failing GHA cache. The survey falsified the "any non-AVX-512 CPU" hypothesis and re-pointed the upstream issue at AMD-Zen4-under-Hyper-V CPUID masking. | Companion skills: [extract-gha-container-image-cache-locally](extract-gha-container-image-cache-locally.md), [symbolicate-mojo-cores-inside-container](symbolicate-mojo-cores-inside-container.md), [mojo-jit-emits-avx512-on-non-avx512-cpu](mojo-jit-emits-avx512-on-non-avx512-cpu.md). |

## References

- [extract-gha-container-image-cache-locally](extract-gha-container-image-cache-locally.md) — companion skill that produces the `dev.tar` you fan out
- [symbolicate-mojo-cores-inside-container](symbolicate-mojo-cores-inside-container.md) — companion skill for inspecting core dumps from the crashing runs
- [mojo-jit-emits-avx512-on-non-avx512-cpu](mojo-jit-emits-avx512-on-non-avx512-cpu.md) — the specific Mojo bug that this survey methodology validated
- [Hyper-V CPUID feature masking documentation](https://learn.microsoft.com/en-us/virtualization/hyper-v-on-windows/reference/tlfs)
