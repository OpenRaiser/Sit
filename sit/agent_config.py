"""Agent auto-discovery configuration generator.

Generates MCP server config and agent rules so that LLM agents
(Claude Code, Cursor, etc.) can automatically discover and use sit
within a skill package.

Usage::

    from sit.agent_config import setup_agent_config, AgentSetupResult
    result = setup_agent_config(Path("./my-skill"))
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class AgentSetupResult:
    root: Path
    created: list[str] = field(default_factory=list)
    updated: list[str] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": "sit.agent_setup.v1",
            "root": str(self.root),
            "created": self.created,
            "updated": self.updated,
            "skipped": self.skipped,
        }


def setup_agent_config(
    package_root: Path,
    *,
    force: bool = False,
) -> AgentSetupResult:
    """Generate agent auto-discovery files in *package_root*.

    Creates:
    - ``.mcp.json`` — MCP server config (Claude Code / Cursor format)
    - ``AGENTS.md`` — agent rules for this skill package
    """
    result = AgentSetupResult(root=package_root)
    _write_mcp_json(package_root / ".mcp.json", result, force=force)
    _write_agents_md(package_root / "AGENTS.md", package_root, result, force=force)
    return result


def render_agent_setup_text(result: AgentSetupResult) -> str:
    lines = [
        "SitHub Agent Setup",
        "",
        f"Root: {result.root}",
        f"Created: {len(result.created)}",
        f"Updated: {len(result.updated)}",
        f"Skipped: {len(result.skipped)}",
    ]
    if result.created:
        lines.extend(["", "Created:"])
        lines.extend(f"  + {p}" for p in result.created)
    if result.updated:
        lines.extend(["", "Updated:"])
        lines.extend(f"  ~ {p}" for p in result.updated)
    if result.skipped:
        lines.extend(["", "Skipped (already exists):"])
        lines.extend(f"  - {p}" for p in result.skipped)
    if result.created or result.updated:
        lines.extend([
            "",
            "Agent auto-discovery is now configured.",
            "Your agent (Claude Code, Cursor, etc.) will detect sit automatically.",
            "",
            "Next steps:",
            "  1. Restart your agent editor to pick up the new MCP config.",
            "  2. Ask your agent: 'What skills are available?' or 'Run sit validate'.",
        ])
    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# File generators
# ---------------------------------------------------------------------------

def _write_mcp_json(path: Path, result: AgentSetupResult, *, force: bool) -> None:
    import json
    relative = path.relative_to(result.root).as_posix()
    existed = path.exists()
    if existed and not force:
        result.skipped.append(relative)
        return

    config = {
        "mcpServers": {
            "sit": {
                "command": "sit-mcp-server",
            }
        }
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")
    (result.updated if existed else result.created).append(relative)


def _write_agents_md(path: Path, package_root: Path, result: AgentSetupResult, *, force: bool) -> None:
    relative = path.relative_to(result.root).as_posix()
    existed = path.exists()
    if existed and not force:
        result.skipped.append(relative)
        return

    content = _agents_md_template(package_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    (result.updated if existed else result.created).append(relative)


def _agents_md_template(package_root: Path) -> str:
    pkg_name = package_root.name
    return f"""# {pkg_name} — Agent Instructions

This is a **sit-managed Skill Package**. The `sit` CLI provides semantic
versioning, validation, testing, and diff for prompts, schemas, and golden tests.

## When working in this package, always:

1. **Before committing**: run `sit validate` and `sit test` to check package integrity.
2. **After changes**: run `sit diff` to see what changed semantically.
3. **For PRs**: run `sit pr-summary` to generate a structured change summary.
4. **Read JSON output**: use `--format json` for machine-readable output.
   Schema definitions are at `docs/schemas/` in the sit repository.

## Key commands

| Command | Purpose |
|---------|---------|
| `sit info` | Package metadata + git state |
| `sit validate` | Check manifest, paths, schemas |
| `sit test` | Run golden expected-vs-schema tests |
| `sit diff` | Semantic diff of skill package |
| `sit pr-summary` | Generate PR summary (Markdown or JSON) |
| `sit report` | Full validation report |
| `sit release` | Bump version and create release |

## JSON output contracts

- `sit info --format json` → `sit.info.v1`
- `sit pr-summary --format json` → `sit.pr_summary.v1`
- `sit test --format json` → `sit.test.v1`
- `sit report --format json` → `sit.report.v1`

## MCP integration

If your editor supports MCP (Model Context Protocol), the `.mcp.json` file
in this directory configures the `sit` MCP server automatically. You can call
sit tools directly via MCP without shell commands.

## Package structure

```
{pkg_name}/
  skill.yaml              # manifest: name, version, paths
  prompts/                # prompt files
  schemas/                # input & output JSON schemas
  tests/golden.jsonl      # deterministic test cases
  reports/                # generated reports
  .mcp.json               # MCP server config (auto-generated)
  AGENTS.md               # this file (auto-generated)
```
"""
