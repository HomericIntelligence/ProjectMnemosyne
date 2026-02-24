# Raw Session Notes

## Session Context

- Date: 2026-01-02
- Repository: ProjectOdyssey → ProjectScylla test fixtures
- Goal: Create 45 SWE-bench style test cases from PR history

## Industry Research

### SWE-bench Methodology

- Uses real GitHub issues/PRs as benchmark tasks
- 2,294 problems from 12 Python repos in original SWE-bench
- Key insight: Use parent commit as starting state, PR as ground truth

### Key Metrics

- **Pass-Rate**: `correct_solutions / total_attempts`
- **Impl-Rate**: `satisfied_requirements / total_requirements`
- **Cost-of-Pass (CoP)**: `total_cost / pass_rate`

### Sources Consulted

- [SWE-Bench Methodology](https://medium.com/@sulbha.jindal/swe-benchmark-llm-evaluation-in-software-engineering-setting-52f315b2de5a)
- [Evidently AI: LLM Coding Benchmarks](https://www.evidentlyai.com/blog/llm-coding-benchmarks)
- [Symflower: Benchmarks for LLM Agents](https://symflower.com/en/company/blog/2025/benchmarks-llm-agents/)

## PR Selection Data

### Build System (5 PRs)

| PR # | Title | Parent Commit | LOC |
|------|-------|---------------|-----|
| 2976 | feat: add mypy to pixi | 8e59e100d11e760a28693796a504e9a864051e83 | 4 |
| 2972 | chore(docker): bump ubuntu 22.04→24.04 | 66628858c553abed2fdcb5f4b0bbdefc764d289c | 6 |
| 2962 | fix(docker): install gh/claude as root | e8a470059158a399b99e24170bf7bba47f4e3a02 | 17 |
| 2864 | fix(examples): prelu_activation.mojo | 4272caba362d26f639d3ddbc3f5fcdef5f9b2747 | 109 |
| 2844 | Simplify justfile | 6f6959bfc67614ce541cb28fb337f4161270ca63 | 1011 |

### CI/CD (5 PRs)

| PR # | Title | Parent Commit | LOC |
|------|-------|---------------|-----|
| 3000 | chore(ci): bump github-actions | d61b7e047d00174f8914241ed8a0d35828b3ce92 | 12 |
| 2982 | fix(ci): lowercase Docker SBOM | 3360ae74a88f7ed4f39949aa7f1858a8c08db3f8 | 3 |
| 2894 | Optimize batch extraction | 87a02fed42ba953163f1daf6f9751cd26fbe13f9 | 482 |
| 2969 | feat(ci/cd): Docker build workflow | ce739d4aa328f1c0815b33e2812c4b889868b740 | 669 |
| 2968 | feat(quality): code coverage infra | ea7dbf31ba70a5a85d76b1ab3d30cc1887d42ccb | 423 |

### Bug Fixing (5 PRs)

| PR # | Title | Parent Commit |
|------|-------|---------------|
| 3054 | fix(tests): remove unused out_shape | 050bcdc049c51e2ab112015cc57bc2fc24d98e11 |
| 3053 | fix: delete ralph loop | 1ab38fd8809554d148d420a4500c3856de482d36 |
| 2977 | fix(mypy): type annotations | ac9b7658757448347ecb5178108e69a3f4efe9bf |
| 2950 | Phase 1 Threading Fixes | 9c9f2a0dafba80c2bc91249f816e3cedf6c187c3 |
| 2960 | fix(scripts): slot management | 93c9fe9cf52f3913704c706496b5a254ca1eebd6 |

### New Features (5 PRs)

| PR # | Title | Parent Commit |
|------|-------|---------------|
| 3040 | feat(training): export modules | 1f83a291811f06f4939ee79c2361202948ea865d |
| 3020 | feat: claude code safety net | 011a3ff024954c0e15d0220bd67d72d6f74ffb64 |
| 3039 | feat(training): dataset_loaders | 33e1689820d3a8cfe547ceb34ea6556560ab5aa9 |
| 3027 | feat(autograd): gradient tracking | 0ff0c2a95ccbc800e47c7f78e1d8337d44392ea0 |
| 3022 | feat(core): FP32 accumulation | faa0ff097e172464ccd2d5528d92aae16f3ff38b |

### Refactoring (5 PRs)

| PR # | Title | Parent Commit |
|------|-------|---------------|
| 3024 | refactor: remove unused vars | 1a1a74758b3be246bde846d6c0ec18934814119d |
| 2984 | refactor: migrate to get_repo_root() | af62bf493b15e06ab412dae292ba2468daeada70 |
| 3035 | cleanup: FIXME/TODO references | 2b06d667fa7b51ce357cefa6954254d9f3aa1c88 |
| 2935 | refactor: layer parameter fixtures | 85acc0d86a3b39e6427def88d3ac60b1cabe930f |
| 2791 | refactor: extract backward ops | 601c5c86bf760fac17d213a867e882ab4f319a8e |

### Optimization (5 PRs)

| PR # | Title | Parent Commit |
|------|-------|---------------|
| 2770 | perf: tensor ops subtract_backward | 5bb122cd1163f04373552291240ba8d7e0cf569d |
| 2750 | perf: pre-allocate stride lists | 9c009fad15a29b33096d958df331018b1c58387b |
| 2936 | perf: @always_inline ops | 55ad174ae1fe0a8831fbefad33160425ca0db7fd |
| 2896 | perf: contiguous fast path | d24233c818a70b47b3cb3ae7d8a5d5942f1103d4 |
| 2774 | perf: eliminate Float64 conversions | 71a3c42263b4fdcee9e1dcaa793bc015497383da |

### Documentation (5 PRs)

| PR # | Title | Parent Commit |
|------|-------|---------------|
| 3057 | docs: from_array() status | 1ec9699bcc0f360eb290ab909abbaedcd07ebd6d |
| 3055 | docs: TODO→NOTE argv | 1f0ff3d0ce392ceecd4f20155b54c469b484cd15 |
| 2995 | docs: Mojo version update | 0878a2e285bb7c1dca106244dfc22091cac4b383 |
| 3029 | docs: year-end summary | fc71e3b1cac4beef20ed57eb8436994f25892f45 |
| 2991 | docs: migration guide | c47f5c6586f7af9ad13da4cd591bc42b43aac1e4 |

### Testing (5 PRs)

| PR # | Title | Parent Commit |
|------|-------|---------------|
| 3056 | test: enable eye() diagonal | dc9a74a94e5406b1d985e71159285b5aa3ddbdde |
| 3044 | cleanup: float16 FIXME→NOTE | 8fb66e59921ed2ec7bf635c45bce9401d5a4d8c1 |
| 3007 | test: implement_issues.py tests | fa1f2882fd7ac8c61f030374237d3cfeeae0164a |
| 3050 | test: visualization module | 45492f625b6ca8f7c9dd1468d9575da1187f7d12 |
| 2518 | test: model test suite | 0fe052906b9ac61483c4c7aed8aef0fd7a0643d9 |

### Issue Planning (5 Issues → Markdown Plans)

| Issue # | Title |
|---------|-------|
| 3094 | Document TrainingLoop bounds |
| 3093 | Review commented imports |
| 3086 | Document slicing behavior |
| 3085 | Enable Conv2D backward tests |
| 3083 | Implement RotatingFileHandler |

## Commands Used

```bash
# List merged PRs
gh pr list --state merged --limit 500 --json number,title,labels,additions,deletions

# Get merge commit
gh pr view <number> --json mergeCommit --jq '.mergeCommit.oid'

# Get parent commit
git rev-parse <merge-commit>^

# Get PR details
gh pr view <number> --json title,body,files

# Create test directories
mkdir -p test-XXX/expected
cp -r test-001/t0 test-001/t1 ... test-XXX/
```

## Files Created

1. `/home/mvillmow/ProjectOdyssey/.claude-plugin/marketplace.json` - Merged marketplace
2. 45 test case directories in `tests/fixtures/tests/test-003` through `test-047`
3. Each with: test.yaml, prompt.md, config.yaml, expected/criteria.md, expected/rubric.yaml, t0-t6/
