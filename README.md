# sit

[English](README.md) | [中文](README_zh.md)

**Git-native versioning for AI Skill packages.**

`sit` puts prompts, schemas, golden tests, and release artifacts under semantic version control. It knows what changed, classifies risk, and gates your commits and releases.

```bash
pip install sit-toolkit
```

## The problem

When you version a prompt or schema with plain Git, you get `+13 -2` lines. You don't know if it's a typo fix or a breaking behavior change. `sit` does.

```
$ sit diff v0.3.0..v0.4.0

Skill Diff
Baseline: paper-webpage-builder@0.3.0
Current: paper-webpage-builder@0.4.0
Risk: review-required
Suggested version bump: minor

[prompt]
  - PROMPT changed SKILL.md (+13 -2; headings: Core Rule, Workflow)

[script]
  - SCRIPT changed scripts/scan_paper.py (review required)

[reference]
  - REFERENCE changed references/design_principles.md (+27 -3)
```

## Quick start

```bash
# New package
sit init my-skill && cd my-skill

# Existing project
sit standardize .

# Validate, test, review
sit validate . && sit test .
sit diff HEAD~1..HEAD
sit pr-summary HEAD~1..HEAD

# Release
sit release minor . --bundle
```

## Commands

**Lifecycle:** `sit init`, `sit standardize`, `sit onboard`, `sit doctor`

**Quality:** `sit validate`, `sit test`, `sit test --run`, `sit deps check`

**Diff & Review:** `sit diff`, `sit pr-summary`, `sit report`, `sit ci-summary`

**Release:** `sit commit`, `sit release`

**Git passthrough:** `sit add`, `sit push`, `sit pull`, `sit branch`, `sit checkout`, `sit log`

## Agent integration

`sit` exposes its capabilities for AI agents via three interfaces:

| Interface | Usage |
|---|---|
| **Python SDK** | `from sit.sdk import Sit` — direct API calls |
| **MCP Server** | `pip install 'sit-toolkit[mcp]'` — 7 tools over stdio |
| **LLM Tool-Use** | `from sit.tool_use import get_tools_openai` — OpenAI & Anthropic schemas |

<details>
<summary>Python SDK example</summary>

```python
from sit.sdk import Sit

s = Sit("./my-skill-package")
s.info()            # package metadata
s.validate()        # structure checks
s.test()            # golden tests
s.diff("./old")     # semantic diff
s.pr_summary("./old")  # PR summary
s.report(compare="./old")  # full report
```
</details>

<details>
<summary>MCP Server config</summary>

```bash
pip install 'sit-toolkit[mcp]'
sit-mcp-server
```

```json
{
  "mcpServers": {
    "sit": { "command": "sit-mcp-server" }
  }
}
```
</details>

<details>
<summary>LLM Tool-Use schema</summary>

```python
from sit.tool_use import get_tools_openai, get_tools_anthropic

tools = get_tools_openai()      # OpenAI format
tools = get_tools_anthropic()   # Anthropic format
```
</details>

## CI integration

`sit init` generates a GitHub Actions workflow that validates, tests, and posts a semantic summary to your PR:

```yaml
- run: sit validate "$SIT_PACKAGE_DIR"
- run: sit test "$SIT_PACKAGE_DIR"
- run: sit test "$SIT_PACKAGE_DIR" --run
- run: sit ci-summary "$SIT_PACKAGE_DIR" --compare origin/main..HEAD >> "$GITHUB_STEP_SUMMARY"
```

## License

Apache-2.0. See [LICENSE](LICENSE).
