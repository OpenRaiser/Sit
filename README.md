<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/OpenRaiser/Sit/main/.github/assets/brand/sit-logo-horizontal-concept-dark.png">
    <source media="(prefers-color-scheme: light)" srcset="https://raw.githubusercontent.com/OpenRaiser/Sit/main/.github/assets/brand/sit-logo-horizontal-concept-light.png">
    <img src="https://raw.githubusercontent.com/OpenRaiser/Sit/main/.github/assets/brand/sit-logo-horizontal-concept-light.png" alt="sit semantic safety for AI skills" width="640">
  </picture>
</p>

[English](README.md) | [中文](README_zh.md)

**A Git-native safety layer for AI agents that edit prompts, schemas, scripts, and Skill packages.**

Git can tell you that a prompt changed. `sit` tells you whether that change is a typo fix, a behavior change, a schema contract change, a test update, or a release risk.

```bash
pip install sit-toolkit
sit diff HEAD..WORKTREE
sit review HEAD..WORKTREE
```

Use `sit` when humans or AI agents evolve reusable skills and you need semantic diffs, golden tests, version gates, PR reviews, and reproducible releases without replacing Git.

![sit turns raw Git diffs into semantic Skill review signals](https://raw.githubusercontent.com/OpenRaiser/Sit/main/.github/assets/brand/sit-readme-hero-flat.png)

## Why sit?

AI Skill packages are not just text prompts. A real Skill often contains:

- `SKILL.md` and reference instructions
- input/output JSON schemas
- golden behavior tests
- validation and asset scripts
- release reports and reproducibility bundles

Plain Git sees file lines. `sit` understands the Skill surface:

```text
SCHEMA output property added keywords (optional)
GOLDEN expected changed latex-project-page
GOLDEN expected changed pdf-with-assets-page
GOLDEN expected changed existing-webpage-refresh
Risk: review-required
Suggested version bump: minor
Golden tests: pass
```

The example above comes from a real package, [paper-webpage-builder](https://github.com/xxllovemkm/paper-webpage-builder), where an agent-facing paper webpage Skill changed its output contract and expected behavior. `sit` turned the change into a reviewable PR signal instead of leaving reviewers to infer intent from raw diffs.

![paper-webpage-builder case: Git sees lines, sit sees behavior](https://raw.githubusercontent.com/OpenRaiser/Sit/main/.github/assets/brand/sit-case-paper-webpage-builder-flat.png)

## 60-second demo

Start with an existing prompt or Skill project:

```bash
pip install sit-toolkit
sit standardize .
sit validate .
sit test .
sit diff HEAD..WORKTREE
sit review HEAD..WORKTREE
```

Or create a new Skill package:

```bash
sit init my-skill
cd my-skill
sit install-hooks .
```

When the Skill changes, commit through `sit`:

```bash
sit add .
sit commit --bump minor -m "improve webpage quality checks"
sit release minor . --bundle
```

Git remains the storage and history layer. `sit` adds the semantic layer: package structure, tests, diffs, version gates, PR summaries, and release reports.

## What sit catches

| Change | What sit reports |
|---|---|
| Prompt or reference edits | Changed headings, prompt summaries, behavior risk |
| JSON schema edits | Added/removed properties, required fields, enum changes, breaking risk |
| Golden test updates | Case-level expected output changes and pass/fail status |
| Script changes | CLI args, functions/classes/imports, external commands, review risk |
| Missing version bump | Required bump vs actual bump before commit/release |
| Local dependencies | `deps.yaml` compatibility and reverse-dependency hints |
| Release reproducibility | Bundle archive, sha256 manifest, `reproduce.sh` |

## Designed for agents

`sit` gives agents a concrete loop after they edit a Skill:

![sit agent safety loop](https://raw.githubusercontent.com/OpenRaiser/Sit/main/.github/assets/brand/sit-agent-loop-flat.png)

```bash
git status --short
sit validate .
sit test .
sit diff HEAD..WORKTREE
sit review HEAD..WORKTREE
```

One command adds project instructions and MCP configuration:

```bash
sit onboard --agent ./my-skill
```

This creates:

- `AGENTS.md` for Codex and other repository-aware agents
- `.mcp.json` for MCP-aware editors such as Claude Code and Cursor
- a local workflow that asks agents to validate, test, and review semantic changes before handing work back

### Agent interfaces

| Interface | Use it for |
|---|---|
| Auto-discovery | `sit onboard --agent` for Codex, Claude Code, Cursor, and similar tools |
| Python SDK | `from sit.sdk import Sit` for direct programmatic calls |
| MCP server | `pip install 'sit-toolkit[mcp]'` for 12 stdio tools |
| LLM tool-use schemas | `from sit.tool_use import get_tools_openai` for OpenAI/Anthropic-compatible tool definitions |

Python SDK example:

```python
from sit.sdk import Sit

s = Sit("./my-skill-package")
s.info()
s.validate()
s.test()
s.diff_range("HEAD..WORKTREE")
s.review_range("HEAD..WORKTREE")
s.report_range("HEAD..WORKTREE")
```

MCP config:

```json
{
  "mcpServers": {
    "sit": { "command": "sit-mcp-server" }
  }
}
```

## Core workflow

```bash
# Inspect package state
sit info .
sit doctor .

# Validate and test behavior
sit validate .
sit test .
sit test --run

# Review semantic changes
sit diff HEAD..WORKTREE
sit diff --staged
sit review main..HEAD
sit pr-summary main..HEAD
sit report . --compare main..HEAD --format html

# Commit and release safely
sit install-hooks .
sit commit --bump minor -m "update skill behavior"
sit release minor . --bundle
```

## CI integration

`sit init` generates a GitHub Actions workflow. You can also add the loop manually:

```yaml
- run: sit validate "$SIT_PACKAGE_DIR"
- run: sit test "$SIT_PACKAGE_DIR"
- run: sit test "$SIT_PACKAGE_DIR" --run
- run: sit ci-summary "$SIT_PACKAGE_DIR" --compare origin/main..HEAD >> "$GITHUB_STEP_SUMMARY"
```

Current package checks run on Python 3.10, 3.11, 3.12, and 3.13 with `ruff`, `mypy`, and `pytest`.

## Command map

**Lifecycle:** `sit init`, `sit standardize`, `sit onboard`, `sit doctor`

**Quality:** `sit validate`, `sit test`, `sit test --run`, `sit deps check`

**Diff and review:** `sit diff`, `sit review`, `sit pr-summary`, `sit report`, `sit ci-summary`

**Release and safety:** `sit install-hooks`, `sit commit`, `sit release`, `sit undo`

**Git passthrough:** `sit add`, `sit push`, `sit pull`, `sit branch`, `sit checkout`, `sit log`

## Installation

```bash
pip install sit-toolkit
```

Optional MCP support:

```bash
pip install 'sit-toolkit[mcp]'
```

Requirements:

- Python 3.10+
- Git
- Optional: an MCP-aware editor or agent runtime

## Project status

`sit` is currently focused on the local CLI and agent integration loop. It does not replace Git storage, branches, remotes, or merges. Git remains the source of truth; `sit` adds Skill-aware validation, semantic review, version gates, and release artifacts on top.

## License

Apache-2.0. See [LICENSE](LICENSE).
