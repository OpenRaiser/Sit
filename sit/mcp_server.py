"""MCP (Model Context Protocol) server for sit.

Exposes sit commands as MCP tools so LLM agents can call them natively
via the MCP protocol.  Uses the Python SDK under the hood — no subprocess.

Usage::

    # Run as stdio MCP server (default transport):
    python -m sit.mcp_server

    # Or import and customise:
    from sit.mcp_server import create_server
    server = create_server()
    server.run()
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

try:
    from mcp.server import Server
    from mcp.server.stdio import stdio_server
    from mcp.types import TextContent, Tool
except ImportError:
    raise ImportError(
        "MCP support requires the 'mcp' package. "
        "Install it with: pip install 'sit-toolkit[mcp]' or pip install mcp"
    )

from .sdk import Sit

# ---------------------------------------------------------------------------
# Tool definitions
# ---------------------------------------------------------------------------

TOOLS: list[Tool] = [
    Tool(
        name="sit_info",
        description=(
            "Get package info for a sit skill package. "
            "Returns the sit.info.v1 contract: name, version, git state, "
            "file listing, validation status, golden test results, reports."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "package_path": {
                    "type": "string",
                    "description": "Path to the skill package directory or skill.yaml file.",
                },
            },
            "required": ["package_path"],
        },
    ),
    Tool(
        name="sit_validate",
        description=(
            "Validate a sit skill package structure. "
            "Checks skill.yaml fields, prompt/schema/test paths, schema validity, "
            "JSONL format. Returns pass/fail with messages."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "package_path": {
                    "type": "string",
                    "description": "Path to the skill package directory or skill.yaml file.",
                },
            },
            "required": ["package_path"],
        },
    ),
    Tool(
        name="sit_test",
        description=(
            "Run validation + golden schema tests on a sit skill package. "
            "Returns the sit.test.v1 contract with validation and test results."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "package_path": {
                    "type": "string",
                    "description": "Path to the skill package directory or skill.yaml file.",
                },
                "run_actual": {
                    "type": "boolean",
                    "description": "If true, run the actual test runner (commands.run_case) instead of static validation only.",
                    "default": False,
                },
                "runner": {
                    "type": "string",
                    "description": "Override the test runner command (default: from skill.yaml commands.run_case).",
                },
                "timeout": {
                    "type": "integer",
                    "description": "Runner timeout in seconds (default: 30).",
                    "default": 30,
                },
            },
            "required": ["package_path"],
        },
    ),
    Tool(
        name="sit_diff",
        description=(
            "Semantic diff between two sit skill packages. "
            "Returns the sit.diff.v1 contract with change events, risk assessment, "
            "and suggested version bump."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "old_path": {
                    "type": "string",
                    "description": "Path to the baseline/old skill package.",
                },
                "new_path": {
                    "type": "string",
                    "description": "Path to the current/new skill package.",
                },
                "include_text_diffs": {
                    "type": "boolean",
                    "description": "Include full unified diff lines in text_diffs (default: false).",
                    "default": False,
                },
            },
            "required": ["old_path", "new_path"],
        },
    ),
    Tool(
        name="sit_pr_summary",
        description=(
            "Generate a PR summary for a skill package change. "
            "Returns the sit.pr_summary.v1 contract with baseline/current refs, "
            "validation, tests, risk, and semantic diff."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "baseline_path": {
                    "type": "string",
                    "description": "Path to the baseline skill package.",
                },
                "current_path": {
                    "type": "string",
                    "description": "Path to the current skill package.",
                },
            },
            "required": ["baseline_path", "current_path"],
        },
    ),
    Tool(
        name="sit_report",
        description=(
            "Build a full sit report for a skill package. "
            "Returns the sit.report.v1 contract with validation, golden tests, "
            "optional diff, and reproducibility commands."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "package_path": {
                    "type": "string",
                    "description": "Path to the skill package directory or skill.yaml file.",
                },
                "compare_path": {
                    "type": "string",
                    "description": "Optional path to a baseline package for diff comparison.",
                },
            },
            "required": ["package_path"],
        },
    ),
    Tool(
        name="sit_doctor",
        description=(
            "Run environment diagnostics for a sit skill package. "
            "Checks git, GitHub remote, manifest, validation, and golden tests."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "package_path": {
                    "type": "string",
                    "description": "Path to the skill package directory or skill.yaml file.",
                },
            },
            "required": ["package_path"],
        },
    ),
]


# ---------------------------------------------------------------------------
# Handler
# ---------------------------------------------------------------------------

def _handle_tool(name: str, arguments: dict[str, Any]) -> str:
    """Dispatch an MCP tool call to the SDK and return JSON string."""
    try:
        if name == "sit_info":
            result = Sit(arguments["package_path"]).info()
        elif name == "sit_validate":
            result = Sit(arguments["package_path"]).validate()
        elif name == "sit_test":
            result = Sit(arguments["package_path"]).test(
                run_actual=arguments.get("run_actual", False),
                runner=arguments.get("runner"),
                timeout=arguments.get("timeout", 30),
            )
        elif name == "sit_diff":
            result = Sit(arguments["new_path"]).diff(
                arguments["old_path"],
                include_text_diffs=arguments.get("include_text_diffs", False),
            )
        elif name == "sit_pr_summary":
            result = Sit(arguments["current_path"]).pr_summary(arguments["baseline_path"])
        elif name == "sit_report":
            result = Sit(arguments["package_path"]).report(
                compare=arguments.get("compare_path"),
            )
        elif name == "sit_doctor":
            result = Sit(arguments["package_path"]).doctor()
        else:
            return json.dumps({"error": f"Unknown tool: {name}"})
        return json.dumps(result, ensure_ascii=False, indent=2)
    except Exception as exc:
        return json.dumps({"error": f"{type(exc).__name__}: {exc}"})


# ---------------------------------------------------------------------------
# Server factory
# ---------------------------------------------------------------------------

def create_server() -> Server:
    """Create and configure an MCP Server instance with sit tools."""
    server = Server("sit-mcp-server")

    @server.list_tools()
    async def list_tools() -> list[Tool]:
        return TOOLS

    @server.call_tool()
    async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
        result = _handle_tool(name, arguments)
        return [TextContent(type="text", text=result)]

    return server


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

async def _run_stdio() -> None:
    server = create_server()
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


def main() -> None:
    """Run the sit MCP server over stdio transport."""
    import asyncio

    asyncio.run(_run_stdio())


if __name__ == "__main__":
    main()
