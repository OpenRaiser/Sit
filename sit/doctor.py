from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import subprocess
from typing import Any

from .errors import SitError
from .git import git_root
from .package import SkillPackage, load_package
from .validate import run_golden_schema_tests, validate_package


@dataclass
class DoctorCheck:
    name: str
    status: str
    message: str
    details: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return self.status in {"pass", "warn"}

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "status": self.status,
            "message": self.message,
            "details": self.details,
        }


def build_doctor_payload(package_spec: str | Path = ".") -> dict[str, Any]:
    checks: list[DoctorCheck] = []
    package: SkillPackage | None = None
    package_error: str | None = None

    try:
        package = load_package(package_spec)
    except SitError as exc:
        package_error = str(exc)

    checks.append(_check_git(Path(package_spec).expanduser()))
    checks.append(_check_github_remote(Path(package_spec).expanduser()))
    checks.append(_check_manifest(package, package_error))

    if package is not None:
        checks.append(_check_validation(package))
        checks.append(_check_golden_tests(package))
        checks.append(_check_workflow(package))
        checks.append(_check_reports(package))

    status = "pass" if all(check.status == "pass" for check in checks) else ("fail" if any(check.status == "fail" for check in checks) else "warn")
    return {
        "schema_version": "sit.doctor.v1",
        "status": status,
        "ok": status != "fail",
        "package": _package_ref(package) if package is not None else None,
        "checks": [check.to_dict() for check in checks],
    }


def render_doctor_text(payload: dict[str, Any]) -> str:
    lines = ["SitHub Doctor", "", f"Status: {payload['status']}"]
    package = payload.get("package")
    if package is not None:
        lines.extend(["", f"Package: {package['name']}@{package['version']}", f"Root: {package['root']}"])

    lines.append("")
    for check in payload["checks"]:
        marker = {"pass": "OK", "warn": "WARN", "fail": "ERR"}.get(check["status"], "INFO")
        lines.append(f"{marker} {check['name']}: {check['message']}")
        lines.extend(f"  - {detail}" for detail in check.get("details", []))
    return "\n".join(lines) + "\n"


def _check_git(package_path: Path) -> DoctorCheck:
    root = git_root(_existing_path(package_path))
    if root is None:
        return DoctorCheck("git", "fail", "not inside a Git repository")

    branch = _git_output(root, ["branch", "--show-current"]) or "<detached>"
    commit = _git_output(root, ["rev-parse", "--short", "HEAD"]) or "<none>"
    dirty = bool(_git_output(root, ["status", "--short"]))
    details = [f"repo: {root}", f"branch: {branch}", f"commit: {commit}", f"dirty: {'yes' if dirty else 'no'}"]
    if dirty:
        return DoctorCheck("git", "warn", "Git repository detected with uncommitted changes", details)
    return DoctorCheck("git", "pass", "Git repository detected", details)


def _check_github_remote(package_path: Path) -> DoctorCheck:
    root = git_root(_existing_path(package_path))
    if root is None:
        return DoctorCheck("github_remote", "fail", "GitHub remote unavailable because this is not a Git repository")

    remotes = _git_output(root, ["remote", "-v"])
    github_lines = [line for line in remotes.splitlines() if "github.com" in line]
    if not github_lines:
        return DoctorCheck("github_remote", "warn", "no GitHub remote found")
    return DoctorCheck("github_remote", "pass", "GitHub remote found", github_lines)


def _check_manifest(package: SkillPackage | None, error: str | None) -> DoctorCheck:
    if package is None:
        return DoctorCheck("manifest", "fail", error or "missing skill.yaml")
    details = [f"manifest: {package.manifest_path}", f"prompts: {len(package.prompt_paths())}", f"schemas: {len(package.schema_paths())}", f"tests: {len(package.test_paths())}"]
    return DoctorCheck("manifest", "pass", "skill.yaml loaded", details)


def _check_validation(package: SkillPackage) -> DoctorCheck:
    result = validate_package(package)
    return DoctorCheck("validate", "pass" if result.ok else "fail", "validation passed" if result.ok else "validation failed", result.messages)


def _check_golden_tests(package: SkillPackage) -> DoctorCheck:
    try:
        result = run_golden_schema_tests(package)
    except SitError as exc:
        return DoctorCheck("golden_tests", "fail", str(exc))
    return DoctorCheck("golden_tests", "pass" if result.ok else "fail", "golden tests passed" if result.ok else "golden tests failed", result.messages)


def _check_workflow(package: SkillPackage) -> DoctorCheck:
    workflow = package.root / ".github" / "workflows" / "sit-ci.yaml"
    if not workflow.exists():
        return DoctorCheck("github_actions", "warn", "missing .github/workflows/sit-ci.yaml")
    text = workflow.read_text(encoding="utf-8", errors="ignore")
    details = [str(workflow)]
    missing = [snippet for snippet in ("sit validate", "sit test", "sit ci-summary") if snippet not in text]
    if missing:
        details.append("missing commands: " + ", ".join(missing))
        return DoctorCheck("github_actions", "warn", "workflow exists but may not run the full SitHub loop", details)
    return DoctorCheck("github_actions", "pass", "SitHub GitHub Actions workflow found", details)


def _check_reports(package: SkillPackage) -> DoctorCheck:
    report_dir = package.report_dir()
    if not report_dir.exists():
        return DoctorCheck("reports", "warn", "reports directory does not exist")
    reports = sorted(path.relative_to(package.root).as_posix() for path in report_dir.rglob("*") if path.is_file())
    if not reports:
        return DoctorCheck("reports", "warn", "reports directory exists but has no files", [str(report_dir)])
    return DoctorCheck("reports", "pass", f"{len(reports)} report files found", reports[:10])


def _existing_path(path: Path) -> Path:
    path = path.resolve()
    if path.exists():
        return path if path.is_dir() else path.parent
    for parent in path.parents:
        if parent.exists():
            return parent
    return Path.cwd()


def _git_output(cwd: Path, args: list[str]) -> str:
    try:
        completed = subprocess.run(["git", *args], cwd=cwd, check=False, text=True, capture_output=True)
    except FileNotFoundError:
        return ""
    if completed.returncode != 0:
        return ""
    return completed.stdout.strip()


def _package_ref(package: SkillPackage) -> dict[str, str]:
    return {
        "name": package.name or "<unknown>",
        "version": package.version or "<unknown>",
        "root": str(package.root),
        "manifest": str(package.manifest_path),
    }
