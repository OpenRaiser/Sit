from __future__ import annotations

import subprocess
from pathlib import Path

from .errors import SitError


def run_git(args: list[str], *, cwd: Path | None = None, check: bool = True) -> int:
    command = ["git", *args]
    try:
        completed = subprocess.run(command, cwd=cwd, check=False)
    except FileNotFoundError as exc:
        raise SitError("git executable not found") from exc

    if check and completed.returncode != 0:
        raise SitError(f"git command failed: {' '.join(command)}")
    return completed.returncode


def git_output(args: list[str], *, cwd: Path | None = None) -> str:
    command = ["git", *args]
    try:
        completed = subprocess.run(command, cwd=cwd, check=False, text=True, capture_output=True)
    except FileNotFoundError as exc:
        raise SitError("git executable not found") from exc

    if completed.returncode != 0:
        message = completed.stderr.strip() or completed.stdout.strip()
        raise SitError(f"git command failed: {' '.join(command)}" + (f": {message}" if message else ""))
    return completed.stdout.strip()


def is_git_repo(path: Path) -> bool:
    try:
        git_output(["rev-parse", "--is-inside-work-tree"], cwd=path)
    except SitError:
        return False
    return True


def git_root(path: Path) -> Path | None:
    try:
        output = git_output(["rev-parse", "--show-toplevel"], cwd=path)
    except SitError:
        return None
    return Path(output).resolve()
