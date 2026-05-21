# paper-webpage-builder Pilot

Date: 2026-05-14

## Purpose

This pilot tested whether an existing Codex Skill directory can be onboarded into SitHub and used in a real GitHub PR loop.

Pilot repository:

- Local path: `/mnt/shared-storage-user/xuxinglong-p/paper-webpage-builder`
- GitHub: `https://github.com/xxllovemkm/paper-webpage-builder`
- PR loop: `https://github.com/xxllovemkm/paper-webpage-builder/pull/1`

## Starting State

The project already had real Skill content:

- `SKILL.md`
- `agents/openai.yaml`
- `assets/single-page-template.html`
- `references/design_principles.md`
- `references/module_patterns.md`
- `scripts/check_webpage_links.py`
- `scripts/convert_figures.sh`
- `scripts/scan_paper.py`

It did not have SitHub package metadata:

- no `skill.yaml`
- no `schemas/`
- no `tests/golden.jsonl`
- no `reports/`
- no GitHub Actions SitHub workflow

Running `sit info` initially failed because `skill.yaml` was missing.

## Onboarding Changes

The pilot added the minimum SitHub package surface:

- `skill.yaml`
- `schemas/input.schema.json`
- `schemas/output.schema.json`
- `tests/golden.jsonl`
- `reports/sithub-onboarding.md`
- `reports/sithub-onboarding.html`
- `reports/ci-onboarding/`
- `.github/pull_request_template.md`
- `.github/workflows/sit-ci.yaml`

The output contract describes the expected webpage generation result:

- `index_html_path`
- `modules`
- `assets`
- `validation`
- `risks`

The golden cases cover:

- LaTeX paper project page generation
- PDF plus assets page generation

## Local Validation

The onboarded project passed:

```bash
sit validate
sit test
sit info
sit report --format html --output reports/sithub-onboarding.html
sit ci-summary --artifact-dir reports/ci-onboarding
```

Observed result:

- validation passed
- golden tests passed
- `2/2` initial cases passed
- SitHub reports were generated locally

## PR Loop Experiment

A real branch was created:

```bash
experiment/sithub-pr-loop
```

The branch made a small Skill contract change:

- version `0.1.0 -> 0.2.0`
- `SKILL.md` output expectations added quality checks
- `schemas/output.schema.json` added optional `quality_checks`
- `tests/golden.jsonl` added `existing-webpage-refresh`

Local SitHub output:

- `sit validate`: pass
- `sit test`: pass, `3/3 golden cases passed`
- `sit diff main..HEAD`: `RISK review-required`
- suggested version bump: `minor`
- `sit commit`: version gate passed

GitHub PR:

- `https://github.com/xxllovemkm/paper-webpage-builder/pull/1`

GitHub Actions:

- initial run failed because `OpenRaiser/SitHub` was private and CI could not install `sit`
- after making `OpenRaiser/SitHub` public, rerun succeeded
- `Install sit`, `sit validate`, `sit test`, `ci-summary`, and artifact upload all passed

## Product Findings

This pilot changed the near-term priority.

The most important missing capability is not more schema keywords. It is onboarding support for existing Skill projects.

Concrete needs:

- a documented `SKILL.md` to SitHub package onboarding path
- a local readiness check
- clearer handling for generated reports during PR loops
- a stable install path for GitHub Actions

## Resulting Product Requirements

Near-term:

- `docs/quickstart-existing-skill.md`
- `sit doctor`
- `sit onboard`

Later:

- clearer report artifact policy
- stable install/distribution path, ideally package release instead of installing from GitHub source
