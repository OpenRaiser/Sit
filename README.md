# sit

**Git-native versioning for AI Skill packages.**

`sit` adds a semantic layer on top of Git for AI Skills — prompts, schemas, golden tests, runners, and release artifacts. It classifies changes by risk, generates reviewer-ready diffs, and gates commits and releases.

## Why sit?

| | Pure Git | sit |
|---|---|---|
| Prompt change | `+13 -2` lines | "Prompt changed (+13 -2); headings: Core Rule, Workflow" |
| Schema update | raw JSON diff | "breaking" vs "review-required" classification |
| Golden tests | manual or none | `sit test .` runs stored cases; `--run` calls your runner |
| Version bump | gut feeling | risk-based gate: patch/minor/major suggested by change type |
| PR review | read every file | `sit pr-summary` generates structured Markdown |

## Install

```bash
pip install sit-toolkit
sit --version
```

Python 3.10+ required. Or install from source:

```bash
git clone https://github.com/OpenRaiser/SitHub.git
cd SitHub
pip install -e .
```

## Quick Start

```bash
# Create a new Skill package
sit init my-skill
cd my-skill

# Or standardize an existing project
cd /path/to/existing-project
sit standardize .

# Validate and test
sit validate .
sit test .

# See what changed
sit diff HEAD~1..HEAD

# Generate a PR summary
sit pr-summary HEAD~1..HEAD

# Release with a version gate
sit release minor . --bundle
```

## Commands

| Command | What it does |
|---|---|
| `sit init <name>` | Create a new Skill package |
| `sit standardize .` | Convert an existing project into a standard Skill package |
| `sit onboard .` | Conservatively add sit files to a `SKILL.md` project |
| `sit doctor .` | Check onboarding readiness |
| `sit validate .` | Validate manifest, schemas, and golden cases |
| `sit test .` | Run golden tests |
| `sit test . --run` | Run cases through your configured runner |
| `sit diff A..B` | Semantic diff for Git refs |
| `sit diff A..B --prompt` | Include prompt/reference text diff |
| `sit pr-summary A..B` | Generate PR-ready Markdown |
| `sit report . --compare A..B` | Generate Markdown/JSON/HTML report |
| `sit ci-summary . --compare A..B` | Generate GitHub Actions summary |
| `sit deps check .` | Check `deps.yaml` dependencies |
| `sit commit -m "..."` | Validate/test/version-gate before commit |
| `sit release minor . --bundle` | Bump version, tag, and write release bundle |

Git passthrough: `sit add`, `sit push`, `sit pull`, `sit branch`, `sit checkout`, `sit log`.

## Package Layout

```
my-skill/
  skill.yaml              # manifest
  prompts/system.md       # prompt files
  schemas/                # input/output JSON schemas
  tests/golden.jsonl      # golden test cases
  scripts/run_case.py     # optional runner
  assets/                 # scanned by semantic diff
  references/             # scanned by semantic diff
  CHANGELOG.md
```

## Semantic Diff Example

```
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
  - REFERENCE changed references/design_principles.md (+27 -3; headings: Design Principles, Fit the Paper)
```

## CI Integration

`sit init`, `sit standardize`, and `sit onboard` create a GitHub Actions workflow:

```bash
sit validate "$SIT_PACKAGE_DIR"
sit test "$SIT_PACKAGE_DIR"
sit test "$SIT_PACKAGE_DIR" --run
sit ci-summary "$SIT_PACKAGE_DIR" --compare origin/main..HEAD >> "$GITHUB_STEP_SUMMARY"
```

## Research

`sit` has been validated through multi-agent experiments on AI Skill packaging workflows. See:

- [Research proposal (H1-H4)](docs/research/proposal.md)
- [Multi-agent mapping](docs/research/sit-multi-agent-mapping.md)
- [H2 experiment results and analysis](experiments/)

## License

Apache-2.0. See [LICENSE](LICENSE).
