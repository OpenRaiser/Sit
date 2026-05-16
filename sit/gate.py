from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
import io
from pathlib import Path
import subprocess
import tarfile
import tempfile
from typing import Iterator

from .diff import PackageDiff, diff_packages
from .errors import SitError
from .git import git_output, git_root
from .package import SkillPackage, load_package

BUMP_ORDER = {"none": 0, "patch": 1, "minor": 2, "major": 3}


@dataclass(frozen=True)
class VersionGateResult:
    checked: bool
    ok: bool
    required_bump: str
    actual_bump: str
    baseline_version: str | None
    current_version: str | None
    diff: PackageDiff | None
    message: str

    def summary_lines(self) -> list[str]:
        return self.message.splitlines()


def check_version_gate_against_head(package: SkillPackage) -> VersionGateResult:
    with load_head_package(package) as baseline:
        if baseline is None:
            return VersionGateResult(
                checked=False,
                ok=True,
                required_bump="none",
                actual_bump="none",
                baseline_version=None,
                current_version=package.version,
                diff=None,
                message="version gate skipped: no Git HEAD baseline",
            )
        return check_version_gate(baseline, package)


def check_release_gate_against_head(package: SkillPackage, requested_bump: str) -> VersionGateResult:
    with load_head_package(package) as baseline:
        if baseline is None:
            return VersionGateResult(
                checked=False,
                ok=True,
                required_bump="none",
                actual_bump=requested_bump,
                baseline_version=None,
                current_version=package.version,
                diff=None,
                message="release gate skipped: no Git HEAD baseline",
            )

        diff = diff_packages(baseline, package)
        required_bump = required_bump_for_gate(diff)
        ok = _bump_rank(requested_bump) >= _bump_rank(required_bump)
        message = _gate_message(
            "release",
            ok=ok,
            required_bump=required_bump,
            actual_bump=requested_bump,
            baseline_version=baseline.version,
            current_version=package.version,
            risk=diff.risk,
        )
        return VersionGateResult(
            checked=True,
            ok=ok,
            required_bump=required_bump,
            actual_bump=requested_bump,
            baseline_version=baseline.version,
            current_version=package.version,
            diff=diff,
            message=message,
        )


def check_version_gate(baseline: SkillPackage, current: SkillPackage) -> VersionGateResult:
    diff = diff_packages(baseline, current)
    required_bump = required_bump_for_gate(diff)
    actual_bump = version_bump_between(baseline.version, current.version)
    ok = _bump_rank(actual_bump) >= _bump_rank(required_bump)
    message = _gate_message(
        "commit",
        ok=ok,
        required_bump=required_bump,
        actual_bump=actual_bump,
        baseline_version=baseline.version,
        current_version=current.version,
        risk=diff.risk,
    )
    return VersionGateResult(
        checked=True,
        ok=ok,
        required_bump=required_bump,
        actual_bump=actual_bump,
        baseline_version=baseline.version,
        current_version=current.version,
        diff=diff,
        message=message,
    )


def version_bump_between(old_version: str | None, new_version: str | None) -> str:
    if old_version is None or new_version is None:
        return "none"
    old = _parse_version(old_version)
    new = _parse_version(new_version)
    if old is None or new is None:
        return "none"
    if new[0] > old[0]:
        return "major"
    if new[0] < old[0]:
        return "none"
    if new[1] > old[1]:
        return "minor"
    if new[1] < old[1]:
        return "none"
    if new[2] > old[2]:
        return "patch"
    return "none"


def required_bump_for_gate(diff: PackageDiff) -> str:
    meaningful_events = [
        event
        for event in diff.events
        if event.category not in {"package", "risk"} and not _is_version_manifest_event(event.message)
    ]
    if any(event.breaking for event in meaningful_events):
        return "major"
    if any(event.changed for event in meaningful_events):
        return "minor"
    return "none"


@contextmanager
def load_head_package(package: SkillPackage) -> Iterator[SkillPackage | None]:
    repo_root = git_root(package.root)
    if repo_root is None or not _has_head(package.root):
        yield None
        return

    package_subpath = package.root.relative_to(repo_root)
    with tempfile.TemporaryDirectory(prefix="sit-gate-") as tmp:
        snapshot_root = _archive_ref(repo_root, "HEAD", Path(tmp) / "head")
        baseline_path = snapshot_root / package_subpath
        if not (baseline_path / "skill.yaml").exists():
            yield None
            return
        yield load_package(baseline_path)


def _gate_message(
    gate: str,
    *,
    ok: bool,
    required_bump: str,
    actual_bump: str,
    baseline_version: str | None,
    current_version: str | None,
    risk: str,
) -> str:
    state = "passed" if ok else "blocked"
    lines = [
        f"{gate} version gate {state}: risk={risk}, required={required_bump}, "
        f"actual={actual_bump}, version={baseline_version or '<unknown>'}->{current_version or '<unknown>'}",
    ]
    if not ok:
        lines.extend(
            [
                f"Reason: semantic changes require at least a {required_bump} version bump, but current change is {actual_bump}.",
                f"Fix: update skill.yaml to a {required_bump} bump or run `sit release {required_bump}` before committing.",
                "Override: use `--no-version-gate` only when the version policy exception is intentional.",
            ]
        )
    return "\n".join(lines)


def format_gate_failure(gate: VersionGateResult, *, limit: int = 6) -> str:
    lines = gate.summary_lines()
    if gate.diff is not None:
        events = [
            event.message
            for event in gate.diff.events
            if event.category not in {"package", "risk"} and not _is_version_manifest_event(event.message)
        ]
        if events:
            lines.extend(["Key semantic changes:", *[f"- {message}" for message in events[:limit]]])
            if len(events) > limit:
                lines.append(f"- ... {len(events) - limit} more changes")
    return "\n".join(lines)


def _parse_version(version: str) -> tuple[int, int, int] | None:
    parts = version.split(".")
    if len(parts) != 3:
        return None
    try:
        return tuple(int(part) for part in parts)  # type: ignore[return-value]
    except ValueError:
        return None


def _is_version_manifest_event(message: str) -> bool:
    return message.startswith("MANIFEST changed version: ")


def _bump_rank(bump: str) -> int:
    return BUMP_ORDER.get(bump, 0)


def _has_head(path: Path) -> bool:
    try:
        git_output(["rev-parse", "--verify", "HEAD"], cwd=path)
    except SitError:
        return False
    return True


def _archive_ref(repo_root: Path, ref: str, destination: Path) -> Path:
    destination.mkdir(parents=True, exist_ok=True)
    command = ["git", "archive", "--format=tar", ref]
    try:
        completed = subprocess.run(command, cwd=repo_root, check=False, capture_output=True)
    except FileNotFoundError as exc:
        raise SitError("git executable not found") from exc

    if completed.returncode != 0:
        message = completed.stderr.decode("utf-8", errors="replace").strip()
        raise SitError(f"git archive failed for {ref}" + (f": {message}" if message else ""))

    with tarfile.open(fileobj=io.BytesIO(completed.stdout), mode="r:") as archive:
        _safe_extract(archive, destination)
    return destination


def _safe_extract(archive: tarfile.TarFile, destination: Path) -> None:
    destination = destination.resolve()
    for member in archive.getmembers():
        target = (destination / member.name).resolve()
        if target != destination and destination not in target.parents:
            raise SitError(f"Unsafe path in git archive: {member.name}")
    try:
        archive.extractall(destination, filter="data")
    except TypeError:
        archive.extractall(destination)
