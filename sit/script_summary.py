from __future__ import annotations

import ast
import re
from pathlib import Path
from typing import Any


def summarize_script_change(action: str, old_path: Path | None, new_path: Path | None) -> dict[str, Any]:
    old_summary = summarize_script(old_path) if old_path is not None and old_path.exists() else None
    new_summary = summarize_script(new_path) if new_path is not None and new_path.exists() else None
    current = new_summary or old_summary or {}
    details: dict[str, Any] = {
        "kind": "script_summary",
        "action": action,
        "language": current.get("language", "unknown"),
        "summary": _summary_sentence(action, current),
    }
    for key in ("doc", "cli_args", "functions", "classes", "imports", "external_commands", "usage", "delegates"):
        values = current.get(key)
        if values:
            details[key] = values
    changes = _compare_summaries(old_summary, new_summary)
    if changes:
        details["changes"] = changes
    return details


def summarize_script(path: Path) -> dict[str, Any]:
    suffix = path.suffix.lower()
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        text = path.read_text(encoding="latin-1", errors="replace")

    if suffix == ".py":
        return _summarize_python(text)
    if suffix in {".sh", ".bash"} or text.startswith("#!/usr/bin/env bash") or text.startswith("#!/bin/bash"):
        return _summarize_shell(text)
    return {
        "language": suffix.lstrip(".") or "text",
        "doc": _first_comment_block(text),
    }


def render_script_details(details: dict[str, Any], *, indent: str = "  ") -> list[str]:
    if details.get("kind") != "script_summary":
        return []
    lines: list[str] = []
    summary = details.get("summary")
    if summary:
        lines.append(f"{indent}summary: {summary}")
    for key, label in (
        ("changes", "changes"),
        ("cli_args", "cli args"),
        ("functions", "functions"),
        ("classes", "classes"),
        ("imports", "imports"),
        ("external_commands", "external commands"),
        ("usage", "usage"),
        ("delegates", "delegates"),
    ):
        values = details.get(key)
        if values:
            lines.append(f"{indent}{label}: {', '.join(str(value) for value in values[:8])}")
    return lines


def _summarize_python(text: str) -> dict[str, Any]:
    data: dict[str, Any] = {
        "language": "python",
        "imports": [],
        "functions": [],
        "classes": [],
        "cli_args": [],
        "external_commands": [],
    }
    try:
        tree = ast.parse(text)
    except SyntaxError:
        data["doc"] = _first_comment_block(text)
        return _compact(data)

    doc = ast.get_docstring(tree)
    if doc:
        data["doc"] = _clean_doc(doc)

    imports: list[str] = []
    functions: list[str] = []
    classes: list[str] = []
    cli_args: list[str] = []
    external_commands: list[str] = []

    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            functions.append(node.name)
        elif isinstance(node, ast.ClassDef):
            classes.append(node.name)

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.extend(alias.name.split(".", 1)[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.append(node.module.split(".", 1)[0])
        if _is_attr_call(node, "add_argument"):
            cli_args.extend(_literal_string_args(node))
        elif _is_subprocess_call(node):
            command = _subprocess_command(node)
            if command:
                external_commands.append(command)
        elif _is_shutil_which_call(node):
            for arg in _literal_string_args(node):
                external_commands.append(arg)

    data["imports"] = _dedupe(imports)[:12]
    data["functions"] = _dedupe(functions)[:12]
    data["classes"] = _dedupe(classes)[:8]
    data["cli_args"] = _dedupe(cli_args)[:16]
    data["external_commands"] = _dedupe(external_commands)[:12]
    return _compact(data)


def _summarize_shell(text: str) -> dict[str, Any]:
    usage: list[str] = []
    delegates: list[str] = []
    external_commands: list[str] = []

    for line in text.splitlines():
        stripped = line.strip()
        usage_match = re.search(r"Usage:\s*([^\"']+)", stripped)
        if usage_match:
            usage.append(usage_match.group(1).strip())
        if re.search(r"\bexec\s+(?:python3|python)\b", stripped):
            delegate_match = re.search(r"([A-Za-z0-9_.-]+\.py)", stripped)
            if delegate_match:
                delegates.append(delegate_match.group(1))
        command_match = re.search(r"\bcommand\s+-v\s+([A-Za-z0-9_.-]+)", stripped)
        if command_match:
            external_commands.append(command_match.group(1))
        for tool in ("gs", "pdfinfo", "pdftotext"):
            if re.search(rf"(^|[ (]){re.escape(tool)}([ )]|$)", stripped):
                external_commands.append(tool)

    return _compact(
        {
            "language": "shell",
            "doc": _first_comment_block(text),
            "usage": _dedupe(usage)[:6],
            "delegates": _dedupe(delegates)[:6],
            "external_commands": _dedupe(external_commands)[:10],
        }
    )


def _is_attr_call(node: ast.AST, attr: str) -> bool:
    return isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == attr


def _is_subprocess_call(node: ast.AST) -> bool:
    return (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and isinstance(node.func.value, ast.Name)
        and node.func.value.id == "subprocess"
        and node.func.attr in {"run", "Popen", "check_call", "check_output"}
    )


def _is_shutil_which_call(node: ast.AST) -> bool:
    return (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and isinstance(node.func.value, ast.Name)
        and node.func.value.id == "shutil"
        and node.func.attr == "which"
    )


def _literal_string_args(node: ast.Call) -> list[str]:
    values: list[str] = []
    for arg in node.args:
        if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
            values.append(arg.value)
    return values


def _subprocess_command(node: ast.Call) -> str | None:
    if not node.args:
        return None
    first = node.args[0]
    if isinstance(first, ast.List) and first.elts:
        head = first.elts[0]
        if isinstance(head, ast.Constant) and isinstance(head.value, str):
            return head.value
    if isinstance(first, ast.Constant) and isinstance(first.value, str):
        return first.value.split()[0] if first.value.split() else None
    return None


def _compare_summaries(old: dict[str, Any] | None, new: dict[str, Any] | None) -> list[str]:
    if not old or not new:
        return []
    changes: list[str] = []
    for key, label in (
        ("cli_args", "CLI args"),
        ("functions", "functions"),
        ("classes", "classes"),
        ("imports", "imports"),
        ("external_commands", "external commands"),
        ("usage", "usage"),
        ("delegates", "delegates"),
    ):
        old_values = set(old.get(key, []))
        new_values = set(new.get(key, []))
        added = sorted(new_values - old_values)
        removed = sorted(old_values - new_values)
        if added:
            changes.append(f"added {label}: {', '.join(added[:6])}")
        if removed:
            changes.append(f"removed {label}: {', '.join(removed[:6])}")
    if old.get("doc") and new.get("doc") and old.get("doc") != new.get("doc"):
        changes.append("updated module description")
    return changes[:10]


def _summary_sentence(action: str, summary: dict[str, Any]) -> str:
    doc = summary.get("doc")
    if doc:
        return f"{action} {summary.get('language', 'script')} script: {doc}"
    functions = summary.get("functions") or []
    if functions:
        return f"{action} {summary.get('language', 'script')} script with functions: {', '.join(functions[:5])}"
    usage = summary.get("usage") or []
    if usage:
        return f"{action} shell script: {usage[0]}"
    return f"{action} {summary.get('language', 'script')} script"


def _clean_doc(doc: str) -> str:
    text = re.sub(r"\s+", " ", doc).strip()
    for separator in (". ", "\n"):
        if separator in text:
            text = text.split(separator, 1)[0].strip()
            break
    return text[:220]


def _first_comment_block(text: str) -> str:
    lines: list[str] = []
    for line in text.splitlines()[:20]:
        stripped = line.strip()
        if stripped.startswith("#!"):
            continue
        if stripped.startswith("#"):
            lines.append(stripped.lstrip("#").strip())
            continue
        if lines:
            break
    return _clean_doc(" ".join(lines)) if lines else ""


def _compact(data: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in data.items() if value not in (None, "", [], {})}


def _dedupe(values) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if not value or value == "__future__" or value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result
