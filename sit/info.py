from __future__ import annotations

from pathlib import Path
import re
from typing import Any

from .errors import SitError
from .git import git_output, git_root
from .package import SkillPackage
from .validate import CheckResult, run_golden_schema_tests, validate_package


def build_info_payload(package: SkillPackage) -> dict[str, Any]:
    validation = validate_package(package)
    tests = _run_tests_for_info(package, validation)

    return {
        "schema_version": "sit.info.v1",
        "package": {
            "name": package.name or "<unknown>",
            "version": package.version or "<unknown>",
            "description": package.description,
            "root": str(package.root),
            "manifest": str(package.manifest_path),
        },
        "git": _git_info(package.root),
        "files": {
            "prompts": _path_entries(package.prompt_paths()),
            "schemas": _path_entries(package.schema_paths()),
            "tests": _path_entries(package.test_paths()),
        },
        "validation": {
            "status": "pass" if validation.ok else "fail",
            "ok": validation.ok,
            "messages": validation.messages,
        },
        "golden_tests": _test_info(tests),
        "reports": _report_info(package.report_dir()),
    }


def render_info_text(data: dict[str, Any]) -> str:
    package = data["package"]
    git = data["git"]
    validation = data["validation"]
    tests = data["golden_tests"]
    reports = data["reports"]

    lines = [
        "Skill Package Info",
        "",
        f"Package: {package['name']}",
        f"Version: {package['version']}",
    ]
    if package.get("description"):
        lines.append(f"Description: {package['description']}")
    lines.extend(
        [
            f"Root: {package['root']}",
            f"Manifest: {package['manifest']}",
            "",
            "Git:",
        ]
    )

    if git["available"]:
        dirty = "yes" if git["dirty"] else "no"
        lines.extend(
            [
                f"  Repo: {git['root']}",
                f"  Branch: {git['branch']}",
                f"  Commit: {git['commit']}",
                f"  Dirty: {dirty}",
            ]
        )
        if git["changed_files_count"]:
            lines.append(f"  Changed files: {git['changed_files_count']}")
    else:
        lines.append("  unavailable: not inside a Git work tree")

    lines.extend(
        [
            "",
            "Files:",
        ]
    )
    for title, key in (("Prompts", "prompts"), ("Schemas", "schemas"), ("Tests", "tests")):
        lines.append(f"  {title}:")
        entries = data["files"][key]
        if not entries:
            lines.append("    <none>")
            continue
        for name, entry in entries.items():
            marker = "exists" if entry["exists"] else "missing"
            lines.append(f"    {name}: {marker} {entry['path']}")

    lines.extend(
        [
            "",
            f"Validation: {validation['status']}",
            f"Golden tests: {tests['status']}",
        ]
    )
    if tests.get("summary"):
        lines.append(f"Golden summary: {tests['summary']}")

    lines.extend(["", "Reports:"])
    if reports["exists"]:
        lines.append(f"  Directory: {reports['path']}")
        if reports["latest"]:
            latest = reports["latest"]
            lines.append(f"  Latest: {latest['name']} ({latest['modified']})")
        else:
            lines.append("  Latest: <none>")
    else:
        lines.append(f"  missing {reports['path']}")

    return "\n".join(lines) + "\n"


def _path_entries(paths: dict[str, Path]) -> dict[str, dict[str, Any]]:
    return {
        name: {
            "path": str(path),
            "exists": path.exists(),
        }
        for name, path in paths.items()
    }


def _git_info(path: Path) -> dict[str, Any]:
    root = git_root(path)
    if root is None:
        return {
            "available": False,
            "root": None,
            "branch": None,
            "commit": None,
            "dirty": None,
            "changed_files_count": 0,
        }

    branch = _safe_git(["branch", "--show-current"], cwd=path) or _safe_git(["rev-parse", "--abbrev-ref", "HEAD"], cwd=path)
    commit = _safe_git(["rev-parse", "--short", "HEAD"], cwd=path)
    porcelain = _safe_git(["status", "--porcelain"], cwd=path) or ""
    changed_files = [line for line in porcelain.splitlines() if line.strip()]

    return {
        "available": True,
        "root": str(root),
        "branch": branch or "<detached>",
        "commit": commit or "<unborn>",
        "dirty": bool(changed_files),
        "changed_files_count": len(changed_files),
    }


def _safe_git(args: list[str], *, cwd: Path) -> str | None:
    try:
        return git_output(args, cwd=cwd)
    except SitError:
        return None


def _run_tests_for_info(package: SkillPackage, validation: CheckResult) -> CheckResult | None:
    if not validation.ok:
        return None
    try:
        return run_golden_schema_tests(package)
    except SitError as exc:
        return CheckResult(ok=False, messages=[f"ERR {exc}"])


def _test_info(result: CheckResult | None) -> dict[str, Any]:
    if result is None:
        return {
            "status": "skipped",
            "ok": None,
            "passed": None,
            "total": None,
            "summary": None,
            "messages": [],
        }

    passed, total, summary = _parse_test_summary(result.messages)
    return {
        "status": "pass" if result.ok else "fail",
        "ok": result.ok,
        "passed": passed,
        "total": total,
        "summary": summary,
        "messages": result.messages,
    }


def _parse_test_summary(messages: list[str]) -> tuple[int | None, int | None, str | None]:
    for message in reversed(messages):
        match = re.match(r"SUMMARY (\d+)/(\d+) golden (?:cases passed|expected records validated)", message)
        if match:
            return int(match.group(1)), int(match.group(2)), message
    return None, None, None


def _report_info(report_dir: Path) -> dict[str, Any]:
    if not report_dir.exists():
        return {
            "path": str(report_dir),
            "exists": False,
            "latest": None,
        }

    files = sorted((path for path in report_dir.iterdir() if path.is_file()), key=lambda path: path.stat().st_mtime, reverse=True)
    latest = files[0] if files else None
    return {
        "path": str(report_dir),
        "exists": True,
        "latest": _report_entry(latest) if latest else None,
    }


def _report_entry(path: Path) -> dict[str, Any]:
    stat = path.stat()
    return {
        "name": path.name,
        "path": str(path),
        "modified": _format_mtime(stat.st_mtime),
        "size_bytes": stat.st_size,
    }


def _format_mtime(timestamp: float) -> str:
    from datetime import datetime

    return datetime.fromtimestamp(timestamp).isoformat(timespec="seconds")
