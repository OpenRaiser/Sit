# SitHub / sit

`sit` is a Git-native CLI for versioning AI Skill packages: prompts, schemas, golden tests, runners, reports, and release artifacts.

Git records file changes. `sit` adds the semantic layer reviewers need:

- output schema changes are classified as breaking or review-required;
- prompt/reference changes get text summaries and optional unified diff;
- scripts, assets, and references are visible in semantic diff;
- golden tests can run statically or through a configured runner;
- commit/release gates check whether the version bump matches the change risk;
- PR, CI, HTML, and release reports are generated from the same payloads.

## Install

From this repository:

```bash
git clone https://github.com/OpenRaiser/SitHub.git
cd SitHub
python3 -m pip install -e .
sit --version
```

For local development without installing:

```bash
python3 -m sit.cli --version
```

Python 3.10+ is required.

## Quick Start

Create a new Skill package:

```bash
sit init my-skill
cd my-skill
```

Validate and test:

```bash
sit validate .
sit test .
```

Compare a Git range:

```bash
sit diff HEAD~1..HEAD
sit diff HEAD~1..HEAD --prompt
```

Generate reviewer output:

```bash
sit pr-summary HEAD~1..HEAD
sit report . --compare HEAD~1..HEAD --format html -o reports/review.html
sit ci-summary . --compare HEAD~1..HEAD
```

Release a version:

```bash
sit release minor . --bundle
```

## Package Layout

Typical package:

```text
my-skill/
  skill.yaml
  prompts/
    system.md
  schemas/
    input.schema.json
    output.schema.json
  tests/
    golden.jsonl
  scripts/
    run_case.py
  assets/
  references/
  reports/
  CHANGELOG.md
```

Minimal `skill.yaml`:

```yaml
name: my-skill
version: 0.1.0
description: Short description.

prompts:
  system: prompts/system.md

schemas:
  input: schemas/input.schema.json
  output: schemas/output.schema.json

tests:
  golden: tests/golden.jsonl

commands:
  run_case: "python3 scripts/run_case.py --input {input} --output {output}"
```

`scripts/`, `assets/`, and `references/` are scanned by semantic diff when present.

## Core Commands

| Command | Purpose |
|---|---|
| `sit init <name>` | Create a new Skill package. |
| `sit onboard .` | Add SitHub files to an existing `SKILL.md` project. |
| `sit doctor .` | Check onboarding readiness. |
| `sit info . --format json` | Inspect package, Git, validation, tests, and reports. |
| `sit validate .` | Validate manifest paths, schemas, and golden cases. |
| `sit test .` | Run golden tests against stored expected/actual values. |
| `sit test . --run` | Run each golden case through `commands.run_case`. |
| `sit diff A..B` | Semantic diff for Git refs. |
| `sit diff A..B --prompt` | Include prompt/reference unified text diff. |
| `sit pr-summary A..B` | Generate PR-ready Markdown. |
| `sit report . --compare A..B` | Generate Markdown/JSON/HTML report. |
| `sit ci-summary . --compare A..B` | Generate GitHub Actions summary Markdown. |
| `sit deps check .` | Check local `deps.yaml` dependencies. |
| `sit commit -m "..."` | Validate/test/version-gate before Git commit. |
| `sit release minor . --bundle` | Bump version, create release commit/tag, and write bundle. |

Git passthrough commands are also available: `sit add`, `sit push`, `sit pull`, `sit branch`, `sit checkout`, and `sit log`.

## Semantic Diff Example

```text
Skill Diff
Baseline: paper-webpage-builder@0.3.0
Current: paper-webpage-builder@0.4.0
Risk: review-required
Suggested version bump: minor

[prompt]
  - PROMPT changed skill: SKILL.md -> SKILL.md (+13 -2; headings: Paper Webpage Builder, Core Rule, Workflow)

[script]
  - SCRIPT changed scripts/scan_paper.py (review required; cover with runner or targeted tests)

[reference]
  - REFERENCE changed references/design_principles.md (+27 -3; headings: Design Principles, Fit the Paper, Avoid Template Cloning)
```

## CI

`sit init` and `sit onboard` create a GitHub Actions workflow that can run:

```bash
sit validate "$SIT_PACKAGE_DIR"
sit test "$SIT_PACKAGE_DIR"
sit test "$SIT_PACKAGE_DIR" --run
sit ci-summary "$SIT_PACKAGE_DIR" --compare origin/main..HEAD >> "$GITHUB_STEP_SUMMARY"
```

The CI summary and artifacts expose validation, golden test status, semantic diff risk, suggested version bump, and reproduce commands.

## Release Bundles

```bash
sit release patch . --bundle
```

The bundle includes package files, reports, `CHANGELOG.md`, `manifest.json` with sha256 entries, and `reproduce.sh`.

## Pilot Material

External trial kit:

- `docs/pilots/external-trial-kit.md`
- `docs/pilots/external-feedback-form.md`

Real pilot walkthrough:

- `docs/walkthrough.md`

## License

MIT
