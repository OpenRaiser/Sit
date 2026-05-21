from __future__ import annotations

from datetime import date
import hashlib
import io
import json
from pathlib import Path
import tarfile

import yaml

from .deps import find_reverse_dependencies
from .errors import SitError
from .gate import VersionGateResult, check_release_gate_against_head, format_gate_failure
from .git import git_output, is_git_repo, run_git
from .package import SkillPackage, load_package
from .report import build_report
from .validate import run_golden_schema_tests, validate_package


def release_package(
    package: SkillPackage,
    bump: str,
    *,
    no_git_tag: bool = False,
    no_version_gate: bool = False,
    bundle: bool = False,
) -> str:
    validation = validate_package(package)
    if not validation.ok:
        raise SitError("release blocked: validation failed")
    tests = run_golden_schema_tests(package)
    if not tests.ok:
        raise SitError("release blocked: golden tests failed")
    gate: VersionGateResult | None = None
    if not no_version_gate:
        gate = check_release_gate_against_head(package, bump)
        if not gate.ok:
            raise SitError(format_gate_failure(gate))

    old_version = package.version
    if old_version is None:
        raise SitError("release blocked: missing package version")

    new_version = bump_version(old_version, bump)
    manifest = dict(package.manifest)
    manifest["version"] = new_version
    package.manifest_path.write_text(yaml.safe_dump(manifest, allow_unicode=True, sort_keys=False), encoding="utf-8")

    refreshed = load_package(package.root)
    reverse_deps = find_reverse_dependencies(refreshed)
    _append_changelog(refreshed.root / "CHANGELOG.md", new_version, gate=gate, validation=validation, tests=tests)
    report_path = refreshed.report_dir() / f"release-v{new_version}.md"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(
        _build_release_report(refreshed, gate=gate, validation=validation, tests=tests, reverse_deps=reverse_deps),
        encoding="utf-8",
    )
    bundle_path = _write_release_bundle(refreshed) if bundle else None

    tag_name = f"v{new_version}"
    tagged = False
    if not no_git_tag and is_git_repo(refreshed.root) and _has_head(refreshed.root):
        git_add_paths = [str(refreshed.manifest_path), str(refreshed.root / "CHANGELOG.md"), str(report_path)]
        if bundle_path is not None:
            git_add_paths.append(str(bundle_path))
        run_git(["add", "-f", *git_add_paths], cwd=refreshed.root)
        run_git(
            [
                "commit",
                "-m",
                f"release: {refreshed.name} v{new_version}",
                "--",
                *git_add_paths,
            ],
            cwd=refreshed.root,
        )
        run_git(["tag", "-a", tag_name, "-m", f"Release {tag_name}"], cwd=refreshed.root)
        tagged = True

    message = f"Released {refreshed.name}@{new_version} (was {old_version}); report: {report_path}"
    if bundle_path is not None:
        message += f"; bundle: {bundle_path}"
    message += "; reverse deps: " + _reverse_dep_count_label(reverse_deps)
    return message + (
        f"; git tag: {tag_name}" if tagged else "; git tag: skipped"
    )


def bump_version(version: str, bump: str) -> str:
    parts = version.split(".")
    if len(parts) != 3:
        raise SitError(f"Expected semantic version MAJOR.MINOR.PATCH, got: {version}")
    try:
        major, minor, patch = (int(part) for part in parts)
    except ValueError as exc:
        raise SitError(f"Expected numeric semantic version, got: {version}") from exc

    if bump == "major":
        return f"{major + 1}.0.0"
    if bump == "minor":
        return f"{major}.{minor + 1}.0"
    if bump == "patch":
        return f"{major}.{minor}.{patch + 1}"
    raise SitError(f"Unknown release bump: {bump}")


def _append_changelog(path: Path, version: str, *, gate: VersionGateResult | None, validation, tests) -> None:
    existing = path.read_text(encoding="utf-8") if path.exists() else "# Changelog\n"
    lines = [
        f"## {version} - {date.today().isoformat()}",
        "",
        "- Released with `sit release`.",
        f"- Validation: {'pass' if validation.ok else 'fail'}.",
        f"- Golden tests: {'pass' if tests.ok else 'fail'}.",
    ]
    lines.extend(["", *_release_note_lines(gate=gate, validation=validation, tests=tests)])
    entry = "\n" + "\n".join(lines) + "\n"
    path.write_text(existing.rstrip() + "\n" + entry, encoding="utf-8")


def _build_release_report(package: SkillPackage, *, gate: VersionGateResult | None, validation, tests, reverse_deps: dict) -> str:
    lines = [
        build_report(package).rstrip(),
        "",
        "## Release Summary",
        "",
        f"- Validation: {'pass' if validation.ok else 'fail'}",
        f"- Golden tests: {'pass' if tests.ok else 'fail'}",
    ]
    if gate is None:
        lines.append("- Version gate: skipped.")
    else:
        lines.extend(f"- {line}" for line in gate.summary_lines())
    lines.extend(["", *_release_note_lines(gate=gate, validation=validation, tests=tests, code=True)])
    lines.extend(["", "## Reverse Dependencies", ""])
    dependencies = reverse_deps.get("dependencies", [])
    if dependencies:
        for item in dependencies:
            lines.append(f"- {item['status']}: `{item['dependent']}` at `{item['path']}`")
            for message in item.get("messages", []):
                lines.append(f"  - {message}")
    else:
        lines.append("- <none found in sibling directories>")
    return "\n".join(lines) + "\n"


def _semantic_change_messages(gate: VersionGateResult) -> list[str]:
    if gate.diff is None:
        return []
    return [
        event.message
        for event in gate.diff.events
        if event.category not in {"package", "risk"} and not event.message.startswith("MANIFEST changed version: ")
    ]


def _release_note_lines(*, gate: VersionGateResult | None, validation, tests, code: bool = False) -> list[str]:
    grouped = _group_release_events(gate)
    quote = "`" if code else ""
    lines: list[str] = []
    for heading in ("Breaking", "Changes", "Fixes"):
        lines.extend([f"### {heading}", ""])
        events = grouped[heading.lower()]
        if events:
            lines.extend(f"- {quote}{message}{quote}" for message in events)
        else:
            lines.append("- <none>")
        lines.append("")

    lines.extend(["### Risk", ""])
    if gate is None:
        lines.append("- Version gate: skipped.")
    else:
        risk = gate.diff.risk if gate.diff is not None else "not checked"
        suggested = gate.diff.suggested_bump if gate.diff is not None else gate.required_bump
        lines.extend(
            [
                f"- Release risk: {risk}.",
                f"- Suggested bump: {suggested}.",
                f"- Version gate: required {gate.required_bump}, actual {gate.actual_bump}.",
            ]
        )
    lines.extend(
        [
            f"- Validation: {'pass' if validation.ok else 'fail'}.",
            f"- Golden tests: {'pass' if tests.ok else 'fail'} ({_golden_count(tests)}).",
            "",
            "### Reproduce",
            "",
            "- `python3 -m sit.cli validate .`",
            "- `python3 -m sit.cli test .`",
            "- `python3 -m sit.cli report .`",
        ]
    )
    return lines


def _group_release_events(gate: VersionGateResult | None) -> dict[str, list[str]]:
    groups = {"breaking": [], "changes": [], "fixes": []}
    if gate is None or gate.diff is None:
        return groups

    for event in gate.diff.events:
        if event.category in {"package", "risk"} or event.message.startswith("MANIFEST changed version: "):
            continue
        if event.breaking:
            groups["breaking"].append(event.message)
        elif event.category in {"test", "golden"} or "fix" in event.message.lower():
            groups["fixes"].append(event.message)
        elif event.changed:
            groups["changes"].append(event.message)
    return groups


def _golden_count(tests) -> str:
    for message in reversed(tests.messages):
        if message.startswith("SUMMARY "):
            return message.removeprefix("SUMMARY ").removesuffix(" golden cases passed")
    return "n/a"


def _write_release_bundle(package: SkillPackage) -> Path:
    name = _safe_name(package.name or "skill-package")
    version = package.version or "0.0.0"
    bundle_dir = package.root / "dist"
    bundle_dir.mkdir(parents=True, exist_ok=True)
    bundle_path = bundle_dir / f"{name}-v{version}.tar.gz"
    root_name = f"{name}-v{version}"

    files = _bundle_files(package)
    manifest_entries = [_bundle_entry(package, path) for path in files]
    reproduce = _reproduce_script()
    manifest_entries.append(_bytes_entry("reproduce.sh", reproduce))
    manifest = {
        "schema_version": "sit.bundle_manifest.v1",
        "package": {
            "name": package.name or "<unknown>",
            "version": package.version or "<unknown>",
        },
        "generated": date.today().isoformat(),
        "files": manifest_entries,
    }
    manifest_bytes = json.dumps(manifest, ensure_ascii=False, indent=2).encode("utf-8") + b"\n"

    with tarfile.open(bundle_path, "w:gz") as archive:
        for path in files:
            archive.add(path, arcname=f"{root_name}/{path.relative_to(package.root).as_posix()}")
        _add_bytes(archive, f"{root_name}/reproduce.sh", reproduce, mode=0o755)
        _add_bytes(archive, f"{root_name}/manifest.json", manifest_bytes)
    return bundle_path


def _bundle_files(package: SkillPackage) -> list[Path]:
    paths: set[Path] = {package.manifest_path}
    for group in (package.prompt_paths(), package.schema_paths(), package.test_paths()):
        paths.update(path for path in group.values() if path.exists() and path.is_file())
    for group in package.resource_paths().values():
        paths.update(path for path in group.values() if path.exists() and path.is_file())

    changelog = package.root / "CHANGELOG.md"
    if changelog.exists() and changelog.is_file():
        paths.add(changelog)

    report_dir = package.report_dir()
    if report_dir.exists():
        paths.update(path for path in report_dir.rglob("*") if path.is_file() and not _skip_bundle_file(package, path))

    return sorted(paths, key=lambda path: path.relative_to(package.root).as_posix())


def _bundle_entry(package: SkillPackage, path: Path) -> dict[str, object]:
    data = path.read_bytes()
    return _bytes_entry(path.relative_to(package.root).as_posix(), data)


def _bytes_entry(path: str, data: bytes) -> dict[str, object]:
    return {
        "path": path,
        "size_bytes": len(data),
        "sha256": hashlib.sha256(data).hexdigest(),
    }


def _add_bytes(archive: tarfile.TarFile, arcname: str, data: bytes, *, mode: int = 0o644) -> None:
    info = tarfile.TarInfo(arcname)
    info.size = len(data)
    info.mode = mode
    archive.addfile(info, io.BytesIO(data))


def _reproduce_script() -> bytes:
    return "\n".join(
        [
            "#!/usr/bin/env bash",
            "set -euo pipefail",
            "python3 -m sit.cli validate .",
            "python3 -m sit.cli test .",
            "python3 -m sit.cli report .",
            "",
        ]
    ).encode("utf-8")


def _skip_bundle_file(package: SkillPackage, path: Path) -> bool:
    try:
        relative = path.relative_to(package.root)
    except ValueError:
        return True
    return any(part.startswith(".") or part == "__pycache__" or part == "dist" for part in relative.parts)


def _safe_name(value: str) -> str:
    safe = "".join(char if char.isalnum() or char in {"-", "_", "."} else "-" for char in value.lower())
    return safe.strip("-") or "skill-package"


def _reverse_dep_count_label(reverse_deps: dict) -> str:
    counts = reverse_deps.get("counts", {})
    return (
        f"{counts.get('compatible', 0)} compatible, "
        f"{counts.get('review', 0)} review, "
        f"{counts.get('incompatible', 0)} incompatible"
    )


def _has_head(path: Path) -> bool:
    try:
        git_output(["rev-parse", "--verify", "HEAD"], cwd=path)
    except SitError:
        return False
    return True
