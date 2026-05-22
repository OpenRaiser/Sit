"""LLM tool-use / function-calling JSON Schemas for sit.

Provides ready-made tool definitions compatible with:
- OpenAI function calling (``tools[].function``)
- Anthropic Claude tool use (``tools[].input_schema``)
- Any system that accepts JSON Schema for tool parameters

Usage::

    from sit.tool_use import get_tools_openai, get_tools_anthropic, get_tool

    # OpenAI format
    tools = get_tools_openai()
    response = client.chat_completion(messages=..., tools=tools)

    # Anthropic format
    tools = get_tools_anthropic()
    response = client.messages.create(messages=..., tools=tools)

    # Single tool by name
    info_tool = get_tool("sit_info")
"""

from __future__ import annotations

from typing import Any

# ---------------------------------------------------------------------------
# Canonical tool definitions (provider-agnostic)
# ---------------------------------------------------------------------------

TOOLS: list[dict[str, Any]] = [
    {
        "name": "sit_info",
        "description": (
            "Get package info for a sit skill package. "
            "Returns the sit.info.v1 contract: name, version, git state, "
            "file listing, validation status, golden test results, reports."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "package_path": {
                    "type": "string",
                    "description": "Path to the skill package directory or skill.yaml file.",
                },
            },
            "required": ["package_path"],
            "additionalProperties": False,
        },
    },
    {
        "name": "sit_validate",
        "description": (
            "Validate a sit skill package structure. "
            "Checks skill.yaml fields, prompt/schema/test paths, schema validity, "
            "JSONL format. Returns pass/fail with messages."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "package_path": {
                    "type": "string",
                    "description": "Path to the skill package directory or skill.yaml file.",
                },
            },
            "required": ["package_path"],
            "additionalProperties": False,
        },
    },
    {
        "name": "sit_test",
        "description": (
            "Run validation + golden schema tests on a sit skill package. "
            "Returns the sit.test.v1 contract with validation and test results."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "package_path": {
                    "type": "string",
                    "description": "Path to the skill package directory or skill.yaml file.",
                },
                "run_actual": {
                    "type": "boolean",
                    "description": "If true, run the actual test runner (commands.run_case) instead of static validation only. Default: false.",
                },
                "runner": {
                    "type": "string",
                    "description": "Override the test runner command (default: from skill.yaml commands.run_case).",
                },
                "timeout": {
                    "type": "integer",
                    "description": "Runner timeout in seconds. Default: 30.",
                },
            },
            "required": ["package_path"],
            "additionalProperties": False,
        },
    },
    {
        "name": "sit_diff",
        "description": (
            "Semantic diff between two sit skill packages. "
            "Returns the sit.diff.v1 contract with change events, risk assessment, "
            "and suggested version bump."
        ),
        "parameters": {
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
                    "description": "Include full unified diff lines in text_diffs. Default: false.",
                },
            },
            "required": ["old_path", "new_path"],
            "additionalProperties": False,
        },
    },
    {
        "name": "sit_pr_summary",
        "description": (
            "Generate a PR summary for a skill package change. "
            "Returns the sit.pr_summary.v1 contract with baseline/current refs, "
            "validation, tests, risk, and semantic diff."
        ),
        "parameters": {
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
            "additionalProperties": False,
        },
    },
    {
        "name": "sit_report",
        "description": (
            "Build a full sit report for a skill package. "
            "Returns the sit.report.v1 contract with validation, golden tests, "
            "optional diff, and reproducibility commands."
        ),
        "parameters": {
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
            "additionalProperties": False,
        },
    },
    {
        "name": "sit_doctor",
        "description": (
            "Run environment diagnostics for a sit skill package. "
            "Checks git, GitHub remote, manifest, validation, and golden tests."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "package_path": {
                    "type": "string",
                    "description": "Path to the skill package directory or skill.yaml file.",
                },
            },
            "required": ["package_path"],
            "additionalProperties": False,
        },
    },
]

_TOOL_MAP: dict[str, dict[str, Any]] = {tool["name"]: tool for tool in TOOLS}


# ---------------------------------------------------------------------------
# Provider-specific formatters
# ---------------------------------------------------------------------------

def get_tools_openai() -> list[dict[str, Any]]:
    """Return tool definitions in OpenAI function-calling format.

    Each item has ``type: "function"`` and ``function: {name, description, parameters}``.
    """
    return [
        {
            "type": "function",
            "function": {
                "name": tool["name"],
                "description": tool["description"],
                "parameters": tool["parameters"],
            },
        }
        for tool in TOOLS
    ]


def get_tools_anthropic() -> list[dict[str, Any]]:
    """Return tool definitions in Anthropic Claude tool-use format.

    Each item has ``name``, ``description``, and ``input_schema``.
    """
    return [
        {
            "name": tool["name"],
            "description": tool["description"],
            "input_schema": tool["parameters"],
        }
        for tool in TOOLS
    ]


def get_tool(name: str) -> dict[str, Any] | None:
    """Look up a single tool definition by name (provider-agnostic)."""
    return _TOOL_MAP.get(name)


def list_tool_names() -> list[str]:
    """Return all available tool names."""
    return [tool["name"] for tool in TOOLS]
