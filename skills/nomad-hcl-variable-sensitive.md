---
name: nomad-hcl-variable-sensitive
description: "Use when: (1) Nomad HCL job spec fails to parse with 'An argument named sensitive is not expected here', (2) variable blocks in .nomad.hcl files contain sensitive = true, (3) migrating Terraform variable patterns to Nomad."
category: ci-cd
date: 2026-04-23
version: "1.0.0"
user-invocable: false
verification: verified-ci
tags: [nomad, hcl, variable, sensitive, terraform, job-spec]
---

# Nomad HCL Variable `sensitive` Attribute Not Supported

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-04-23 |
| **Objective** | Fix Nomad HCL parse error caused by unsupported `sensitive` attribute in variable blocks |
| **Outcome** | Removed `sensitive = true` from variable blocks; Nomad parsed job spec correctly |
| **Verification** | verified-ci |

## When to Use

- Nomad job spec (`.nomad.hcl`) fails to validate or plan with an argument error
- Error message: `An argument named 'sensitive' is not expected here`
- `variable` blocks in `.nomad.hcl` files contain `sensitive = true`
- Migrating job specs written by someone familiar with Terraform to Nomad
- Code review of Nomad HCL that copied Terraform variable patterns

## Verified Workflow

### Quick Reference

```bash
# Find all sensitive = true in Nomad HCL files
grep -rn "sensitive" nomad/

# Remove them — sensitive is Terraform-only, not valid in Nomad variable blocks
# Before:
variable "anthropic_api_key" {
  type        = string
  description = "Anthropic API key"
  sensitive   = true   # INVALID in Nomad
}

# After:
variable "anthropic_api_key" {
  type        = string
  description = "Anthropic API key"
}
```

### Detailed Steps

1. Search for `sensitive` in all Nomad job files:
   ```bash
   grep -rn "sensitive" nomad/ --include="*.hcl" --include="*.nomad"
   ```

2. Remove `sensitive = true` from each `variable` block.

3. Validate the corrected spec:
   ```bash
   nomad job validate nomad/mesh.nomad.hcl
   # or via CI: nomad job plan -var-file=nomad/vars.hcl nomad/mesh.nomad.hcl
   ```

4. If secrets are needed in Nomad, use Vault integration instead:
   ```hcl
   # Nomad-native secret handling via Vault:
   template {
     data = <<EOF
   {{ with secret "secret/data/anthropic" }}
   ANTHROPIC_API_KEY={{ .Data.data.api_key }}
   {{ end }}
   EOF
     destination = "secrets/env.sh"
     env         = true
   }
   ```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| Keeping `sensitive = true` in Nomad variable blocks | Assumed Nomad HCL supports same variable attributes as Terraform | Nomad 1.9.7 HCL parser rejects: `An argument named 'sensitive' is not expected here` | `sensitive` is a Terraform/OpenTofu-only attribute; Nomad variable blocks only support `type`, `description`, and `default` |

## Results & Parameters

### Nomad Variable Block — Valid Attributes

```hcl
variable "example" {
  type        = string      # valid
  description = "..."       # valid
  default     = "value"     # valid
  # sensitive = true        # INVALID — Terraform only
}
```

### Nomad vs Terraform Variable Block Comparison

| Attribute | Terraform | Nomad |
| ----------- | ----------- | ------- |
| `type` | Yes | Yes |
| `description` | Yes | Yes |
| `default` | Yes | Yes |
| `sensitive` | Yes | **No — parse error** |
| `validation {}` | Yes | No |
| `nullable` | Yes | No |

### Error Message Pattern

```
Error: Unsupported argument

  on mesh.nomad.hcl line 12, in variable "anthropic_api_key":
  12:   sensitive = true

An argument named "sensitive" is not expected here.
```

### Handling Secrets in Nomad (Without `sensitive`)

Nomad does not expose a `sensitive` attribute for variables because Nomad's recommended secret pattern uses Vault or environment variables injected at runtime, not the job spec itself. Options:

1. **Vault integration** (recommended): Use `template` stanza with `{{ with secret }}` to pull secrets at task start
2. **`-var` flag at plan/run time**: Pass secret vars on the CLI (`nomad job run -var="key=value"`) — they are not stored in the job spec
3. **Environment variables on the Nomad agent**: Set `NOMAD_VAR_<name>` on the client nodes

## Verified On

| Project | Context | Details |
| --------- | --------- | --------- |
| AchaeanFleet | CI repair — nomad/mesh.nomad.hcl rejected by Nomad 1.9.7 parser | 2026-04-23; CI passed after removing sensitive = true from all variable blocks |
