from __future__ import annotations

from dataclasses import dataclass, field
import difflib
import json
from pathlib import Path
import re
from typing import Any

from .errors import SitError
from .package import SkillPackage, load_json, load_jsonl
from .script_summary import summarize_script_change


@dataclass(frozen=True)
class DiffEvent:
    message: str
    category: str
    changed: bool = False
    breaking: bool = False
    details: dict[str, Any] | None = None

    @property
    def severity(self) -> str:
        if self.breaking:
            return "breaking"
        if self.changed:
            return "changed"
        return "info"

    def to_dict(self) -> dict[str, Any]:
        data: dict[str, Any] = {
            "category": self.category,
            "severity": self.severity,
            "changed": self.changed,
            "breaking": self.breaking,
            "message": self.message,
        }
        if self.details:
            data["details"] = self.details
        return data


@dataclass(frozen=True)
class TextDiff:
    kind: str
    name: str
    old_path: str
    new_path: str
    added_lines: int
    removed_lines: int
    headings: list[str] = field(default_factory=list)
    variables: list[str] = field(default_factory=list)
    lines: list[str] = field(default_factory=list)

    @property
    def summary(self) -> str:
        details = [f"+{self.added_lines} -{self.removed_lines}"]
        if self.headings:
            details.append("headings: " + ", ".join(self.headings[:5]))
        if self.variables:
            details.append("vars: " + ", ".join(self.variables[:8]))
        return f"{self.kind.upper()} summary {self.name}: " + "; ".join(details)

    def to_dict(self, *, include_lines: bool = False) -> dict[str, Any]:
        data: dict[str, Any] = {
            "kind": self.kind,
            "name": self.name,
            "old_path": self.old_path,
            "new_path": self.new_path,
            "added_lines": self.added_lines,
            "removed_lines": self.removed_lines,
            "headings": self.headings,
            "variables": self.variables,
            "summary": self.summary,
        }
        if include_lines:
            data["lines"] = self.lines
        return data


@dataclass
class PackageDiff:
    messages: list[str] = field(default_factory=list)
    events: list[DiffEvent] = field(default_factory=list)
    text_diffs: list[TextDiff] = field(default_factory=list)
    breaking: bool = False
    changed: bool = False

    def add(
        self,
        message: str,
        *,
        changed: bool = False,
        breaking: bool = False,
        category: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        self.messages.append(message)
        self.events.append(
            DiffEvent(
                message=message,
                category=category or _infer_category(message),
                changed=changed or breaking,
                breaking=breaking,
                details=details,
            )
        )
        self.changed = self.changed or changed or breaking
        self.breaking = self.breaking or breaking

    @property
    def risk(self) -> str:
        if self.breaking:
            return "breaking-change"
        if self.changed:
            return "review-required"
        return "no-change"

    @property
    def suggested_bump(self) -> str:
        if self.breaking:
            return "major"
        if self.changed:
            return "minor"
        return "patch"

    def to_dict(
        self,
        old: SkillPackage,
        new: SkillPackage,
        *,
        old_source: str | None = None,
        new_source: str | None = None,
        include_text_diffs: bool = False,
    ) -> dict[str, Any]:
        return {
            "schema_version": "sit.diff.v1",
            "old": _package_ref(old, source=old_source),
            "new": _package_ref(new, source=new_source),
            "changed": self.changed,
            "breaking": self.breaking,
            "risk": self.risk,
            "suggested_bump": self.suggested_bump,
            "messages": self.messages,
            "events": [event.to_dict() for event in self.events],
            "text_diffs": [text_diff.to_dict(include_lines=include_text_diffs) for text_diff in self.text_diffs],
        }


def diff_packages(old: SkillPackage, new: SkillPackage) -> PackageDiff:
    result = PackageDiff()
    result.add(
        f"PACKAGE {old.name or '<unknown>'}@{old.version or '<unknown>'} -> {new.name or '<unknown>'}@{new.version or '<unknown>'}",
        category="package",
    )

    _diff_manifest(result, old.manifest, new.manifest)
    _diff_path_group(result, "prompt", old.prompt_paths(), new.prompt_paths(), compare_text=True, collect_text_diff=True)
    _diff_resource_groups(result, old, new)
    _diff_schema_group(result, old.schema_paths(), new.schema_paths())
    _diff_path_group(result, "test", old.test_paths(), new.test_paths(), compare_text=True)
    _diff_golden_cases(result, old, new)

    if result.breaking:
        result.add("RISK breaking-change", breaking=True, category="risk")
    elif result.changed:
        result.add("RISK review-required", changed=True, category="risk")
    else:
        result.add("RISK no-change", category="risk")

    return result


def _diff_manifest(result: PackageDiff, old: dict[str, Any], new: dict[str, Any]) -> None:
    ignored = {"prompts", "schemas", "tests"}
    old_keys = set(old) - ignored
    new_keys = set(new) - ignored

    for key in sorted(new_keys - old_keys):
        result.add(f"MANIFEST added {key}", changed=True)
    for key in sorted(old_keys - new_keys):
        result.add(f"MANIFEST removed {key}", changed=True)
    for key in sorted(old_keys & new_keys):
        if old[key] != new[key]:
            result.add(f"MANIFEST changed {key}: {_short(old[key])} -> {_short(new[key])}", changed=True)


def _diff_path_group(
    result: PackageDiff,
    label: str,
    old_paths: dict[str, Path],
    new_paths: dict[str, Path],
    *,
    compare_text: bool,
    collect_text_diff: bool = False,
) -> None:
    old_names = set(old_paths)
    new_names = set(new_paths)

    for name in sorted(new_names - old_names):
        result.add(f"{label.upper()} added {name}: {new_paths[name]}", changed=True)
    for name in sorted(old_names - new_names):
        result.add(f"{label.upper()} removed {name}: {old_paths[name]}", changed=True)

    if not compare_text:
        return

    for name in sorted(old_names & new_names):
        old_path = old_paths[name]
        new_path = new_paths[name]
        if not old_path.exists() or not new_path.exists():
            continue
        old_text = old_path.read_text(encoding="utf-8")
        new_text = new_path.read_text(encoding="utf-8")
        if old_text != new_text:
            detail = ""
            if collect_text_diff:
                text_diff = _build_text_diff(label, name, old_path, new_path, old_text, new_text)
                result.text_diffs.append(text_diff)
                detail = " (" + _text_diff_inline_summary(text_diff) + ")"
            result.add(f"{label.upper()} changed {name}: {old_path.name} -> {new_path.name}{detail}", changed=True)


def _diff_resource_groups(result: PackageDiff, old: SkillPackage, new: SkillPackage) -> None:
    old_groups = old.resource_paths()
    new_groups = new.resource_paths()
    for label in ("script", "asset", "reference"):
        _diff_resource_group(result, label, old_groups.get(label, {}), new_groups.get(label, {}))


def _diff_resource_group(result: PackageDiff, label: str, old_paths: dict[str, Path], new_paths: dict[str, Path]) -> None:
    old_names = set(old_paths)
    new_names = set(new_paths)

    for name in sorted(new_names - old_names):
        details = _resource_details(label, "added", None, new_paths[name])
        result.add(_resource_message(label, "added", name), changed=True, category=label, details=details)
    for name in sorted(old_names - new_names):
        details = _resource_details(label, "removed", old_paths[name], None)
        result.add(_resource_message(label, "removed", name), changed=True, category=label, details=details)

    for name in sorted(old_names & new_names):
        old_path = old_paths[name]
        new_path = new_paths[name]
        if not old_path.exists() or not new_path.exists():
            continue
        if old_path.read_bytes() != new_path.read_bytes():
            detail = ""
            if label == "reference":
                text_diff = _try_build_text_diff(label, name, old_path, new_path)
                if text_diff is not None:
                    result.text_diffs.append(text_diff)
                    detail = " (" + _text_diff_inline_summary(text_diff) + ")"
            details = _resource_details(label, "changed", old_path, new_path)
            result.add(_resource_message(label, "changed", name, detail=detail), changed=True, category=label, details=details)


def _resource_message(label: str, action: str, name: str, *, detail: str = "") -> str:
    message = f"{label.upper()} {action} {name}{detail}"
    if label == "script":
        message += " (review required; cover with runner or targeted tests)"
    return message


def _resource_details(label: str, action: str, old_path: Path | None, new_path: Path | None) -> dict[str, Any] | None:
    if label != "script":
        return None
    return summarize_script_change(action, old_path, new_path)


def _try_build_text_diff(kind: str, name: str, old_path: Path, new_path: Path) -> TextDiff | None:
    try:
        old_text = old_path.read_text(encoding="utf-8")
        new_text = new_path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return None
    return _build_text_diff(kind, name, old_path, new_path, old_text, new_text)


def _build_text_diff(kind: str, name: str, old_path: Path, new_path: Path, old_text: str, new_text: str) -> TextDiff:
    diff_lines = list(
        difflib.unified_diff(
            old_text.splitlines(),
            new_text.splitlines(),
            fromfile=str(old_path.name),
            tofile=str(new_path.name),
            lineterm="",
        )
    )
    added = sum(1 for line in diff_lines if line.startswith("+") and not line.startswith("+++"))
    removed = sum(1 for line in diff_lines if line.startswith("-") and not line.startswith("---"))
    return TextDiff(
        kind=kind,
        name=name,
        old_path=str(old_path),
        new_path=str(new_path),
        added_lines=added,
        removed_lines=removed,
        headings=_extract_headings(new_text),
        variables=_extract_template_variables(new_text),
        lines=diff_lines,
    )


def _text_diff_inline_summary(text_diff: TextDiff) -> str:
    parts = [f"+{text_diff.added_lines} -{text_diff.removed_lines}"]
    if text_diff.headings:
        parts.append("headings: " + ", ".join(text_diff.headings[:3]))
    if text_diff.variables:
        parts.append("vars: " + ", ".join(text_diff.variables[:5]))
    return "; ".join(parts)


def _extract_headings(text: str) -> list[str]:
    headings: list[str] = []
    for line in text.splitlines():
        match = re.match(r"^\s{0,3}#{1,6}\s+(.+?)\s*$", line)
        if match:
            headings.append(match.group(1).strip().rstrip("#").strip())
    return _dedupe(headings)


def _extract_template_variables(text: str) -> list[str]:
    return _dedupe(match.group(1) for match in re.finditer(r"\{([A-Za-z_][A-Za-z0-9_.-]*)\}", text))


def _dedupe(values) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result


def _diff_schema_group(result: PackageDiff, old_paths: dict[str, Path], new_paths: dict[str, Path]) -> None:
    _diff_path_group(result, "schema", old_paths, new_paths, compare_text=False)

    for name in sorted(set(old_paths) & set(new_paths)):
        old_path = old_paths[name]
        new_path = new_paths[name]
        if not old_path.exists() or not new_path.exists():
            continue

        old_schema = load_json(old_path)
        new_schema = load_json(new_path)
        if old_schema == new_schema:
            continue

        result.add(f"SCHEMA changed {name}: {old_path.name} -> {new_path.name}", changed=True)
        _diff_schema_node(result, name, old_schema, new_schema, path="", old_root=old_schema, new_root=new_schema)


def _diff_schema_node(
    result: PackageDiff,
    name: str,
    old_schema: Any,
    new_schema: Any,
    *,
    path: str,
    old_root: Any,
    new_root: Any,
) -> None:
    if not isinstance(old_schema, dict) or not isinstance(new_schema, dict):
        return

    old_schema, new_schema = _diff_and_resolve_refs(result, name, old_schema, new_schema, path=path, old_root=old_root, new_root=new_root)
    if not isinstance(old_schema, dict) or not isinstance(new_schema, dict):
        return

    _diff_schema_type(result, name, old_schema, new_schema, path=path)
    _diff_schema_enum(result, name, old_schema, new_schema, path=path)
    _diff_schema_additional_properties(result, name, old_schema, new_schema, path=path)
    _diff_schema_bounds(result, name, old_schema, new_schema, path=path)
    _diff_schema_combinators(result, name, old_schema, new_schema, path=path, old_root=old_root, new_root=new_root)
    _diff_schema_items(result, name, old_schema, new_schema, path=path, old_root=old_root, new_root=new_root)
    _diff_schema_properties(result, name, old_schema, new_schema, path=path, old_root=old_root, new_root=new_root)


def _diff_schema_properties(
    result: PackageDiff,
    name: str,
    old_schema: dict[str, Any],
    new_schema: dict[str, Any],
    *,
    path: str,
    old_root: Any,
    new_root: Any,
) -> None:
    old_properties = _schema_properties(old_schema)
    new_properties = _schema_properties(new_schema)
    old_required = _schema_required(old_schema)
    new_required = _schema_required(new_schema)

    old_property_names = set(old_properties)
    new_property_names = set(new_properties)

    for field in sorted(new_property_names - old_property_names):
        marker = "required" if field in new_required else "optional"
        field_path = _join_schema_path(path, field)
        result.add(f"SCHEMA {name} property added {field_path} ({marker})", changed=True, breaking=field in new_required)
    for field in sorted(old_property_names - new_property_names):
        field_path = _join_schema_path(path, field)
        result.add(f"SCHEMA {name} property removed {field_path}", breaking=True)

    for field in sorted(old_property_names & new_property_names):
        field_path = _join_schema_path(path, field)
        _diff_schema_node(result, name, old_properties[field], new_properties[field], path=field_path, old_root=old_root, new_root=new_root)

    for field in sorted(new_required - old_required):
        if field in old_properties:
            field_path = _join_schema_path(path, field)
            result.add(f"SCHEMA {name} property became required {field_path}", breaking=True)
    for field in sorted(old_required - new_required):
        if field in new_properties:
            field_path = _join_schema_path(path, field)
            result.add(f"SCHEMA {name} property became optional {field_path}", changed=True)


def _diff_schema_type(result: PackageDiff, name: str, old_schema: dict[str, Any], new_schema: dict[str, Any], *, path: str) -> None:
    old_type = _schema_type(old_schema)
    new_type = _schema_type(new_schema)
    if old_type == new_type:
        return

    label = _schema_label(path)
    if path:
        result.add(f"SCHEMA {name} property type changed {label}: {old_type} -> {new_type}", breaking=True)
    else:
        result.add(f"SCHEMA {name} root type changed: {old_type} -> {new_type}", breaking=True)


def _diff_schema_enum(result: PackageDiff, name: str, old_schema: dict[str, Any], new_schema: dict[str, Any], *, path: str) -> None:
    old_enum = _schema_enum(old_schema)
    new_enum = _schema_enum(new_schema)
    if old_enum is None and new_enum is None:
        return

    label = _schema_label(path)
    if old_enum is None:
        result.add(f"SCHEMA {name} enum added {label}: {_short_sorted(new_enum or set())}", breaking=True)
        return
    if new_enum is None:
        result.add(f"SCHEMA {name} enum removed {label}", changed=True)
        return

    removed = old_enum - new_enum
    added = new_enum - old_enum
    if removed:
        result.add(f"SCHEMA {name} enum removed values {label}: {_short_sorted(removed)}", breaking=True)
    if added:
        result.add(f"SCHEMA {name} enum added values {label}: {_short_sorted(added)}", changed=True)


def _diff_schema_additional_properties(
    result: PackageDiff,
    name: str,
    old_schema: dict[str, Any],
    new_schema: dict[str, Any],
    *,
    path: str,
) -> None:
    old_value = old_schema.get("additionalProperties", True)
    new_value = new_schema.get("additionalProperties", True)
    if old_value == new_value:
        return

    label = _schema_label(path)
    if old_value is not False and new_value is False:
        result.add(f"SCHEMA {name} additionalProperties restricted {label}: {_short(old_value)} -> False", breaking=True)
    elif old_value is False and new_value is not False:
        result.add(f"SCHEMA {name} additionalProperties relaxed {label}: False -> {_short(new_value)}", changed=True)
    else:
        result.add(
            f"SCHEMA {name} additionalProperties changed {label}: {_short(old_value)} -> {_short(new_value)}",
            changed=True,
            breaking=isinstance(old_value, dict) or new_value is False,
        )


def _diff_schema_bounds(result: PackageDiff, name: str, old_schema: dict[str, Any], new_schema: dict[str, Any], *, path: str) -> None:
    for key in ("minLength", "minItems", "minimum", "exclusiveMinimum", "minProperties"):
        _diff_lower_bound(result, name, old_schema, new_schema, key, path=path)
    for key in ("maxLength", "maxItems", "maximum", "exclusiveMaximum", "maxProperties"):
        _diff_upper_bound(result, name, old_schema, new_schema, key, path=path)


def _diff_lower_bound(
    result: PackageDiff,
    name: str,
    old_schema: dict[str, Any],
    new_schema: dict[str, Any],
    key: str,
    *,
    path: str,
) -> None:
    old_value = old_schema.get(key)
    new_value = new_schema.get(key)
    if old_value == new_value:
        return

    label = _schema_label(path)
    breaking = _is_number(old_value) and _is_number(new_value) and new_value > old_value
    if old_value is None and new_value is not None:
        breaking = True
    result.add(f"SCHEMA {name} constraint changed {label}.{key}: {_short(old_value)} -> {_short(new_value)}", changed=True, breaking=breaking)


def _diff_upper_bound(
    result: PackageDiff,
    name: str,
    old_schema: dict[str, Any],
    new_schema: dict[str, Any],
    key: str,
    *,
    path: str,
) -> None:
    old_value = old_schema.get(key)
    new_value = new_schema.get(key)
    if old_value == new_value:
        return

    label = _schema_label(path)
    breaking = _is_number(old_value) and _is_number(new_value) and new_value < old_value
    if old_value is None and new_value is not None:
        breaking = True
    result.add(f"SCHEMA {name} constraint changed {label}.{key}: {_short(old_value)} -> {_short(new_value)}", changed=True, breaking=breaking)


def _diff_schema_combinators(
    result: PackageDiff,
    name: str,
    old_schema: dict[str, Any],
    new_schema: dict[str, Any],
    *,
    path: str,
    old_root: Any,
    new_root: Any,
) -> None:
    for key in ("oneOf", "anyOf", "allOf"):
        _diff_schema_combinator(result, name, old_schema, new_schema, key, path=path, old_root=old_root, new_root=new_root)


def _diff_schema_combinator(
    result: PackageDiff,
    name: str,
    old_schema: dict[str, Any],
    new_schema: dict[str, Any],
    key: str,
    *,
    path: str,
    old_root: Any,
    new_root: Any,
) -> None:
    old_branches = old_schema.get(key)
    new_branches = new_schema.get(key)
    if old_branches is None and new_branches is None:
        return

    label = _schema_label(path)
    old_valid = isinstance(old_branches, list)
    new_valid = isinstance(new_branches, list)
    if old_branches is None:
        result.add(
            f"SCHEMA {name} {key} added {label} ({len(new_branches) if new_valid else 'invalid'} branches)",
            changed=True,
            breaking=key in {"allOf", "anyOf"},
        )
        return
    if new_branches is None:
        result.add(f"SCHEMA {name} {key} removed {label}", changed=True, breaking=key == "oneOf")
        return
    if not old_valid or not new_valid:
        result.add(f"SCHEMA {name} {key} changed {label}: {_short(old_branches)} -> {_short(new_branches)}", changed=True, breaking=True)
        return

    old_canonical = [_canonical_schema(branch) for branch in old_branches]
    new_canonical = [_canonical_schema(branch) for branch in new_branches]
    if old_canonical == new_canonical:
        return
    if len(old_canonical) == len(new_canonical) and sorted(old_canonical) == sorted(new_canonical):
        result.add(f"SCHEMA {name} {key} branches reordered {label}", changed=True)
        return

    for index in range(min(len(old_branches), len(new_branches))):
        old_branch = old_branches[index]
        new_branch = new_branches[index]
        branch_path = _join_schema_path(path, f"{key}[{index}]")
        if _canonical_schema(old_branch) != _canonical_schema(new_branch):
            result.add(f"SCHEMA {name} {key} branch changed {_schema_label(branch_path)}", changed=True)
            _diff_schema_node(result, name, old_branch, new_branch, path=branch_path, old_root=old_root, new_root=new_root)

    for index in range(len(new_branches) - 1, len(old_branches) - 1, -1):
        branch_path = _join_schema_path(path, f"{key}[{index}]")
        result.add(f"SCHEMA {name} {key} branch added {_schema_label(branch_path)}", changed=True, breaking=key == "allOf")
    for index in range(len(old_branches) - 1, len(new_branches) - 1, -1):
        branch_path = _join_schema_path(path, f"{key}[{index}]")
        result.add(f"SCHEMA {name} {key} branch removed {_schema_label(branch_path)}", changed=True, breaking=key in {"oneOf", "anyOf"})


def _diff_schema_items(
    result: PackageDiff,
    name: str,
    old_schema: dict[str, Any],
    new_schema: dict[str, Any],
    *,
    path: str,
    old_root: Any,
    new_root: Any,
) -> None:
    if "items" not in old_schema and "items" not in new_schema:
        return
    if "items" not in old_schema:
        result.add(f"SCHEMA {name} items added {_schema_label(path)}", breaking=True)
        return
    if "items" not in new_schema:
        result.add(f"SCHEMA {name} items removed {_schema_label(path)}", changed=True)
        return

    old_items = old_schema["items"]
    new_items = new_schema["items"]
    if old_items == new_items:
        return
    if isinstance(old_items, dict) and isinstance(new_items, dict):
        _diff_schema_node(result, name, old_items, new_items, path=_join_schema_path(path, "[]"), old_root=old_root, new_root=new_root)
    else:
        result.add(f"SCHEMA {name} items changed {_schema_label(path)}: {_short(old_items)} -> {_short(new_items)}", breaking=True)


def _diff_golden_cases(result: PackageDiff, old: SkillPackage, new: SkillPackage) -> None:
    old_tests = old.test_paths()
    new_tests = new.test_paths()
    if "golden" not in old_tests or "golden" not in new_tests:
        return
    old_path = old_tests["golden"]
    new_path = new_tests["golden"]
    if not old_path.exists() or not new_path.exists():
        return

    old_cases = _case_map(load_jsonl(old_path))
    new_cases = _case_map(load_jsonl(new_path))

    old_case_ids = set(old_cases)
    new_case_ids = set(new_cases)

    for case_id in sorted(new_case_ids - old_case_ids):
        result.add(f"GOLDEN case added {case_id}", changed=True)
    for case_id in sorted(old_case_ids - new_case_ids):
        result.add(f"GOLDEN case removed {case_id}", changed=True)
    for case_id in sorted(old_case_ids & new_case_ids):
        if old_cases[case_id].get("expected") != new_cases[case_id].get("expected"):
            result.add(f"GOLDEN expected changed {case_id}", changed=True)


def _case_map(records: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    cases: dict[str, dict[str, Any]] = {}
    for index, record in enumerate(records, start=1):
        case_id = record.get("case_id", f"line-{index}")
        if not isinstance(case_id, str):
            raise SitError(f"golden case_id at line {index} must be a string")
        cases[case_id] = record
    return cases


def _schema_properties(schema: dict[str, Any]) -> dict[str, Any]:
    properties = schema.get("properties", {})
    return properties if isinstance(properties, dict) else {}


def _schema_required(schema: dict[str, Any]) -> set[str]:
    required = schema.get("required", [])
    return {item for item in required if isinstance(item, str)} if isinstance(required, list) else set()


def _schema_enum(schema: dict[str, Any]) -> set[str] | None:
    values = schema.get("enum")
    if not isinstance(values, list):
        return None
    return {repr(value) for value in values}


def _schema_type(schema: Any) -> str:
    if not isinstance(schema, dict):
        return "<unknown>"
    schema_type = schema.get("type")
    if isinstance(schema_type, list):
        return "|".join(str(item) for item in schema_type)
    if schema_type is None:
        return "<unspecified>"
    return str(schema_type)


def _diff_and_resolve_refs(
    result: PackageDiff,
    name: str,
    old_schema: dict[str, Any],
    new_schema: dict[str, Any],
    *,
    path: str,
    old_root: Any,
    new_root: Any,
) -> tuple[Any, Any]:
    old_ref = _schema_ref(old_schema)
    new_ref = _schema_ref(new_schema)
    label = _schema_label(path)

    if old_ref != new_ref:
        if old_ref is None:
            result.add(f"SCHEMA {name} $ref added {label}: {new_ref}", changed=True)
        elif new_ref is None:
            result.add(f"SCHEMA {name} $ref removed {label}: {old_ref}", changed=True)
        else:
            result.add(f"SCHEMA {name} $ref target changed {label}: {old_ref} -> {new_ref}", changed=True)

    old_resolved = _resolve_schema_ref(old_schema, old_root)
    new_resolved = _resolve_schema_ref(new_schema, new_root)
    if old_resolved.unresolved:
        result.add(f"SCHEMA {name} unresolved $ref {label}: {old_resolved.ref}", changed=True, breaking=True)
    if new_resolved.unresolved:
        result.add(f"SCHEMA {name} unresolved $ref {label}: {new_resolved.ref}", changed=True, breaking=True)
    return old_resolved.schema, new_resolved.schema


@dataclass(frozen=True)
class _ResolvedSchema:
    schema: Any
    ref: str | None = None
    unresolved: bool = False


def _schema_ref(schema: Any) -> str | None:
    if not isinstance(schema, dict):
        return None
    ref = schema.get("$ref")
    return ref if isinstance(ref, str) else None


def _resolve_schema_ref(schema: Any, root: Any) -> _ResolvedSchema:
    current = schema
    last_ref: str | None = None
    seen: set[str] = set()
    while isinstance(current, dict):
        ref = _schema_ref(current)
        if ref is None:
            return _ResolvedSchema(current, ref=last_ref)
        last_ref = ref
        if ref in seen:
            return _ResolvedSchema(current, ref=ref, unresolved=True)
        seen.add(ref)
        target = _resolve_json_pointer(root, ref)
        if target is None:
            return _ResolvedSchema(current, ref=ref, unresolved=True)
        current = target
    return _ResolvedSchema(current, ref=last_ref)


def _resolve_json_pointer(root: Any, ref: str) -> Any:
    if ref == "#":
        return root
    if not ref.startswith("#/"):
        return None

    current = root
    for raw_part in ref[2:].split("/"):
        part = raw_part.replace("~1", "/").replace("~0", "~")
        if isinstance(current, dict):
            if part not in current:
                return None
            current = current[part]
        elif isinstance(current, list):
            try:
                index = int(part)
            except ValueError:
                return None
            if index < 0 or index >= len(current):
                return None
            current = current[index]
        else:
            return None
    return current


def _canonical_schema(schema: Any) -> str:
    try:
        return _json_dumps_stable(schema)
    except TypeError:
        return repr(schema)


def _json_dumps_stable(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _join_schema_path(base: str, part: str) -> str:
    if not base:
        return part
    if part == "[]":
        return f"{base}[]"
    return f"{base}.{part}"


def _schema_label(path: str) -> str:
    return path or "<root>"


def _short_sorted(values: set[str]) -> str:
    text = ", ".join(sorted(values))
    return text if len(text) <= 80 else text[:77] + "..."


def _is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _short(value: Any) -> str:
    text = repr(value)
    return text if len(text) <= 80 else text[:77] + "..."


def _infer_category(message: str) -> str:
    head = message.split(maxsplit=1)[0].lower() if message else "unknown"
    return "".join(char for char in head if char.isalnum() or char in {"_", "-"}) or "unknown"


def _package_ref(package: SkillPackage, *, source: str | None = None) -> dict[str, str]:
    data = {
        "name": package.name or "<unknown>",
        "version": package.version or "<unknown>",
        "root": str(package.root),
        "manifest": str(package.manifest_path),
    }
    if source is not None:
        data["source"] = source
    return data
