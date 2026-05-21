from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any

import yaml

from .errors import SitError

RESOURCE_GROUPS = {
    "scripts": "script",
    "assets": "asset",
    "references": "reference",
}


@dataclass(frozen=True)
class SkillPackage:
    root: Path
    manifest_path: Path
    manifest: dict[str, Any]

    @property
    def name(self) -> str | None:
        value = self.manifest.get("name")
        return value if isinstance(value, str) else None

    @property
    def version(self) -> str | None:
        value = self.manifest.get("version")
        return _normalize_version(value)

    @property
    def description(self) -> str | None:
        value = self.manifest.get("description")
        return value if isinstance(value, str) else None

    def resolve_manifest_path(self, value: str) -> Path:
        return (self.root / value).resolve()

    def prompt_paths(self) -> dict[str, Path]:
        return _resolve_path_map(self, "prompts")

    def schema_paths(self) -> dict[str, Path]:
        return _resolve_path_map(self, "schemas")

    def test_paths(self) -> dict[str, Path]:
        return _resolve_path_map(self, "tests")

    def resource_paths(self) -> dict[str, dict[str, Path]]:
        return {label: _resolve_resource_map(self, manifest_key) for manifest_key, label in RESOURCE_GROUPS.items()}

    def report_dir(self) -> Path:
        return (self.root / "reports").resolve()


def load_package(package_path: str | Path) -> SkillPackage:
    root = Path(package_path).expanduser().resolve()
    if root.is_file():
        if root.name != "skill.yaml":
            raise SitError(f"Expected a package directory or skill.yaml, got file: {root}")
        manifest_path = root
        root = root.parent
    else:
        manifest_path = root / "skill.yaml"

    if not manifest_path.exists():
        raise SitError(f"Missing skill.yaml: {manifest_path}")

    try:
        data = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise SitError(f"Invalid YAML in {manifest_path}: {exc}") from exc

    if not isinstance(data, dict):
        raise SitError(f"skill.yaml must contain a mapping: {manifest_path}")

    return SkillPackage(root=root, manifest_path=manifest_path, manifest=data)


def load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SitError(f"Invalid JSON in {path}: line {exc.lineno}, column {exc.colno}: {exc.msg}") from exc


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for index, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError as exc:
            raise SitError(f"Invalid JSONL in {path}: line {index}: {exc.msg}") from exc
        if not isinstance(record, dict):
            raise SitError(f"JSONL line {index} in {path} must be an object")
        records.append(record)
    return records


def _resolve_path_map(package: SkillPackage, key: str) -> dict[str, Path]:
    value = package.manifest.get(key, {})
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise SitError(f"skill.yaml field '{key}' must be a mapping")

    paths: dict[str, Path] = {}
    for name, relative_path in value.items():
        if isinstance(relative_path, str):
            paths[str(name)] = package.resolve_manifest_path(relative_path)
        else:
            raise SitError(f"skill.yaml field '{key}.{name}' must be a path string")
    return paths


def _resolve_resource_map(package: SkillPackage, key: str) -> dict[str, Path]:
    paths: dict[str, Path] = {}

    resources = package.manifest.get("resources", {})
    if resources is not None and not isinstance(resources, dict):
        raise SitError("skill.yaml field 'resources' must be a mapping")
    if isinstance(resources, dict):
        paths.update(_resource_paths_from_value(package, resources.get(key)))

    paths.update(_resource_paths_from_value(package, package.manifest.get(key)))

    default_dir = package.root / key
    if default_dir.exists() and default_dir.is_dir():
        for path in sorted(default_dir.rglob("*")):
            if not path.is_file() or _skip_resource_file(path):
                continue
            paths.setdefault(_resource_display_name(package, path), path.resolve())

    return paths


def _resource_paths_from_value(package: SkillPackage, value: Any) -> dict[str, Path]:
    if value is None:
        return {}
    if isinstance(value, str):
        path = package.resolve_manifest_path(value)
        return {_resource_display_name(package, path): path}
    if isinstance(value, list):
        paths: dict[str, Path] = {}
        for item in value:
            if not isinstance(item, str):
                raise SitError("skill.yaml resource lists must contain path strings")
            path = package.resolve_manifest_path(item)
            paths[_resource_display_name(package, path)] = path
        return paths
    if isinstance(value, dict):
        paths = {}
        for name, relative_path in value.items():
            if not isinstance(relative_path, str):
                raise SitError(f"skill.yaml resource field '{name}' must be a path string")
            path = package.resolve_manifest_path(relative_path)
            paths[_resource_display_name(package, path)] = path
        return paths
    raise SitError("skill.yaml resource fields must be a path string, list, or mapping")


def _resource_display_name(package: SkillPackage, path: Path) -> str:
    try:
        return path.resolve().relative_to(package.root).as_posix()
    except ValueError:
        return path.name


def _skip_resource_file(path: Path) -> bool:
    if path.suffix in {".pyc", ".pyo"}:
        return True
    return any(part.startswith(".") or part == "__pycache__" for part in path.parts)


def _normalize_version(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        return value
    if isinstance(value, int) and not isinstance(value, bool):
        return f"{value}.0.0"
    if isinstance(value, float):
        text = str(value)
        return f"{text}.0" if text.count(".") == 1 else text
    return str(value)
