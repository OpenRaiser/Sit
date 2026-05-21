from __future__ import annotations

from dataclasses import dataclass, field
import json
import re
from pathlib import Path
import subprocess
from typing import Any

import yaml

from .doctor import build_doctor_payload
from .errors import SitError
from .git import git_output, is_git_repo
from .init import _github_workflow, _pull_request_template
from .package import load_package
from .report import build_report, render_report_html, build_report_payload


@dataclass
class OnboardResult:
    root: Path
    created: list[str] = field(default_factory=list)
    updated: list[str] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    doctor: dict[str, Any] | None = None
    operation: str = "onboard"

    @property
    def ok(self) -> bool:
        if self.operation == "standardize":
            if self.doctor is None:
                return False
            failed = [
                check
                for check in self.doctor.get("checks", [])
                if check.get("status") == "fail" and check.get("name") not in {"git", "github_remote"}
            ]
            return not failed
        return self.doctor is not None and bool(self.doctor.get("ok"))

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": f"sit.{self.operation}.v1",
            "root": str(self.root),
            "created": self.created,
            "updated": self.updated,
            "skipped": self.skipped,
            "warnings": self.warnings,
            "doctor": self.doctor,
        }


def onboard_existing_skill(
    path: str | Path = ".",
    *,
    name: str | None = None,
    version: str = "0.1.0",
    remote: str | None = None,
    no_git: bool = False,
    force: bool = False,
) -> OnboardResult:
    root = Path(path).expanduser().resolve()
    if root.exists() and not root.is_dir():
        raise SitError(f"Expected a Skill directory, got file: {root}")
    root.mkdir(parents=True, exist_ok=True)

    skill_md = root / "SKILL.md"
    if not skill_md.exists():
        raise SitError(f"Missing SKILL.md: {skill_md}")

    result = OnboardResult(root=root)
    package_name = name or _infer_name(root)
    description = _infer_description(skill_md, package_name)

    _ensure_dir(root / "schemas", result)
    _ensure_dir(root / "tests", result)
    _ensure_dir(root / "reports", result)
    _ensure_dir(root / ".github" / "workflows", result)

    _write_manifest(root / "skill.yaml", root, package_name, version, description, result, force=force)
    _write_json(root / "schemas" / "input.schema.json", _input_schema(), result, force=force)
    _write_json(root / "schemas" / "output.schema.json", _output_schema(), result, force=force)
    _write_file(root / "tests" / "golden.jsonl", json.dumps(_golden_case(package_name), ensure_ascii=False) + "\n", result, force=force)
    _write_file(root / ".github" / "workflows" / "sit-ci.yaml", _github_workflow(), result, force=force)
    _write_file(root / ".github" / "pull_request_template.md", _pull_request_template(), result, force=force)

    if not no_git:
        _ensure_git(root, remote, result)

    package = load_package(root)
    payload = build_report_payload(package)
    _write_file(root / "reports" / "sithub-onboarding.md", build_report(package), result, force=force)
    _write_file(root / "reports" / "sithub-onboarding.html", render_report_html(payload), result, force=force)

    result.doctor = build_doctor_payload(root)
    return result


def standardize_skill_package(
    path: str | Path = ".",
    *,
    name: str | None = None,
    version: str = "0.1.0",
    remote: str | None = None,
    no_git: bool = False,
    force: bool = False,
) -> OnboardResult:
    root = Path(path).expanduser().resolve()
    if root.exists() and not root.is_dir():
        raise SitError(f"Expected a Skill directory, got file: {root}")
    root.mkdir(parents=True, exist_ok=True)

    result = OnboardResult(root=root, operation="standardize")
    package_name = name or _infer_name(root)
    prompt_sources = _discover_prompt_sources(root)
    description = _infer_standardize_description(prompt_sources, package_name)

    _ensure_dir(root / "prompts", result)
    _ensure_dir(root / "schemas", result)
    _ensure_dir(root / "tests", result)
    _ensure_dir(root / "reports", result)
    _ensure_dir(root / ".github" / "workflows", result)

    prompt_paths = _standardize_prompts(root, package_name, prompt_sources, result, force=force)
    _write_manifest(root / "skill.yaml", root, package_name, version, description, result, force=force, prompts=prompt_paths)
    _write_json(root / "schemas" / "input.schema.json", _input_schema(), result, force=force)
    _write_json(root / "schemas" / "output.schema.json", _output_schema(), result, force=force)
    _write_file(root / "tests" / "golden.jsonl", json.dumps(_golden_case(package_name), ensure_ascii=False) + "\n", result, force=force)
    _write_file(root / ".github" / "workflows" / "sit-ci.yaml", _github_workflow(), result, force=force)
    _write_file(root / ".github" / "pull_request_template.md", _pull_request_template(), result, force=force)

    if not no_git:
        _ensure_git(root, remote, result)

    package = load_package(root)
    payload = build_report_payload(package)
    _write_file(root / "reports" / "sithub-standardization.md", build_report(package), result, force=force)
    _write_file(root / "reports" / "sithub-standardization.html", render_report_html(payload), result, force=force)

    result.doctor = build_doctor_payload(root)
    return result


def render_onboard_text(result: OnboardResult) -> str:
    lines = [
        "SitHub Onboard",
        "",
        f"Root: {result.root}",
        f"Created: {len(result.created)}",
        f"Updated: {len(result.updated)}",
        f"Skipped: {len(result.skipped)}",
    ]
    if result.warnings:
        lines.append(f"Warnings: {len(result.warnings)}")

    if result.created:
        lines.extend(["", "Created files:"])
        lines.extend(f"  - {path}" for path in result.created)
    if result.updated:
        lines.extend(["", "Updated files:"])
        lines.extend(f"  - {path}" for path in result.updated)
    if result.skipped:
        lines.extend(["", "Skipped existing files:"])
        lines.extend(f"  - {path}" for path in result.skipped)
    if result.warnings:
        lines.extend(["", "Warnings:"])
        lines.extend(f"  - {warning}" for warning in result.warnings)

    if result.doctor is not None:
        lines.extend(
            [
                "",
                f"Doctor status: {result.doctor['status']}",
                "Next commands:",
                "  sit doctor",
                "  sit validate",
                "  sit test",
                "  sit report --format html --output reports/sithub-onboarding.html",
            ]
        )
    return "\n".join(lines) + "\n"


def render_standardize_text(result: OnboardResult) -> str:
    lines = [
        "SitHub Standardize",
        "",
        f"Root: {result.root}",
        f"Created: {len(result.created)}",
        f"Updated: {len(result.updated)}",
        f"Skipped: {len(result.skipped)}",
    ]
    if result.warnings:
        lines.append(f"Warnings: {len(result.warnings)}")

    if result.created:
        lines.extend(["", "Created files:"])
        lines.extend(f"  - {path}" for path in result.created)
    if result.updated:
        lines.extend(["", "Updated files:"])
        lines.extend(f"  - {path}" for path in result.updated)
    if result.skipped:
        lines.extend(["", "Skipped existing files:"])
        lines.extend(f"  - {path}" for path in result.skipped)
    if result.warnings:
        lines.extend(["", "Warnings:"])
        lines.extend(f"  - {warning}" for warning in result.warnings)

    if result.doctor is not None:
        lines.extend(
            [
                "",
                f"Doctor status: {result.doctor['status']}",
                "Next commands:",
                "  sit doctor",
                "  sit validate",
                "  sit test",
                "  sit report --format html --output reports/sithub-standardization.html",
            ]
        )
    return "\n".join(lines) + "\n"


def _infer_name(root: Path) -> str:
    slug = re.sub(r"[^a-zA-Z0-9._-]+", "-", root.name.strip()).strip("-._").lower()
    return slug or "skill-package"


def _infer_description(skill_md: Path, name: str) -> str:
    for line in skill_md.read_text(encoding="utf-8", errors="ignore").splitlines():
        text = line.strip()
        if not text:
            continue
        if text.startswith("#"):
            heading = text.lstrip("#").strip()
            if heading:
                return f"{heading} Skill Package."
            continue
        return text[:200]
    return f"{name} Skill Package."


def _manifest(root: Path, name: str, version: str, description: str, prompts: dict[str, str] | None = None) -> dict[str, Any]:
    if prompts is None:
        prompts = {"skill": "SKILL.md"}
        references = root / "references"
        if references.exists():
            for path in sorted(references.glob("*.md")):
                key = _manifest_key(path.stem, prompts)
                prompts[key] = path.relative_to(root).as_posix()

    manifest = {
        "name": name,
        "version": version,
        "description": description,
        "prompts": prompts,
        "schemas": {
            "input": "schemas/input.schema.json",
            "output": "schemas/output.schema.json",
        },
        "tests": {"golden": "tests/golden.jsonl"},
        "runtime": {"model": "configurable", "temperature": 0},
        "tags": ["codex-skill", "sithub"],
    }
    return manifest


def _write_manifest(
    path: Path,
    root: Path,
    name: str,
    version: str,
    description: str,
    result: OnboardResult,
    *,
    force: bool,
    prompts: dict[str, str] | None = None,
) -> None:
    relative = path.relative_to(result.root).as_posix()
    default_manifest = _manifest(root, name, version, description, prompts=prompts)
    if not path.exists() or force:
        path.write_text(yaml.safe_dump(default_manifest, allow_unicode=True, sort_keys=False), encoding="utf-8")
        result.created.append(relative)
        return

    try:
        existing = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise SitError(f"Invalid YAML in {path}: {exc}") from exc
    if not isinstance(existing, dict):
        raise SitError(f"skill.yaml must contain a mapping: {path}")

    merged = dict(existing)
    changed = False
    for key in ("name", "version", "description"):
        if key not in merged or merged[key] in (None, ""):
            merged[key] = default_manifest[key]
            changed = True

    for key in ("prompts", "schemas", "tests", "runtime"):
        value = merged.get(key)
        if not isinstance(value, dict):
            merged[key] = default_manifest[key]
            changed = True
            continue
        for child_key, child_value in default_manifest[key].items():
            if child_key not in value:
                value[child_key] = child_value
                changed = True

    tags = merged.get("tags")
    if not isinstance(tags, list):
        merged["tags"] = default_manifest["tags"]
        changed = True
    else:
        for tag in default_manifest["tags"]:
            if tag not in tags:
                tags.append(tag)
                changed = True

    if changed:
        path.write_text(yaml.safe_dump(merged, allow_unicode=True, sort_keys=False), encoding="utf-8")
        result.updated.append(relative)
    else:
        result.skipped.append(relative)


def _discover_prompt_sources(root: Path) -> list[Path]:
    sources: list[Path] = []
    seen: set[Path] = set()

    def add(path: Path) -> None:
        resolved = path.resolve()
        if resolved in seen or not path.is_file() or path.suffix.lower() not in {".md", ".txt"}:
            return
        seen.add(resolved)
        sources.append(path)

    skill_md = root / "SKILL.md"
    if skill_md.exists():
        add(skill_md)

    prompts_dir = root / "prompts"
    if prompts_dir.exists():
        for path in sorted(prompts_dir.rglob("*")):
            add(path)

    ignored_names = {
        "agents.md",
        "changelog.md",
        "license",
        "license.md",
        "license.txt",
        "readme.md",
    }
    for path in sorted(root.iterdir()):
        if path.name.lower() in ignored_names:
            continue
        add(path)
    return sources


def _infer_standardize_description(prompt_sources: list[Path], name: str) -> str:
    for path in prompt_sources:
        for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
            text = line.strip()
            if not text:
                continue
            if text.startswith("#"):
                heading = text.lstrip("#").strip()
                if heading:
                    return f"{heading} Skill Package."
                continue
            return text[:200]
    return f"{name} Skill Package."


def _standardize_prompts(
    root: Path,
    package_name: str,
    prompt_sources: list[Path],
    result: OnboardResult,
    *,
    force: bool,
) -> dict[str, str]:
    prompt_map: dict[str, str] = {}
    if not prompt_sources:
        target = root / "prompts" / "system.md"
        _write_file(target, _standard_prompt(package_name), result, force=force)
        prompt_map["system"] = target.relative_to(root).as_posix()
        return prompt_map

    used_targets: set[str] = set()
    for source in prompt_sources:
        target = _standard_prompt_target(root, source)
        relative_target = target.relative_to(root).as_posix()
        if relative_target in used_targets:
            if _is_under_prompts(root, source) or _same_text_file(source, target):
                result.skipped.append(relative_target)
                continue
            target = _dedupe_prompt_target(root, target, used_targets)
            relative_target = target.relative_to(root).as_posix()
        used_targets.add(relative_target)
        if source.resolve() != target.resolve():
            _copy_prompt(source, target, result, force=force)
        else:
            result.skipped.append(relative_target)
        key = _manifest_key(target.stem, prompt_map)
        prompt_map[key] = relative_target
    return prompt_map


def _standard_prompt_target(root: Path, source: Path) -> Path:
    try:
        relative = source.resolve().relative_to((root / "prompts").resolve())
    except ValueError:
        stem = "skill" if source.name == "SKILL.md" else _safe_filename(source.stem)
        relative = Path(f"{stem}{source.suffix.lower()}")

    return root / "prompts" / relative


def _dedupe_prompt_target(root: Path, target: Path, used_targets: set[str]) -> Path:
    candidate = target
    if candidate.relative_to(root).as_posix() not in used_targets:
        return candidate

    stem = _safe_filename(candidate.stem)
    suffix = candidate.suffix or ".md"
    index = 2
    while True:
        candidate = root / "prompts" / f"{stem}_{index}{suffix}"
        if candidate.relative_to(root).as_posix() not in used_targets:
            return candidate
        index += 1


def _is_under_prompts(root: Path, source: Path) -> bool:
    try:
        source.resolve().relative_to((root / "prompts").resolve())
    except ValueError:
        return False
    return True


def _copy_prompt(source: Path, target: Path, result: OnboardResult, *, force: bool) -> None:
    content = source.read_text(encoding="utf-8", errors="ignore")
    _write_file(target, content, result, force=force)


def _same_text_file(left: Path, right: Path) -> bool:
    if not right.exists():
        return False
    return left.read_text(encoding="utf-8", errors="ignore") == right.read_text(encoding="utf-8", errors="ignore")


def _safe_filename(value: str) -> str:
    return re.sub(r"[^a-zA-Z0-9._-]+", "-", value.strip()).strip("-._").lower() or "prompt"


def _standard_prompt(name: str) -> str:
    return f"""# {name}

Describe the Skill behavior here.

Return JSON that conforms to `schemas/output.schema.json`.
"""


def _manifest_key(value: str, existing: dict[str, str]) -> str:
    key = re.sub(r"[^a-zA-Z0-9_]+", "_", value.strip().lower()).strip("_") or "reference"
    candidate = key
    index = 2
    while candidate in existing:
        candidate = f"{key}_{index}"
        index += 1
    return candidate


def _input_schema() -> dict[str, Any]:
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "type": "object",
        "additionalProperties": True,
        "properties": {
            "task": {"type": "string"},
            "project_path": {"type": "string"},
            "source_path": {"type": "string"},
            "text": {"type": "string"},
        },
    }


def _output_schema() -> dict[str, Any]:
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "type": "object",
        "additionalProperties": True,
        "required": ["status"],
        "properties": {
            "status": {"type": "string"},
            "summary": {"type": "string"},
            "artifacts": {
                "type": "array",
                "items": {"type": "string"},
            },
            "risks": {
                "type": "array",
                "items": {"type": "string"},
            },
        },
    }


def _golden_case(name: str) -> dict[str, Any]:
    return {
        "case_id": "onboarding-smoke",
        "input": {"task": f"Run {name} on a representative input."},
        "expected": {"status": "ok", "summary": "Representative output conforms to the onboarding schema."},
        "match_mode": "schema_only",
    }


def _ensure_dir(path: Path, result: OnboardResult) -> None:
    if path.exists():
        result.skipped.append(path.relative_to(result.root).as_posix() + "/")
        return
    path.mkdir(parents=True, exist_ok=True)
    result.created.append(path.relative_to(result.root).as_posix() + "/")


def _write_json(path: Path, data: dict[str, Any], result: OnboardResult, *, force: bool) -> None:
    _write_file(path, json.dumps(data, ensure_ascii=False, indent=2) + "\n", result, force=force)


def _write_file(path: Path, content: str, result: OnboardResult, *, force: bool) -> None:
    relative = path.relative_to(result.root).as_posix()
    if path.exists() and not force:
        result.skipped.append(relative)
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    result.created.append(relative)


def _ensure_git(root: Path, remote: str | None, result: OnboardResult) -> None:
    if not is_git_repo(root):
        if _run_git_quiet(["init", "-b", "main"], cwd=root) != 0 and _run_git_quiet(["init"], cwd=root) != 0:
            raise SitError("git command failed: git init")
        result.created.append(".git/")
    else:
        result.skipped.append(".git/")

    if remote is None:
        return

    try:
        remotes = git_output(["remote"], cwd=root).splitlines()
    except SitError as exc:
        result.warnings.append(str(exc))
        return

    if "origin" in remotes:
        result.skipped.append("git remote origin")
        return

    if _run_git_quiet(["remote", "add", "origin", remote], cwd=root) == 0:
        result.created.append("git remote origin")
    else:
        result.warnings.append(f"failed to add Git remote origin: {remote}")


def _run_git_quiet(args: list[str], *, cwd: Path) -> int:
    try:
        completed = subprocess.run(["git", *args], cwd=cwd, check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except FileNotFoundError as exc:
        raise SitError("git executable not found") from exc
    return completed.returncode
