---
name: hi-branch-protection-two-layer
description: "HomericIntelligence main-branch protection is split across TWO layers (repo ruleset + classic branch protection) whose UNION GitHub enforces. Use when: (1) managing HI main-branch protection or deciding whether a rule belongs in a ruleset vs classic branch protection, (2) a PR is BLOCKED by a review/check that the ruleset reports as 0/absent (the OTHER layer adds it), (3) a ruleset PUT returns HTTP 422 on required_conversation_resolution, (4) `gh api .../branches/main/protection` 404 body gets parsed as fake required-check contexts."
category: ci-cd
date: 2026-05-31
version: "1.0.0"
user-invocable: false
verification: verified-ci
tags:
  - github
  - rulesets
  - branch-protection
  - classic-protection
  - required-signatures
  - conversation-resolution
  - linear-history
  - gh-api
---

# HomericIntelligence main Branch Protection: The Two-Layer Split

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-05-31 |
| **Objective** | Document the intentional two-layer (ruleset + classic) protection design on HI `main` and the gh-api gotchas encountered while auditing/applying it across all 15 repos |
| **Outcome** | Successful — both layers audited and applied live via `gh api` on all 15 HomericIntelligence repos; design and constraints confirmed |
| **Verification** | verified-ci (applied + verified live via gh api on all 15 HI repos, 2026-05-31) |

## When to Use

- You are managing HomericIntelligence `main`-branch protection and need to know where a given rule lives
- You must decide whether a new rule belongs in a **repo ruleset** vs **classic branch protection**
- A PR is `BLOCKED` by a review or status check that the **ruleset** reports as `0`/absent — the OTHER layer (classic) is adding it
- A ruleset PUT returns `HTTP 422: data matches no possible input` when you add `required_conversation_resolution`
- `gh api repos/<O>/<R>/branches/main/protection` returns a 404 body and you risk parsing its keys as fake required-check contexts
- You see fully-signed PRs with empty `reviewDecision` that still will not merge

Related: [[ci-cd-ruleset-bootstrap-deadlock]] (required-check names that exist only in the blocked PR), [[ci-cd-homeric-intelligence-merge-gotchas]] (squash-only, auto-merge behaviour), [[git-gpg-sign-email-mismatch-silent-unsigned-blocks-merge]] (`required_signatures` lives in the ruleset and silently blocks unsigned PRs).

## Verified Workflow

### Quick Reference

```bash
O=HomericIntelligence
R=ProjectAgamemnon   # any of the 15 HI repos

# (a) AUDIT BOTH LAYERS — GitHub enforces the UNION (stricter wins)
echo "=== RULESET (shared baseline) ==="
gh api repos/$O/$R/rulesets --jq '.[] | {id, name, target, enforcement}'
RID=$(gh api repos/$O/$R/rulesets --jq '.[0].id')
gh api repos/$O/$R/rulesets/$RID --jq '.rules[].type'
gh api repos/$O/$R/rulesets/$RID \
  --jq '.rules[] | select(.type=="required_status_checks") | .parameters.required_status_checks[].context'

echo "=== CLASSIC (repo-specific additions) ==="
# 404 GUARD: a repo with no classic protection returns {"message":"Branch not protected","status":"404"}
P=$(gh api repos/$O/$R/branches/main/protection 2>/dev/null)
if [ -z "$P" ] || echo "$P" | python3 -c 'import sys,json;d=json.load(sys.stdin);sys.exit(0 if str(d.get("status"))=="404" else 1)' 2>/dev/null; then
  echo "  (no classic protection)"
else
  echo "$P" | python3 -c 'import sys,json;d=json.load(sys.stdin);print("convo_resolution:",d.get("required_conversation_resolution",{}).get("enabled"));print("extras:",d.get("required_status_checks",{}).get("contexts",[]));print("reviews:",(d.get("required_pull_request_reviews") or {}).get("required_approving_review_count"))'
fi

# (b) COMPUTE EXTRAS = classic_contexts − ruleset_contexts (set difference)
python3 - "$RID" <<'PY'
import json, subprocess, sys
O,R,RID = "HomericIntelligence","ProjectAgamemnon",sys.argv[1]
rs = json.loads(subprocess.check_output(["gh","api",f"repos/{O}/{R}/rulesets/{RID}"]))
ruleset_ctx = set()
for rule in rs["rules"]:
    if rule["type"]=="required_status_checks":
        ruleset_ctx = {c["context"] for c in rule["parameters"]["required_status_checks"]}
raw = subprocess.run(["gh","api",f"repos/{O}/{R}/branches/main/protection"],capture_output=True,text=True).stdout
classic_ctx = set()
try:
    d = json.loads(raw)
    if str(d.get("status")) != "404":               # 404 GUARD
        classic_ctx = set(d.get("required_status_checks",{}).get("contexts",[]))
except Exception:
    pass
print("EXTRAS (classic-only):", sorted(classic_ctx - ruleset_ctx))
PY

# (c) ADD A VALID RULE TYPE TO ALL RULESETS (fetch → dedup → append → PUT)
# PUT is a FULL REPLACE of .rules — never PUT only the new rule.
for R in ProjectAgamemnon ProjectNestor ProjectMnemosyne ProjectHermes ProjectProteus \
         ProjectArgus AchaeanFleet Myrmidons ProjectTelemachy ProjectKeystone \
         ProjectOdyssey ProjectScylla ProjectHephaestus ProjectCharybdis Odysseus; do
  RID=$(gh api repos/$O/$R/rulesets --jq '.[0].id')
  gh api repos/$O/$R/rulesets/$RID > /tmp/rs.json
  python3 - <<'PY'
import json
rs=json.load(open("/tmp/rs.json"))
NEW={"type":"required_linear_history"}           # a VALID ruleset rule type
rules=[r for r in rs["rules"] if r["type"]!=NEW["type"]]   # dedup same type
rules.append(NEW)
json.dump({"name":rs["name"],"target":rs["target"],"enforcement":rs["enforcement"],
          "conditions":rs["conditions"],"bypass_actors":rs.get("bypass_actors",[]),
          "rules":rules}, open("/tmp/rs_patched.json","w"))
PY
  gh api -X PUT repos/$O/$R/rulesets/$RID --input /tmp/rs_patched.json --jq '.id'
done

# (d) SET CLASSIC = extras + conversation-resolution ONLY (no reviews, no linear-history)
cat > /tmp/prot.json <<'JSON'
{ "required_status_checks": {"strict": false, "contexts": ["validate","markdownlint"]},
  "required_pull_request_reviews": null,
  "enforce_admins": null,
  "restrictions": null,
  "required_conversation_resolution": true,
  "required_linear_history": false,
  "allow_force_pushes": false,
  "allow_deletions": false }
JSON
gh api -X PUT repos/$O/$R/branches/main/protection --input /tmp/prot.json
```

### Detailed Steps

1. **Always audit BOTH layers.** GitHub merges them and applies the **union** — the stricter setting
   across the two layers wins. A rule reported as `0`/absent in the ruleset can still be enforced by
   classic protection (and vice-versa).

2. **Know which layer owns each rule:**
   - **RULESET = the shared common baseline**, identical across all 15 repos (±minor per-repo
     variation in status-check contexts). Rule types present:
     `deletion, non_fast_forward, pull_request (required_approving_review_count=0),
     required_linear_history, required_signatures, required_status_checks`.
     Canonical contexts: `lint, unit-tests, integration-tests, security/dependency-scan,
     security/secrets-scan, build, schema-validation, deps/version-sync`.
   - **CLASSIC = repo-specific ADDITIONS only:** `required_conversation_resolution: true`
     (all repos) PLUS each repo's EXTRA required status-check contexts (the ones NOT already in
     the ruleset). NO reviews, NO linear-history in classic — those moved to the ruleset.

3. **`required_conversation_resolution` is classic-only.** It is NOT a valid repo-ruleset rule type.
   Putting `{"type":"required_conversation_resolution"}` into a ruleset PUT returns
   `HTTP 422: Invalid property /rules/N: data matches no possible input`. By contrast
   `required_linear_history` and `non_fast_forward` ARE valid ruleset rule types and work fine.

4. **Editing a ruleset is a FULL REPLACE.** `PUT repos/<O>/<R>/rulesets/<id>` with `{"rules":[...]}`
   replaces the entire rules array — it is not additive. Correct pattern: fetch the full ruleset,
   take `.rules`, drop any rule of the same type you are adding (dedup), append the new rule, then PUT
   `{"name","target","enforcement","conditions","bypass_actors","rules"}`. See snippet (c).

5. **Guard for the 404 before reading classic contexts.** A repo with no classic protection returns a
   404 JSON body `{"message":"Branch not protected","documentation_url":...,"status":"404"}`. A naive
   `--jq '.required_status_checks.contexts[]?'` is safe (yields nothing), BUT piping the whole body
   through code that extracts top-level keys yields FAKE contexts
   `["documentation_url","message","status"]` — which, if PUT back, permanently block all merges.
   Always check `.status == "404"` first. See snippet (a)/(b).

6. **Audit classic reviews independently.** Classic protection can require reviews even when the
   ruleset says `0`. Fix with:
   ```bash
   gh api -X PATCH repos/$O/$R/branches/main/protection/required_pull_request_reviews \
     -F required_approving_review_count=0
   ```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| Attempt 1 | Added `{"type":"required_conversation_resolution"}` to a repo ruleset and PUT it | `HTTP 422: Invalid property /rules/N: data matches no possible input` — it is not a valid ruleset rule type | `required_conversation_resolution` is **classic-only**; keep it in classic branch protection. (`required_linear_history` and `non_fast_forward` ARE valid ruleset types.) |
| Attempt 2 | PUT the ruleset with just the two new rules in `{"rules":[...]}` | Ruleset PUT REPLACES the entire `.rules` array — this would have dropped the entire shared baseline (signatures, status checks, etc.) | Ruleset edits are NOT additive. Always fetch existing `.rules`, dedup the same type, append, then PUT the full object. |
| Attempt 3 | Parsed `branches/main/protection` output for ProjectKeystone (which had NO classic protection) | The 404 body `{"message":...,"status":"404"}` was treated as data; its top-level keys became fake required contexts `documentation_url`/`message`/`status`, which if PUT back permanently block all merges | Always guard for `.status == "404"` (or empty/non-200) BEFORE extracting `required_status_checks.contexts`. This happened live on Keystone and had to be corrected. |
| Attempt 4 | Assumed the ruleset's `required_approving_review_count=0` meant no review gate anywhere | ProjectNestor's CLASSIC protection independently required `1` approving review, blocking ~18 fully-signed PRs that showed empty `reviewDecision` | Audit BOTH layers; the union wins. Fix Nestor with `PATCH .../branches/main/protection/required_pull_request_reviews -F required_approving_review_count=0`. |

## Results & Parameters

**Per-layer matrix (final state, all 15 HI repos, 2026-05-31):**

```text
LAYER 1 — RULESET (shared common baseline, identical on all 15 repos ±minor context variation)
  rule types:
    deletion
    non_fast_forward
    pull_request                  (required_approving_review_count = 0)
    required_linear_history
    required_signatures           ← this blocked the 5 unsigned PRs earlier in session
    required_status_checks        contexts: lint, unit-tests, integration-tests,
                                  security/dependency-scan, security/secrets-scan,
                                  build, schema-validation, deps/version-sync

LAYER 2 — CLASSIC branch protection (repo-specific ADDITIONS only)
  required_conversation_resolution = true          (ALL repos)
  required_pull_request_reviews    = null          (NO reviews — that lives in the ruleset)
  required_linear_history          = false         (lives in the ruleset)
  required_status_checks.contexts  = EXTRAS only    (classic_contexts − ruleset_contexts)

  EXTRAS per repo (examples):
    ProjectAgamemnon : ubuntu-24.04-{gcc,clang}-{debug,release},
                       "All Build/Test Checks", "All Static Analysis Checks"
    ProjectMnemosyne : validate, markdownlint
    ProjectHermes    : "Secret Scanning (gitleaks)", justfile-check
    ProjectProteus   : "Lint Shell Scripts"
    AchaeanFleet, Myrmidons, ProjectTelemachy, Odysseus : (empty — no extras)
```

**GitHub API behaviour (CRITICAL):**

```text
PUT ruleset with rules[] containing {"type":"required_conversation_resolution"}
  → HTTP 422: "Invalid property /rules/N: data matches no possible input"   ← classic-only rule

PUT ruleset with {"rules":[<only the new rule>]}
  → HTTP 200 but DESTROYS the baseline (full replace)                       ← always fetch+append

GET branches/main/protection on an unprotected repo
  → HTTP 404 body {"message":"Branch not protected","status":"404"}         ← guard before parsing keys

required_conversation_resolution / extra contexts → classic
required_signatures / reviews / linear_history / baseline checks → ruleset
```

**Classic protection PUT object for "extras + conversation-resolution only":**

```json
{
  "required_status_checks": {"strict": false, "contexts": ["<extras>"]},
  "required_pull_request_reviews": null,
  "enforce_admins": null,
  "restrictions": null,
  "required_conversation_resolution": true,
  "required_linear_history": false,
  "allow_force_pushes": false,
  "allow_deletions": false
}
```
(Use `"required_status_checks": null` if the repo has no extras.)

**Cross-references:** `required_signatures` (ruleset) is what silently blocked 5 unsigned PRs earlier in
this session — see [[git-gpg-sign-email-mismatch-silent-unsigned-blocks-merge]]. For squash-only
merge behaviour and auto-merge gotchas see [[ci-cd-homeric-intelligence-merge-gotchas]]. For required
check names that exist only in the blocked PR (a different deadlock) see
[[ci-cd-ruleset-bootstrap-deadlock]].

## Verified On

| Project | Context | Details |
| --------- | --------- | --------- |
| HomericIntelligence (all 15 Project* repos) | Session 2026-05-31 | Both layers audited and applied live via `gh api`; union confirmed; ProjectKeystone 404-body fake-context trap hit and corrected; ProjectNestor classic `required_approving_review_count=1` blocked ~18 signed PRs and was patched to 0 |
