"""Programmatic Python SDK for sit.

Import and call directly — no subprocess, no CLI parsing.
Every function returns the same dict structure as the corresponding
``sit --format json`` command, so downstream code can reuse JSON contract
validators unchanged.

Example::

    from sit.sdk import Sit

    s = Sit("./my-skill-package")
    info = s.info()
    test = s.test()
    diff = s.diff("./baseline-package")
    pr = s.pr_summary("./baseline-package")
    report = s.report(compare="./baseline-package")
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .diff import diff_packages
from .doctor import build_doctor_payload
from .errors import SitError
from .gate import check_version_gate_against_head
from .info import build_info_payload
from .package import SkillPackage, load_package
from .release import release_package
from .report import build_report_payload
from .summary import build_pr_summary_payload
from .validate import build_test_payload, validate_package


class Sit:
    """High-level SDK entry point.

    Parameters
    ----------
    package_path : str | Path
        Path to a skill package directory (containing ``skill.yaml``)
        or directly to a ``skill.yaml`` file.
    """

    def __init__(self, package_path: str | Path) -> None:
        self._package_path = Path(package_path)
        self._package: SkillPackage | None = None

    # -- internal helpers --------------------------------------------------

    def _load(self) -> SkillPackage:
        if self._package is None:
            self._package = load_package(self._package_path)
        return self._package

    @staticmethod
    def _load_other(path: str | Path) -> SkillPackage:
        return load_package(path)

    # -- public API --------------------------------------------------------

    def info(self) -> dict[str, Any]:
        """Return package info (``sit.info.v1`` contract)."""
        return build_info_payload(self._load())

    def validate(self) -> dict[str, Any]:
        """Run structural validation only.  Returns a ``CheckResult``-shaped dict."""
        result = validate_package(self._load())
        return result.to_dict()

    def test(
        self,
        *,
        run_actual: bool = False,
        runner: str | None = None,
        timeout: int = 30,
    ) -> dict[str, Any]:
        """Run validation + golden tests (``sit.test.v1`` contract)."""
        return build_test_payload(
            self._load(),
            run_actual=run_actual,
            runner=runner,
            timeout=timeout,
        )

    def diff(
        self,
        other: str | Path,
        *,
        include_text_diffs: bool = False,
    ) -> dict[str, Any]:
        """Semantic diff against *other* package (``sit.diff.v1`` contract)."""
        old = self._load_other(other)
        new = self._load()
        result = diff_packages(old, new)
        return result.to_dict(
            old,
            new,
            include_text_diffs=include_text_diffs,
        )

    def pr_summary(
        self,
        baseline: str | Path,
        *,
        baseline_source: str | None = None,
        current_source: str | None = None,
    ) -> dict[str, Any]:
        """Build PR summary payload (``sit.pr_summary.v1`` contract)."""
        old = self._load_other(baseline)
        new = self._load()
        return build_pr_summary_payload(
            old,
            new,
            baseline_source=baseline_source,
            current_source=current_source,
        )

    def report(
        self,
        *,
        compare: str | Path | None = None,
        diff_command: str | None = None,
        package_source: str | None = None,
        compare_source: str | None = None,
    ) -> dict[str, Any]:
        """Build full report payload (``sit.report.v1`` contract)."""
        compare_pkg = self._load_other(compare) if compare else None
        return build_report_payload(
            self._load(),
            compare=compare_pkg,
            package_spec=str(self._package_path),
            diff_command=diff_command,
            package_source=package_source,
            compare_source=compare_source,
        )

    def doctor(self) -> dict[str, Any]:
        """Run environment diagnostics."""
        return build_doctor_payload(str(self._package_path))

    def release(
        self,
        *,
        bump: str = "patch",
        no_git_tag: bool = False,
        no_version_gate: bool = False,
        bundle: bool = False,
    ) -> dict[str, Any]:
        """Create a release.  Returns a summary dict."""
        message = release_package(
            self._load(),
            bump=bump,
            no_git_tag=no_git_tag,
            no_version_gate=no_version_gate,
            bundle=bundle,
        )
        return {"message": message}


def info(package_path: str | Path) -> dict[str, Any]:
    """Module-level convenience: ``sit.sdk.info(path)``."""
    return Sit(package_path).info()


def validate(package_path: str | Path) -> dict[str, Any]:
    """Module-level convenience: ``sit.sdk.validate(path)``."""
    return Sit(package_path).validate()


def test(package_path: str | Path, **kwargs: Any) -> dict[str, Any]:
    """Module-level convenience: ``sit.sdk.test(path)``."""
    return Sit(package_path).test(**kwargs)


def diff(old: str | Path, new: str | Path, **kwargs: Any) -> dict[str, Any]:
    """Module-level convenience: ``sit.sdk.diff(old, new)``."""
    return Sit(new).diff(old, **kwargs)


def pr_summary(baseline: str | Path, current: str | Path, **kwargs: Any) -> dict[str, Any]:
    """Module-level convenience: ``sit.sdk.pr_summary(baseline, current)``."""
    return Sit(current).pr_summary(baseline, **kwargs)


def report(package_path: str | Path, **kwargs: Any) -> dict[str, Any]:
    """Module-level convenience: ``sit.sdk.report(path)``."""
    return Sit(package_path).report(**kwargs)
