from __future__ import annotations

from dataclasses import dataclass, field
import json
from pathlib import Path
import shlex
import subprocess
import tempfile
from typing import Any

from jsonschema import Draft202012Validator, SchemaError, ValidationError

from .errors import SitError
from .package import SkillPackage, load_json, load_jsonl

MATCH_MODES = {"schema_only", "exact", "partial", "contains"}


@dataclass
class CheckResult:
    ok: bool = True
    messages: list[str] = field(default_factory=list)

    def add_ok(self, message: str) -> None:
        self.messages.append(f"OK  {message}")

    def add_fail(self, message: str) -> None:
        self.ok = False
        self.messages.append(f"ERR {message}")

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": "pass" if self.ok else "fail",
            "ok": self.ok,
            "messages": self.messages,
        }


def validate_package(package: SkillPackage) -> CheckResult:
    result = CheckResult()

    if package.name:
        result.add_ok(f"name: {package.name}")
    else:
        result.add_fail("skill.yaml missing string field: name")

    if package.version:
        result.add_ok(f"version: {package.version}")
    else:
        result.add_fail("skill.yaml missing field: version")

    _check_path(result, package.manifest_path, "manifest")

    for label, paths in (
        ("prompt", package.prompt_paths()),
        ("schema", package.schema_paths()),
        ("test", package.test_paths()),
    ):
        if not paths:
            result.add_fail(f"skill.yaml has no {label} paths")
        for name, path in paths.items():
            _check_path(result, path, f"{label}.{name}")

    for name, path in package.schema_paths().items():
        if path.exists():
            try:
                schema = load_json(path)
                Draft202012Validator.check_schema(schema)
            except (SitError, SchemaError) as exc:
                result.add_fail(f"schema.{name} invalid: {exc}")
            else:
                result.add_ok(f"schema.{name} JSON schema valid")

    for name, path in package.test_paths().items():
        if path.exists() and path.suffix == ".jsonl":
            try:
                records = load_jsonl(path)
            except SitError as exc:
                result.add_fail(str(exc))
            else:
                _check_match_modes(result, records, name)
                result.add_ok(f"test.{name} JSONL parsed: {len(records)} cases")

    _check_commands(result, package)
    return result


def _check_match_modes(result: CheckResult, records: list[dict[str, Any]], test_name: str) -> None:
    for index, record in enumerate(records, start=1):
        match_mode = record.get("match_mode", "schema_only")
        if not isinstance(match_mode, str) or match_mode not in MATCH_MODES:
            result.add_fail(f"test.{test_name} line {index} unsupported match_mode: {match_mode!r}")


def _check_commands(result: CheckResult, package: SkillPackage) -> None:
    commands = package.manifest.get("commands")
    if commands is None:
        return
    if not isinstance(commands, dict):
        result.add_fail("skill.yaml field 'commands' must be a mapping")
        return
    for name, command in commands.items():
        if isinstance(command, str) and command.strip():
            result.add_ok(f"command.{name}: configured")
        else:
            result.add_fail(f"skill.yaml field 'commands.{name}' must be a non-empty string")


def run_golden_schema_tests(
    package: SkillPackage,
    *,
    run_actual: bool = False,
    runner: str | None = None,
    timeout: int = 30,
) -> CheckResult:
    result = CheckResult()
    schema_path = _select_output_schema(package)
    golden_path = _select_golden_file(package)
    runner_command = _resolve_runner(package, runner) if run_actual else None

    schema = load_json(schema_path)
    validator = Draft202012Validator(schema)
    records = load_jsonl(golden_path)

    passed = 0
    for index, record in enumerate(records, start=1):
        case_id = record.get("case_id", f"line-{index}")
        match_mode = record.get("match_mode", "schema_only")
        if match_mode not in MATCH_MODES:
            result.add_fail(f"{case_id}: unsupported match_mode {match_mode!r}")
            continue
        if "expected" not in record:
            result.add_fail(f"{case_id}: missing expected object")
            continue
        actual = record.get("actual")
        if runner_command is not None:
            actual, error = _run_case(package, runner_command, record, case_id, timeout)
            if error is not None:
                result.add_fail(f"{case_id}: {error}")
                continue
            result.add_ok(f"{case_id}: runner produced actual")

        if match_mode != "schema_only" and actual is None:
            result.add_fail(f"{case_id}: match_mode {match_mode} requires actual")
            continue

        candidate = actual if actual is not None else record["expected"]
        schema_ok = _validate_candidate(result, validator, case_id, candidate, "actual" if actual is not None else "expected")
        if not schema_ok:
            continue

        match_error = _match_record(record["expected"], actual, match_mode)
        if match_error:
            result.add_fail(f"{case_id}: {match_error}")
        else:
            passed += 1
            result.add_ok(f"{case_id}: {match_mode} match passed")

    result.messages.append(f"SUMMARY {passed}/{len(records)} golden cases passed")
    return result


def build_test_payload(
    package: SkillPackage,
    *,
    run_actual: bool = False,
    runner: str | None = None,
    timeout: int = 30,
) -> dict[str, Any]:
    validation = validate_package(package)
    tests = run_golden_schema_tests(package, run_actual=run_actual, runner=runner, timeout=timeout) if validation.ok else None
    runner_command = None
    if run_actual:
        runner_command = runner or _manifest_runner(package)
    return {
        "schema_version": "sit.test.v1",
        "package": _package_ref(package),
        "execution": {
            "mode": "runner" if run_actual else "static",
            "runner": runner_command,
            "timeout_seconds": timeout if run_actual else None,
        },
        "validation": validation.to_dict(),
        "golden_tests": _test_result_dict(tests),
    }


def _test_result_dict(result: CheckResult | None) -> dict[str, Any]:
    if result is None:
        return {
            "status": "skipped",
            "ok": None,
            "passed": None,
            "total": None,
            "summary": None,
            "messages": [],
        }
    passed, total, summary = _parse_summary(result.messages)
    return {
        "status": "pass" if result.ok else "fail",
        "ok": result.ok,
        "passed": passed,
        "total": total,
        "summary": summary,
        "messages": result.messages,
    }


def _parse_summary(messages: list[str]) -> tuple[int | None, int | None, str | None]:
    prefix = "SUMMARY "
    suffix = " golden cases passed"
    for message in reversed(messages):
        if not message.startswith(prefix) or not message.endswith(suffix):
            continue
        counts = message[len(prefix) : -len(suffix)]
        left, separator, right = counts.partition("/")
        if not separator:
            continue
        try:
            return int(left), int(right), message
        except ValueError:
            continue
    return None, None, None


def _package_ref(package: SkillPackage) -> dict[str, str]:
    return {
        "name": package.name or "<unknown>",
        "version": package.version or "<unknown>",
        "root": str(package.root),
        "manifest": str(package.manifest_path),
    }


def _resolve_runner(package: SkillPackage, runner: str | None) -> str:
    command = runner or _manifest_runner(package)
    if not command:
        raise SitError("No test runner configured; define commands.run_case in skill.yaml or pass --runner")
    return command


def _manifest_runner(package: SkillPackage) -> str | None:
    commands = package.manifest.get("commands", {})
    if not isinstance(commands, dict):
        return None
    command = commands.get("run_case")
    return command if isinstance(command, str) and command.strip() else None


def _run_case(
    package: SkillPackage,
    runner_command: str,
    record: dict[str, Any],
    case_id: Any,
    timeout: int,
) -> tuple[Any | None, str | None]:
    with tempfile.TemporaryDirectory(prefix="sit-case-") as tmp:
        tmp_path = Path(tmp)
        input_path = tmp_path / "input.json"
        output_path = tmp_path / "output.json"
        input_path.write_text(json.dumps(record.get("input", {}), ensure_ascii=False), encoding="utf-8")

        try:
            command = [
                part.format(
                    input=str(input_path),
                    output=str(output_path),
                    case_id=str(case_id),
                    root=str(package.root),
                )
                for part in shlex.split(runner_command)
            ]
        except KeyError as exc:
            return None, f"runner command has unsupported placeholder: {exc}"
        except ValueError as exc:
            return None, f"runner command is not a valid argv template: {exc}"

        try:
            completed = subprocess.run(
                command,
                cwd=package.root,
                check=False,
                text=True,
                capture_output=True,
                timeout=timeout,
            )
        except subprocess.TimeoutExpired:
            return None, f"runner timed out after {timeout}s"

        if completed.returncode != 0:
            detail = completed.stderr.strip() or completed.stdout.strip()
            return None, "runner failed" + (f": {_clip(detail)}" if detail else "")

        if output_path.exists() and output_path.read_text(encoding="utf-8").strip():
            text = output_path.read_text(encoding="utf-8")
            source = str(output_path)
        else:
            text = completed.stdout
            source = "stdout"

        if not text.strip():
            return None, "runner produced no JSON output"

        try:
            return json.loads(text), None
        except json.JSONDecodeError as exc:
            return None, f"runner produced invalid JSON from {source}: line {exc.lineno}, column {exc.colno}: {exc.msg}"


def _clip(text: str, limit: int = 300) -> str:
    clean = " ".join(text.split())
    if len(clean) <= limit:
        return clean
    return clean[: limit - 3] + "..."


def _validate_candidate(
    result: CheckResult,
    validator: Draft202012Validator,
    case_id: Any,
    candidate: Any,
    label: str,
) -> bool:
    try:
        validator.validate(candidate)
    except ValidationError as exc:
        location = ".".join(str(part) for part in exc.absolute_path) or "<root>"
        result.add_fail(f"{case_id}: {label} failed schema validation at {location}: {exc.message}")
        return False
    return True


def _match_record(expected: Any, actual: Any, match_mode: str) -> str | None:
    if match_mode == "schema_only":
        return None
    if match_mode == "exact":
        return None if actual == expected else "exact mismatch"
    if match_mode == "partial":
        path = _first_partial_mismatch(expected, actual)
        return None if path is None else f"partial mismatch at {path}"
    if match_mode == "contains":
        path = _first_contains_mismatch(expected, actual)
        return None if path is None else f"contains mismatch at {path}"
    return f"unsupported match_mode {match_mode!r}"


def _first_partial_mismatch(expected: Any, actual: Any, path: str = "<root>") -> str | None:
    if isinstance(expected, dict):
        if not isinstance(actual, dict):
            return path
        for key, expected_value in expected.items():
            if key not in actual:
                return _join_path(path, str(key))
            mismatch = _first_partial_mismatch(expected_value, actual[key], _join_path(path, str(key)))
            if mismatch is not None:
                return mismatch
        return None

    if isinstance(expected, list):
        if not isinstance(actual, list) or len(actual) < len(expected):
            return path
        for index, expected_value in enumerate(expected):
            mismatch = _first_partial_mismatch(expected_value, actual[index], f"{path}[{index}]")
            if mismatch is not None:
                return mismatch
        return None

    return None if actual == expected else path


def _first_contains_mismatch(expected: Any, actual: Any, path: str = "<root>") -> str | None:
    if isinstance(expected, dict):
        if not isinstance(actual, dict):
            return path
        for key, expected_value in expected.items():
            if key not in actual:
                return _join_path(path, str(key))
            mismatch = _first_contains_mismatch(expected_value, actual[key], _join_path(path, str(key)))
            if mismatch is not None:
                return mismatch
        return None

    if isinstance(expected, list):
        if not isinstance(actual, list):
            return path
        for index, expected_value in enumerate(expected):
            if not any(_first_contains_mismatch(expected_value, actual_item, f"{path}[{index}]") is None for actual_item in actual):
                return f"{path}[{index}]"
        return None

    if isinstance(expected, str):
        return None if isinstance(actual, str) and expected in actual else path
    return None if actual == expected else path


def _join_path(base: str, part: str) -> str:
    return part if base == "<root>" else f"{base}.{part}"


def _select_output_schema(package: SkillPackage) -> Path:
    schemas = package.schema_paths()
    if "output" in schemas:
        return schemas["output"]
    if len(schemas) == 1:
        return next(iter(schemas.values()))
    raise SitError("Cannot select output schema; define schemas.output in skill.yaml")


def _select_golden_file(package: SkillPackage) -> Path:
    tests = package.test_paths()
    if "golden" in tests:
        return tests["golden"]
    jsonl_tests = [path for path in tests.values() if path.suffix == ".jsonl"]
    if len(jsonl_tests) == 1:
        return jsonl_tests[0]
    raise SitError("Cannot select golden file; define tests.golden in skill.yaml")


def _check_path(result: CheckResult, path: Path, label: str) -> None:
    if path.exists():
        result.add_ok(f"{label} exists: {path}")
    else:
        result.add_fail(f"{label} missing: {path}")
