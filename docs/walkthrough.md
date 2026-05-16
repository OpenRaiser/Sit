# SitHub Walkthrough: paper-webpage-builder

This walkthrough records the first real SitHub loop on an existing Skill project.

Skill repo:

```text
/mnt/shared-storage-user/xuxinglong-p/paper-webpage-builder
https://github.com/xxllovemkm/paper-webpage-builder
```

Key commits:

| Commit | Meaning |
|---|---|
| `70d5845` | Add runner-backed golden tests. |
| `1e7cfbf` | Add optional `keywords` output field. |
| `51fe1b4` | Merge PR #2. |
| `a4d0f92` | Strengthen paper webpage quality guidance after GGBench feedback. |

Current closure:

- PR #2 was merged: `https://github.com/xxllovemkm/paper-webpage-builder/pull/2`
- `experiment/sithub-pr-loop` has been pushed through `a4d0f92`.
- SitHub `main` includes resource-aware diff and release workflow hardening through `0.18.1`.

## 1. Onboard an Existing Skill

The project started as an existing `SKILL.md` repository. SitHub added the package surface:

```text
skill.yaml
schemas/input.schema.json
schemas/output.schema.json
tests/golden.jsonl
.github/workflows/sit-ci.yaml
.github/pull_request_template.md
reports/
```

Check readiness:

```bash
cd /mnt/shared-storage-user/xuxinglong-p/paper-webpage-builder
sit doctor .
sit validate .
sit test .
```

## 2. Add Runner-Backed Golden Tests

`skill.yaml` defines a deterministic runner:

```yaml
commands:
  run_case: "python3 scripts/sit_run_case.py --input {input} --output {output}"
```

Run both static and live regression checks:

```bash
sit test .
sit test . --run
```

Expected result:

```text
OK  latex-project-page: runner produced actual
OK  latex-project-page: partial match passed
OK  pdf-with-assets-page: runner produced actual
OK  pdf-with-assets-page: partial match passed
OK  existing-webpage-refresh: runner produced actual
OK  existing-webpage-refresh: partial match passed
SUMMARY 3/3 golden cases passed
```

Evidence:

```text
reports/real-runner-loop/sit-test-run.txt
reports/real-runner-loop/sit-test-run.json
reports/real-runner-loop/sit-test-run-failure.txt
```

## 3. Add an Optional Output Field

The branch `feature/add-keywords` added an optional output field:

```text
schemas/output.schema.json -> keywords
SKILL.md -> output expectations
scripts/sit_run_case.py -> deterministic output
tests/golden.jsonl -> expected partial matches
```

Because the schema change is review-required but not breaking, the version moved from `0.2.0` to `0.3.0`.

Run:

```bash
sit validate .
sit test .
sit test . --run
sit diff HEAD~1..HEAD --format plain
```

Observed semantic signal:

```text
SCHEMA output property added keywords (optional)
RISK review-required
```

Commit through the gate:

```bash
sit commit -m "schema: add keywords output field"
```

Observed gate:

```text
commit version gate passed: risk=review-required, required=minor, actual=minor, version=0.2.0->0.3.0
```

Created commit:

```text
1e7cfbf schema: add keywords output field
```

## 4. Generate Reviewer Artifacts

Use the Git range:

```bash
sit pr-summary HEAD~1..HEAD
sit report . --compare HEAD~1..HEAD
sit report . --compare HEAD~1..HEAD --format html -o reports/add-keywords-walkthrough/sit-report.html
sit ci-summary . --compare HEAD~1..HEAD
```

Saved artifacts:

```text
reports/add-keywords-walkthrough/diff.json
reports/add-keywords-walkthrough/diff.txt
reports/add-keywords-walkthrough/pr-summary.md
reports/add-keywords-walkthrough/sit-report.html
reports/add-keywords-walkthrough/sit-report.json
reports/add-keywords-walkthrough/sit-report.md
reports/add-keywords-walkthrough/sit-summary.md
reports/add-keywords-walkthrough/sit-test-run.json
reports/add-keywords-walkthrough/sit-test-run.txt
```

## 5. Push and Merge

The first push failed with GitHub 403 because credentials for two GitHub accounts collided.

Resolution:

```bash
git config credential.useHttpPath true
```

Then store path-specific credentials for:

```text
github.com/OpenRaiser/SitHub.git
github.com/xxllovemkm/paper-webpage-builder.git
```

The feature branch was pushed, PR #2 was created and merged:

```text
https://github.com/xxllovemkm/paper-webpage-builder/pull/2
51fe1b4 Merge PR #2: schema: add keywords output field
```

## 6. Close the Quality Feedback Loop

GGBench feedback exposed a real weakness in `paper-webpage-builder`:

- background design reused Pager-like grid patterns too often;
- main experiment tables and benchmark comparison tables were not always fully represented.

The skill was updated to require:

- target-paper-specific visual cue inventory;
- table ledger before design;
- full representation of central result/statistics/ablation tables;
- avoidance of template-cloned backgrounds.

Commit:

```text
a4d0f92 quality: strengthen paper webpage skill guidance
```

Validate:

```bash
sit validate .
sit test .
sit test . --run
sit diff HEAD~1..HEAD
```

With SitHub `0.18.x`, the same change now shows resource-aware events:

```text
PROMPT changed skill: SKILL.md -> SKILL.md
SCRIPT changed scripts/scan_paper.py (review required; cover with runner or targeted tests)
REFERENCE changed references/design_principles.md
REFERENCE changed references/module_patterns.md
RISK review-required
```

This closed the earlier observation gap where `scripts/scan_paper.py` changed but semantic diff did not mention it.

## What This Proved

- Existing `SKILL.md` repos can be onboarded without replacing Git.
- `sit test --run` can make Skill behavior regression testable.
- Optional output fields produce review-required/minor, not breaking/major.
- `sit commit` turns semantic diff into a version gate.
- `sit pr-summary`, `sit report`, and `sit ci-summary` give reviewers a stable summary.
- Resource-aware diff is necessary because scripts and references can change behavior as much as prompts.

## Remaining Follow-Up

- Run the external pilot kit with 2-3 real teams.
- Test whether schema requirements are too rigid for prompt-only or workflow-style projects.
- Use VS Code extension work to verify whether JSON outputs are sufficient for GUI workflows.
