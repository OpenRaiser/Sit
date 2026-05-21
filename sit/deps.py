from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from .diff import diff_packages
from .errors import SitError
from .package import SkillPackage, load_package


@dataclass(frozen=True)
class DependencyCheck:
    name: str
    path: str
    version: str | None
    version_range: str | None
    ok: bool = True
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    risk: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "path": self.path,
            "version": self.version,
            "version_range": self.version_range,
            "ok": self.ok,
            "warnings": self.warnings,
            "errors": self.errors,
            "risk": self.risk,
        }


def check_dependencies(package: SkillPackage) -> dict[str, Any]:
    deps_path = package.root / "deps.yaml"
    if not deps_path.exists():
        return {
            "schema_version": "sit.deps.v1",
            "status": "pass",
            "ok": True,
            "warnings": [],
            "dependencies": [],
            "message": "No deps.yaml found.",
        }

    data = _load_deps_yaml(deps_path)
    checks = [_check_dependency(package, item) for item in _dependency_items(data)]
    errors = [message for check in checks for message in check.errors]
    warnings = [message for check in checks for message in check.warnings]
    status = "fail" if errors else ("warn" if warnings else "pass")
    return {
        "schema_version": "sit.deps.v1",
        "status": status,
        "ok": not errors,
        "warnings": warnings,
        "dependencies": [check.to_dict() for check in checks],
        "message": f"{len(checks)} dependencies checked.",
    }


def render_deps_text(payload: dict[str, Any]) -> str:
    lines = ["SitHub Dependencies", "", f"Status: {payload['status']}", payload["message"], ""]
    dependencies = payload["dependencies"]
    if not dependencies:
        lines.append("- <none>")
        return "\n".join(lines) + "\n"

    for item in dependencies:
        lines.append(f"- {item['name']}: {item['version'] or '<unknown>'} at {item['path']}")
        if item.get("version_range"):
            lines.append(f"  range: {item['version_range']}")
        if item.get("risk"):
            lines.append(f"  schema risk: {item['risk']}")
        for warning in item["warnings"]:
            lines.append(f"  WARN {warning}")
        for error in item["errors"]:
            lines.append(f"  ERR {error}")
    return "\n".join(lines) + "\n"


def dependency_warnings_for_commit(package: SkillPackage) -> list[str]:
    payload = check_dependencies(package)
    return [f"dependency warning: {message}" for message in payload["warnings"]]


def find_reverse_dependencies(package: SkillPackage, *, workspace: Path | None = None) -> dict[str, Any]:
    workspace = workspace or package.root.parent
    records = []
    if not workspace.exists() or not workspace.is_dir():
        return _reverse_payload(records)

    for candidate in sorted(workspace.iterdir()):
        if not candidate.is_dir() or candidate.resolve() == package.root:
            continue
        deps_path = candidate / "deps.yaml"
        manifest_path = candidate / "skill.yaml"
        if not deps_path.exists() or not manifest_path.exists():
            continue
        try:
            dependent = load_package(candidate)
            deps_data = _load_deps_yaml(deps_path)
        except SitError:
            continue
        for item in _dependency_items(deps_data):
            record = _reverse_dependency_record(package, dependent, item)
            if record is not None:
                records.append(record)
    return _reverse_payload(records)


def _load_deps_yaml(path: Path) -> dict[str, Any]:
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as exc:
        raise SitError(f"Invalid YAML in {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise SitError(f"deps.yaml must contain a mapping: {path}")
    return data


def _dependency_items(data: dict[str, Any]) -> list[dict[str, Any]]:
    value = data.get("dependencies", data.get("deps", []))
    if isinstance(value, dict):
        items = []
        for name, entry in value.items():
            if not isinstance(entry, dict):
                raise SitError(f"dependency '{name}' must be a mapping")
            items.append({"name": str(name), **entry})
        return items
    if isinstance(value, list):
        items = []
        for index, entry in enumerate(value, start=1):
            if not isinstance(entry, dict):
                raise SitError(f"dependency #{index} must be a mapping")
            items.append(entry)
        return items
    raise SitError("deps.yaml field 'dependencies' must be a list or mapping")


def _check_dependency(package: SkillPackage, item: dict[str, Any]) -> DependencyCheck:
    name = str(item.get("name") or "<unnamed>")
    raw_path = item.get("path")
    version_range = item.get("version") or item.get("version_range")
    warnings: list[str] = []
    errors: list[str] = []
    risk: str | None = None

    if not isinstance(raw_path, str):
        return DependencyCheck(name=name, path="<missing>", version=None, version_range=_range_text(version_range), ok=False, errors=["missing local path"])

    dep_path = (package.root / raw_path).resolve()
    try:
        dependency = load_package(dep_path)
    except SitError as exc:
        return DependencyCheck(
            name=name,
            path=str(dep_path),
            version=None,
            version_range=_range_text(version_range),
            ok=False,
            errors=[str(exc)],
        )

    if version_range and not _version_satisfies(dependency.version, str(version_range)):
        errors.append(f"version {dependency.version or '<unknown>'} does not satisfy {version_range}")

    baseline_path = item.get("baseline_path") or item.get("previous_path")
    if baseline_path is not None:
        if not isinstance(baseline_path, str):
            errors.append("baseline_path must be a local path string")
        else:
            try:
                baseline = load_package((package.root / baseline_path).resolve())
                diff = diff_packages(baseline, dependency)
                risk = diff.risk
                if diff.breaking:
                    warnings.append(f"{name} schema diff is breaking-change against {baseline_path}")
                elif diff.changed:
                    warnings.append(f"{name} changed with risk {diff.risk} against {baseline_path}")
            except SitError as exc:
                errors.append(f"baseline check failed: {exc}")

    return DependencyCheck(
        name=name,
        path=str(dep_path),
        version=dependency.version,
        version_range=_range_text(version_range),
        ok=not errors,
        warnings=warnings,
        errors=errors,
        risk=risk,
    )


def _reverse_dependency_record(package: SkillPackage, dependent: SkillPackage, item: dict[str, Any]) -> dict[str, Any] | None:
    raw_path = item.get("path")
    if not isinstance(raw_path, str):
        return None
    dep_path = (dependent.root / raw_path).resolve()
    if dep_path != package.root:
        return None

    version_range = _range_text(item.get("version") or item.get("version_range"))
    messages: list[str] = []
    status = "compatible"
    if version_range and not _version_satisfies(package.version, version_range):
        status = "incompatible"
        messages.append(f"version {package.version or '<unknown>'} does not satisfy {version_range}")

    baseline_path = item.get("baseline_path") or item.get("previous_path")
    if isinstance(baseline_path, str):
        try:
            baseline = load_package((dependent.root / baseline_path).resolve())
            diff = diff_packages(baseline, package)
            if diff.breaking:
                status = "incompatible"
                messages.append(f"schema diff is breaking-change against {baseline_path}")
            elif diff.changed and status == "compatible":
                status = "review"
                messages.append(f"schema diff is {diff.risk} against {baseline_path}")
        except SitError as exc:
            status = "review" if status == "compatible" else status
            messages.append(f"baseline check failed: {exc}")

    return {
        "dependent": dependent.name or dependent.root.name,
        "path": str(dependent.root),
        "version_range": version_range,
        "status": status,
        "messages": messages,
    }


def _reverse_payload(records: list[dict[str, Any]]) -> dict[str, Any]:
    counts = {"compatible": 0, "review": 0, "incompatible": 0}
    for record in records:
        status = record.get("status")
        if status in counts:
            counts[status] += 1
    return {
        "schema_version": "sit.reverse_deps.v1",
        "counts": counts,
        "dependencies": records,
    }


def _range_text(value: Any) -> str | None:
    return str(value) if value is not None else None


def _version_satisfies(version: str | None, expression: str) -> bool:
    if version is None:
        return False
    if expression.strip() in {"", "*"}:
        return True
    current = _parse_version(version)
    if current is None:
        return False

    for raw_part in expression.split(","):
        part = raw_part.strip()
        if not part:
            continue
        operator = "=="
        expected_text = part
        for candidate in (">=", "<=", "==", ">", "<"):
            if part.startswith(candidate):
                operator = candidate
                expected_text = part[len(candidate) :].strip()
                break
        expected = _parse_version(expected_text)
        if expected is None or not _compare_version(current, expected, operator):
            return False
    return True


def _parse_version(version: str) -> tuple[int, int, int] | None:
    parts = version.split(".")
    if len(parts) != 3:
        return None
    try:
        return tuple(int(part) for part in parts)  # type: ignore[return-value]
    except ValueError:
        return None


def _compare_version(current: tuple[int, int, int], expected: tuple[int, int, int], operator: str) -> bool:
    if operator == ">=":
        return current >= expected
    if operator == "<=":
        return current <= expected
    if operator == ">":
        return current > expected
    if operator == "<":
        return current < expected
    return current == expected
