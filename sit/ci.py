from __future__ import annotations

from typing import Any

from .script_summary import render_script_details


def render_ci_summary(data: dict[str, Any]) -> str:
    package = data["package"]
    validation = data["validation"]
    tests = data["golden_tests"]
    diff = data.get("diff")

    lines = [
        "## SitHub CI Summary",
        "",
        f"- Package: `{package['name']}@{package['version']}`",
        f"- Validation: **{validation['status']}**",
        f"- Golden tests: **{tests['status']}**",
    ]
    if tests.get("summary"):
        lines.append(f"- Golden summary: `{tests['summary']}`")

    if diff is not None:
        lines.extend(
            [
                f"- Diff risk: **{diff['risk']}**",
                f"- Suggested version bump: `{diff['suggested_bump']}`",
            ]
        )

    lines.extend(["", "### Validation", ""])
    lines.extend(_message_lines(validation["messages"]))

    lines.extend(["", "### Golden Tests", ""])
    if tests["status"] == "skipped":
        lines.append("- Skipped because validation failed.")
    else:
        lines.extend(_message_lines(tests["messages"]))

    if diff is not None:
        lines.extend(["", "### Semantic Diff", ""])
        for event in diff["events"]:
            lines.append(f"- `{event['message']}`")
            for detail in _event_detail_lines(event):
                lines.append(f"  - `{detail}`")

    repro = data.get("reproducibility", {})
    commands = [value for value in (repro.get("validate"), repro.get("test"), repro.get("diff")) if value]
    if commands:
        lines.extend(["", "### Reproduce", "", "```bash"])
        lines.extend(commands)
        lines.append("```")

    return "\n".join(lines) + "\n"


def _message_lines(messages: list[str]) -> list[str]:
    if not messages:
        return ["- <none>"]
    return [f"- `{message}`" for message in messages]


def _event_detail_lines(event: dict[str, Any]) -> list[str]:
    details = event.get("details")
    if not isinstance(details, dict):
        return []
    return render_script_details(details, indent="")
