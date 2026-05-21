# Quickstart: Onboard an Existing Skill

This guide shows how to bring an existing Skill directory under SitHub control.

Use this when a project already has files such as:

- `SKILL.md`
- prompt/reference documents
- scripts
- examples
- generated outputs

SitHub does not replace those files. It adds a semantic control layer around them.

## 1. Start From a Git Repository

If the project is not a Git repository yet:

```bash
cd /path/to/existing-skill
git init -b main
git add .
git commit -m "feat: add existing skill"
git remote add origin https://github.com/OWNER/REPO.git
git push -u origin main
```

## 2. Run SitHub Onboarding

If the project is a loose prompt project, or you want a standard package layout with prompts copied under `prompts/`, run:

```bash
cd /path/to/existing-skill
sit standardize
```

`sit standardize` creates or fills:

- `skill.yaml`
- `prompts/`
- `schemas/input.schema.json`
- `schemas/output.schema.json`
- `tests/golden.jsonl`
- `.github/workflows/sit-ci.yaml`
- `.github/pull_request_template.md`
- `reports/sithub-standardization.md`
- `reports/sithub-standardization.html`

The generated schemas and golden case are draft contracts. They let `sit validate` and `sit test` run immediately, but they should be refined to match the Skill's real input/output behavior.

From the existing Skill directory:

```bash
cd /path/to/existing-skill
sit onboard
```

For a GitHub-backed project, pass the remote when the repository does not already have `origin`:

```bash
sit onboard --remote https://github.com/OWNER/REPO.git
```

`sit onboard` is conservative by default and is best for existing `SKILL.md` projects where you do not want to reorganize prompts:

- it requires `SKILL.md`
- it creates missing SitHub directories and files
- it augments an existing `skill.yaml` without replacing existing name/version/description values
- it does not overwrite generated files unless `--force` is used
- it initializes Git when the directory is not already a Git repository, unless `--no-git` is used
- it generates `reports/sithub-onboarding.md` and `reports/sithub-onboarding.html`
- it finishes by running the same checks as `sit doctor`

Then run:

```bash
sit doctor
sit validate
sit test
sit info
```

## 3. Manual Metadata Fallback

If you need to do the same process by hand, create `skill.yaml`:


```yaml
name: paper-webpage-builder
version: 0.1.0
description: Build polished single-page academic project webpages from paper sources.
prompts:
  skill: SKILL.md
schemas:
  input: schemas/input.schema.json
  output: schemas/output.schema.json
tests:
  golden: tests/golden.jsonl
runtime:
  model: configurable
  temperature: 0
tags:
  - codex-skill
  - sithub
```

The important part is that `prompts`, `schemas`, and `tests` point to files that exist.

## 4. Add Schemas

Create:

```text
schemas/input.schema.json
schemas/output.schema.json
```

The output schema should describe the result contract of the Skill. For example, a webpage builder can return:

- generated `index_html_path`
- page `modules`
- copied `assets`
- `validation` status
- remaining `risks`

## 5. Add Golden Cases

Create `tests/golden.jsonl`.

Each line is one deterministic case:

```json
{"case_id":"case-001","input":{"text":"hello"},"expected":{"answer":"hello"},"match_mode":"schema_only"}
```

Use `schema_only` first. It lets SitHub check that expected outputs conform to the output schema before you have a full execution harness.

## 6. Check Readiness

Run:

```bash
sit doctor
sit validate
sit test
sit info
```

Expected result:

- `sit doctor` reports package/Git/GitHub/CI readiness
- `sit validate` passes
- `sit test` passes
- `sit info` shows Git state and reports

## 7. Generate an Onboarding Report

```bash
mkdir -p reports
sit report --format html --output reports/sithub-onboarding.html
sit report --output reports/sithub-onboarding.md
sit ci-summary --artifact-dir reports/ci-onboarding
```

These reports prove the Skill can be observed and tested by SitHub.

## 8. Add GitHub Actions

Create `.github/workflows/sit-ci.yaml`:

```yaml
name: Skill CI
on: [pull_request]

env:
  SIT_PACKAGE_DIR: "."
  SIT_BASELINE_REF: "origin/${{ github.base_ref }}"
  SIT_HEAD_REF: "HEAD"
  SIT_ARTIFACT_DIR: "reports/ci"

jobs:
  validate-and-test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0
      - name: Install sit
        run: python -m pip install git+https://github.com/OpenRaiser/SitHub.git
      - run: sit validate "$SIT_PACKAGE_DIR"
      - run: sit test "$SIT_PACKAGE_DIR"
      - name: Write SitHub summary
        if: always()
        run: |
          sit ci-summary \
            --package-dir "$SIT_PACKAGE_DIR" \
            --baseline-ref "$SIT_BASELINE_REF" \
            --head-ref "$SIT_HEAD_REF" \
            --artifact-dir "$SIT_ARTIFACT_DIR" \
            >> "$GITHUB_STEP_SUMMARY"
      - name: Upload SitHub artifacts
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: sithub-report
          path: ${{ env.SIT_ARTIFACT_DIR }}
```

This requires `OpenRaiser/SitHub` to be publicly installable, or a private install token to be configured.

## 9. Run a PR Loop

Create a branch:

```bash
sit checkout -b experiment/sithub-pr-loop
```

Make a small Skill change, then run:

```bash
sit validate
sit test
sit diff main..HEAD
sit report . --compare main..HEAD --format html --output reports/pr-loop.html
sit pr-summary main..HEAD
sit commit -m "feat: update skill contract"
sit push -u origin experiment/sithub-pr-loop
```

Open a GitHub PR and confirm:

- Actions install `sit`
- `sit validate` passes
- `sit test` passes
- SitHub summary appears in the run summary
- `sithub-report` artifact is uploaded

## Current Limits

- By default, `sit test` validates golden expected/actual records against schema and match mode. To run the Skill itself, add a project runner and use `sit test --run`.
- Installing from GitHub source requires `OpenRaiser/SitHub` to be reachable from CI.
- `sit standardize` and `sit onboard` do not infer a domain-perfect schema yet. Treat the generated schemas and golden case as a safe starting point, then refine them for the Skill's real contract.
- Behavior regression requires a project runner. Add `commands.run_case` to `skill.yaml`, then use `sit test --run`.
