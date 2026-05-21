from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
import io
from pathlib import Path
import subprocess
import tarfile
import tempfile
from typing import Iterator

from .errors import SitError
from .git import git_root
from .package import SkillPackage, load_package


@dataclass(frozen=True)
class GitRange:
    old: str
    new: str

    @property
    def display(self) -> str:
        return f"{self.old}..{self.new}"


def parse_git_range(value: str | None) -> GitRange | None:
    if not value or "..." in value or value.count("..") != 1:
        return None

    old, new = value.split("..", 1)
    if not old or not new:
        return None
    if old.startswith(".") or new.startswith("."):
        return None
    return GitRange(old=old, new=new)


@contextmanager
def load_package_pair(old_spec: str, new_spec: str | None = None) -> Iterator[tuple[SkillPackage, SkillPackage]]:
    git_range = parse_git_range(old_spec) if new_spec is None else None
    if git_range is None:
        if new_spec is None:
            raise SitError("Expected a Git range like main..HEAD or two package paths")
        yield load_package(old_spec), load_package(new_spec)
        return

    with _load_git_range(git_range) as packages:
        yield packages


@contextmanager
def load_compare_package(current_spec: str, compare_spec: str | None) -> Iterator[tuple[SkillPackage, SkillPackage | None]]:
    git_range = parse_git_range(compare_spec)
    if git_range is None:
        package = load_package(current_spec)
        compare = load_package(compare_spec) if compare_spec else None
        yield package, compare
        return

    with _load_git_range(git_range, package_subpath=_package_subpath_for_spec(current_spec)) as (old, new):
        yield new, old


@contextmanager
def _load_git_range(git_range: GitRange, *, package_subpath: Path | None = None) -> Iterator[tuple[SkillPackage, SkillPackage]]:
    cwd = Path.cwd().resolve()
    repo_root = git_root(cwd)
    if repo_root is None:
        raise SitError(f"Git range requires running inside a Git work tree: {git_range.display}")

    package_subpath = package_subpath or _current_package_subpath(repo_root, cwd)
    with tempfile.TemporaryDirectory(prefix="sit-ref-") as tmp:
        tmp_root = Path(tmp)
        old_root = _archive_ref(repo_root, git_range.old, tmp_root / "old")
        new_root = _archive_ref(repo_root, git_range.new, tmp_root / "new")
        yield load_package(old_root / package_subpath), load_package(new_root / package_subpath)


def _package_subpath_for_spec(spec: str) -> Path | None:
    spec_path = Path(spec).expanduser()
    if spec_path == Path("."):
        return None

    cwd = Path.cwd().resolve()
    repo_root = git_root(cwd)
    if repo_root is None:
        return None

    path = spec_path.resolve()
    if path.is_file() and path.name == "skill.yaml":
        path = path.parent
    if not path.exists() or (path != repo_root and repo_root not in path.parents):
        return None
    return path.relative_to(repo_root)


def _current_package_subpath(repo_root: Path, cwd: Path) -> Path:
    for candidate in (cwd, *cwd.parents):
        if repo_root != candidate and repo_root not in candidate.parents:
            break
        if (candidate / "skill.yaml").exists():
            return candidate.relative_to(repo_root)
        if candidate == repo_root:
            break
    return Path(".")


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
