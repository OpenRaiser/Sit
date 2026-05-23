from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import __version__
from .agent_config import setup_agent_config, render_agent_setup_text
from .ci import render_ci_summary
from .deps import check_dependencies, dependency_warnings_for_commit, render_deps_text
from .doctor import build_doctor_payload, render_doctor_text
from .diff import diff_packages
from .errors import SitError
from .gate import check_version_gate_against_head, format_gate_failure
from .git import run_git
from .init import init_package
from .info import build_info_payload, render_info_text
from .onboard import onboard_existing_skill, render_onboard_text, render_standardize_text, standardize_skill_package
from .package import load_package
from .release import release_package
from .ref import load_compare_package, load_package_pair, parse_git_range
from .report import build_report, build_report_payload, render_report_html, render_report_markdown
from .script_summary import render_script_details
from .summary import build_pr_summary, build_pr_summary_payload, build_pr_summary_text
from .validate import build_test_payload, run_golden_schema_tests, validate_package

GIT_PASSTHROUGH_COMMANDS = {"add", "push", "pull", "branch", "checkout", "log"}


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if argv and argv[0] in GIT_PASSTHROUGH_COMMANDS:
        return cmd_git(argparse.Namespace(git_command=argv[0], git_args=argv[1:]))

    parser = _build_parser()
    args = parser.parse_args(argv)

    try:
        return args.func(args)
    except SitError as exc:
        print(f"sit: error: {exc}", file=sys.stderr)
        return 2


def cmd_status(args: argparse.Namespace) -> int:
    package = load_package(args.package)

    print(f"Package: {package.name or '<unknown>'}")
    print(f"Version: {package.version or '<unknown>'}")
    if package.description:
        print(f"Description: {package.description}")
    print(f"Root: {package.root}")
    print(f"Manifest: {package.manifest_path}")
    print()

    _print_path_group("Prompts", package.prompt_paths())
    _print_path_group("Schemas", package.schema_paths())
    _print_path_group("Tests", package.test_paths())
    report_dir = package.report_dir()
    marker = "exists" if report_dir.exists() else "missing"
    print(f"Reports: {marker} {report_dir}")
    return 0


def cmd_info(args: argparse.Namespace) -> int:
    package = load_package(args.package)
    payload = build_info_payload(package)
    if args.format == "json":
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(render_info_text(payload), end="")
    return 0


def cmd_doctor(args: argparse.Namespace) -> int:
    payload = build_doctor_payload(args.package)
    if args.format == "json":
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(render_doctor_text(payload), end="")
    return 0 if payload["ok"] else 1


def cmd_deps_check(args: argparse.Namespace) -> int:
    package = load_package(args.package)
    payload = check_dependencies(package)
    if args.format == "json":
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(render_deps_text(payload), end="")
    return 0 if payload["ok"] else 1


def cmd_onboard(args: argparse.Namespace) -> int:
    root = Path(args.path).expanduser().resolve()
    has_skill_yaml = (root / "skill.yaml").exists()
    has_skill_md = (root / "SKILL.md").exists()

    # --agent mode: add agent config to any package
    if args.agent:
        if has_skill_yaml:
            # Already a sit package — just add agent config
            agent_result = setup_agent_config(root, force=args.force)
            if args.format == "json":
                print(json.dumps(agent_result.to_dict(), ensure_ascii=False, indent=2))
            else:
                print(render_agent_setup_text(agent_result), end="")
            return 0
        if has_skill_md:
            # SKILL.md project — full onboard + agent config
            result = onboard_existing_skill(
                args.path, name=args.name, version=args.version,
                remote=args.remote, no_git=args.no_git, force=args.force,
            )
            agent_result = setup_agent_config(result.root, force=args.force)
            result.created.extend(agent_result.created)
            result.updated.extend(agent_result.updated)
            result.skipped.extend(agent_result.skipped)
            if args.format == "json":
                print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))
            else:
                print(render_onboard_text(result), end="")
            return 0 if result.ok else 1
        # No skill.yaml or SKILL.md — agent config only
        root.mkdir(parents=True, exist_ok=True)
        agent_result = setup_agent_config(root, force=args.force)
        if args.format == "json":
            print(json.dumps(agent_result.to_dict(), ensure_ascii=False, indent=2))
        else:
            print(render_agent_setup_text(agent_result), end="")
        return 0

    # Standard onboard (requires SKILL.md)
    result = onboard_existing_skill(
        args.path, name=args.name, version=args.version,
        remote=args.remote, no_git=args.no_git, force=args.force,
    )
    if args.format == "json":
        print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))
    else:
        print(render_onboard_text(result), end="")
    return 0 if result.ok else 1


def cmd_standardize(args: argparse.Namespace) -> int:
    result = standardize_skill_package(
        args.path,
        name=args.name,
        version=args.version,
        remote=args.remote,
        no_git=args.no_git,
        force=args.force,
    )
    if args.format == "json":
        print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))
    else:
        print(render_standardize_text(result), end="")
    return 0 if result.ok else 1


def cmd_validate(args: argparse.Namespace) -> int:
    package = load_package(args.package)
    result = validate_package(package)
    for message in result.messages:
        print(message)
    return 0 if result.ok else 1


def cmd_test(args: argparse.Namespace) -> int:
    package = load_package(args.package)
    if args.format == "json":
        payload = build_test_payload(package, run_actual=args.run, runner=args.runner, timeout=args.timeout)
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0 if payload["validation"]["ok"] and payload["golden_tests"]["ok"] else 1

    validation = validate_package(package)
    if not validation.ok:
        for message in validation.messages:
            print(message)
        return 1

    result = run_golden_schema_tests(package, run_actual=args.run, runner=args.runner, timeout=args.timeout)
    print("Skill Tests")
    print(f"Result: {'pass' if result.ok else 'fail'}")
    print()
    for message in result.messages:
        print(message)
    return 0 if result.ok else 1


def cmd_diff(args: argparse.Namespace) -> int:
    git_range = parse_git_range(args.old) if args.new is None else None
    with load_package_pair(args.old, args.new) as (old, new):
        result = diff_packages(old, new)
        print(
            _render_diff(
                result,
                old,
                new,
                args.format,
                old_source=git_range.old if git_range else args.old,
                new_source=git_range.new if git_range else args.new,
                show_prompt_diff=args.prompt,
            ),
            end="",
        )
    return 0


def cmd_report(args: argparse.Namespace) -> int:
    compare_range = parse_git_range(args.compare)
    with load_compare_package(args.package, args.compare) as (package, compare):
        package_spec = "." if compare_range else None
        diff_command = f"python3 -m sit.cli diff {args.compare}" if compare_range else None
        if args.format == "json":
            content = json.dumps(
                build_report_payload(
                    package,
                    compare=compare,
                    package_spec=package_spec,
                    diff_command=diff_command,
                    package_source=compare_range.new if compare_range else None,
                    compare_source=compare_range.old if compare_range else None,
                ),
                ensure_ascii=False,
                indent=2,
            ) + "\n"
        elif args.format == "html":
            content = render_report_html(
                build_report_payload(
                    package,
                    compare=compare,
                    package_spec=package_spec,
                    diff_command=diff_command,
                    package_source=compare_range.new if compare_range else None,
                    compare_source=compare_range.old if compare_range else None,
                )
            )
        else:
            content = build_report(
                package,
                compare=compare,
                package_spec=package_spec,
                diff_command=diff_command,
                package_source=compare_range.new if compare_range else None,
                compare_source=compare_range.old if compare_range else None,
            )

    if args.output:
        output = Path(args.output).expanduser().resolve()
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(content, encoding="utf-8")
        print(f"Wrote report: {output}")
    else:
        print(content, end="")
    return 0


def cmd_ci_summary(args: argparse.Namespace) -> int:
    package_spec_arg = args.package_dir or args.package
    compare_spec = _ci_compare_spec(args)
    compare_range = parse_git_range(compare_spec)
    with load_compare_package(package_spec_arg, compare_spec) as (package, compare):
        package_spec = package_spec_arg if args.package_dir else ("." if compare_range else None)
        diff_command = f"python3 -m sit.cli report {package_spec_arg} --compare {compare_spec}" if compare_range else None
        payload = build_report_payload(
            package,
            compare=compare,
            package_spec=package_spec,
            diff_command=diff_command,
            package_source=compare_range.new if compare_range else None,
            compare_source=compare_range.old if compare_range else None,
        )
        content = render_ci_summary(payload)

    if args.artifact_dir:
        _write_ci_artifacts(Path(args.artifact_dir).expanduser().resolve(), payload, content)

    if args.output:
        output = Path(args.output).expanduser().resolve()
        output.parent.mkdir(parents=True, exist_ok=True)
        if args.append:
            with output.open("a", encoding="utf-8") as handle:
                handle.write(content)
        else:
            output.write_text(content, encoding="utf-8")
        print(f"Wrote CI summary: {output}")
    else:
        print(content, end="")
    return 0


def cmd_init(args: argparse.Namespace) -> int:
    root = init_package(args.name, path=args.path, no_git=args.no_git)
    print(f"Initialized Skill Package: {root}")
    return 0


def cmd_git(args: argparse.Namespace) -> int:
    return run_git([args.git_command, *args.git_args], check=False)


def cmd_commit(args: argparse.Namespace) -> int:
    if not args.no_verify:
        package = load_package(args.package)
        validation = validate_package(package)
        for message in validation.messages:
            print(message)
        if not validation.ok:
            raise SitError("commit blocked: validation failed")

        if not args.no_test:
            tests = run_golden_schema_tests(package)
            for message in tests.messages:
                print(message)
            if not tests.ok:
                raise SitError("commit blocked: golden tests failed")

        if not args.no_version_gate:
            gate = check_version_gate_against_head(package)
            print(gate.message)
            if not gate.ok:
                raise SitError(format_gate_failure(gate))
        for warning in dependency_warnings_for_commit(package):
            print(f"WARN {warning}")

    git_args = ["commit"]
    if args.message:
        git_args.extend(["-m", args.message])
    git_args.extend(args.git_args)
    return run_git(git_args, check=False)


def cmd_pr_summary(args: argparse.Namespace) -> int:
    git_range = parse_git_range(args.old) if args.new is None else None
    with load_package_pair(args.old, args.new) as (old, new):
        content = _render_pr_summary(
            old,
            new,
            args.format,
            current_spec="." if git_range else None,
            diff_command=f"sit diff {args.old}" if git_range else None,
            baseline_source=git_range.old if git_range else args.old,
            current_source=git_range.new if git_range else args.new,
        )

    if args.output:
        output = Path(args.output).expanduser().resolve()
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(content, encoding="utf-8")
        print(f"Wrote PR summary: {output}")
    else:
        print(content, end="")
    return 0


def cmd_release(args: argparse.Namespace) -> int:
    package = load_package(args.package)
    print(
        release_package(
            package,
            args.bump,
            no_git_tag=args.no_git_tag,
            no_version_gate=args.no_version_gate,
            bundle=args.bundle,
        )
    )
    return 0


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="sit", description="Skill Iteration Toolkit CLI")
    parser.add_argument("--version", action="version", version=f"sit {__version__}")
    subparsers = parser.add_subparsers(dest="command", required=True)

    init = subparsers.add_parser("init", help="Create a Skill Package scaffold and optionally initialize Git")
    init.add_argument("name", help="Skill Package name")
    init.add_argument("--path", help="Target directory; defaults to ./<name>")
    init.add_argument("--no-git", action="store_true", help="Do not run git init in the new package")
    init.set_defaults(func=cmd_init)

    status = subparsers.add_parser("status", help="Show Skill Package manifest and file status")
    status.add_argument("package", nargs="?", default=".", help="Skill Package directory or skill.yaml")
    status.set_defaults(func=cmd_status)

    info = subparsers.add_parser("info", help="Show a full Skill Package state snapshot")
    info.add_argument("package", nargs="?", default=".", help="Skill Package directory or skill.yaml")
    info.add_argument("--format", choices=["text", "json"], default="text", help="Output format")
    info.set_defaults(func=cmd_info)

    doctor = subparsers.add_parser("doctor", help="Check SitHub onboarding readiness for an existing Skill Package")
    doctor.add_argument("package", nargs="?", default=".", help="Skill Package directory or skill.yaml")
    doctor.add_argument("--format", choices=["text", "json"], default="text", help="Output format")
    doctor.set_defaults(func=cmd_doctor)

    deps = subparsers.add_parser("deps", help="Check local Skill Package dependencies")
    deps_subparsers = deps.add_subparsers(dest="deps_command", required=True)
    deps_check = deps_subparsers.add_parser("check", help="Validate deps.yaml local path dependencies")
    deps_check.add_argument("package", nargs="?", default=".", help="Skill Package directory or skill.yaml")
    deps_check.add_argument("--format", choices=["text", "json"], default="text", help="Output format")
    deps_check.set_defaults(func=cmd_deps_check)

    onboard = subparsers.add_parser("onboard", help="Onboard an existing SKILL.md project into a SitHub Skill Package")
    onboard.add_argument("path", nargs="?", default=".", help="Existing Skill directory containing SKILL.md")
    onboard.add_argument("--name", help="Skill Package name; defaults to the directory name")
    onboard.add_argument("--version", default="0.1.0", help="Initial Skill Package version")
    onboard.add_argument("--remote", help="Optional GitHub remote URL to add as origin when missing")
    onboard.add_argument("--no-git", action="store_true", help="Do not initialize a Git repository")
    onboard.add_argument("--force", action="store_true", help="Overwrite generated SitHub onboarding files")
    onboard.add_argument("--agent", action="store_true", help="Generate agent auto-discovery config (.mcp.json + AGENTS.md)")
    onboard.add_argument("--format", choices=["text", "json"], default="text", help="Output format")
    onboard.set_defaults(func=cmd_onboard)

    standardize = subparsers.add_parser("standardize", help="Standardize an existing prompt or SKILL.md project into a Skill Package")
    standardize.add_argument("path", nargs="?", default=".", help="Existing Skill or prompt directory")
    standardize.add_argument("--name", help="Skill Package name; defaults to the directory name")
    standardize.add_argument("--version", default="0.1.0", help="Initial Skill Package version")
    standardize.add_argument("--remote", help="Optional GitHub remote URL to add as origin when missing")
    standardize.add_argument("--no-git", action="store_true", help="Do not initialize a Git repository")
    standardize.add_argument("--force", action="store_true", help="Overwrite generated SitHub standardization files")
    standardize.add_argument("--format", choices=["text", "json"], default="text", help="Output format")
    standardize.set_defaults(func=cmd_standardize)

    validate = subparsers.add_parser("validate", help="Validate manifest paths, schemas, and golden JSONL")
    validate.add_argument("package", nargs="?", default=".", help="Skill Package directory or skill.yaml")
    validate.set_defaults(func=cmd_validate)

    test = subparsers.add_parser("test", help="Run deterministic golden expected-vs-schema tests")
    test.add_argument("package", nargs="?", default=".", help="Skill Package directory or skill.yaml")
    test.add_argument("--format", choices=["text", "json"], default="text", help="Output format")
    test.add_argument("--run", action="store_true", help="Run each golden case through a Skill runner to generate actual output")
    test.add_argument("--runner", help="Runner command template; overrides skill.yaml commands.run_case")
    test.add_argument("--timeout", type=int, default=30, help="Runner timeout per golden case in seconds")
    test.set_defaults(func=cmd_test)

    diff = subparsers.add_parser("diff", help="Compare two Skill Package directories or a Git range")
    diff.add_argument("old", help="Baseline Skill Package directory, skill.yaml, or Git range such as main..HEAD")
    diff.add_argument("new", nargs="?", help="Current Skill Package directory or skill.yaml")
    diff.add_argument("--format", choices=["text", "plain", "markdown", "json"], default="text", help="Output format")
    diff.add_argument("--prompt", action="store_true", help="Include prompt/reference unified text diffs")
    diff.set_defaults(func=cmd_diff)

    report = subparsers.add_parser("report", help="Generate a validation, test, and reproducibility report")
    report.add_argument("package", nargs="?", default=".", help="Skill Package directory or skill.yaml")
    report.add_argument("--compare", help="Optional baseline Skill Package or Git range such as main..HEAD")
    report.add_argument("--format", choices=["markdown", "json", "html"], default="markdown", help="Output format")
    report.add_argument("-o", "--output", help="Write report to this path instead of stdout")
    report.set_defaults(func=cmd_report)

    ci_summary = subparsers.add_parser("ci-summary", help="Generate a Markdown summary for GitHub Actions")
    ci_summary.add_argument("package", nargs="?", default=".", help="Skill Package directory or skill.yaml")
    ci_summary.add_argument("--compare", help="Optional baseline Skill Package or Git range such as origin/main..HEAD")
    ci_summary.add_argument("--baseline-ref", help="Baseline Git ref used to build a compare range")
    ci_summary.add_argument("--head-ref", help="Head Git ref used to build a compare range")
    ci_summary.add_argument("--package-dir", help="Skill Package subdirectory when running from a repository root")
    ci_summary.add_argument("--artifact-dir", help="Write sit-report.json, sit-report.md, sit-report.html, and sit-summary.md")
    ci_summary.add_argument("-o", "--output", help="Write Markdown summary to this path instead of stdout")
    ci_summary.add_argument("--append", action="store_true", help="Append to --output instead of replacing it")
    ci_summary.set_defaults(func=cmd_ci_summary)

    pr_summary = subparsers.add_parser("pr-summary", help="Generate a Markdown Skill PR summary")
    pr_summary.add_argument("old", help="Baseline Skill Package directory, skill.yaml, or Git range such as main..HEAD")
    pr_summary.add_argument("new", nargs="?", help="Current Skill Package directory or skill.yaml")
    pr_summary.add_argument("--format", choices=["markdown", "text", "json"], default="markdown", help="Output format")
    pr_summary.add_argument("-o", "--output", help="Write summary to this path instead of stdout")
    pr_summary.set_defaults(func=cmd_pr_summary)

    release = subparsers.add_parser("release", help="Bump package version, write release report, and tag with Git")
    release.add_argument("bump", choices=["patch", "minor", "major"], help="Semantic version bump")
    release.add_argument("package", nargs="?", default=".", help="Skill Package directory or skill.yaml")
    release.add_argument("--no-git-tag", action="store_true", help="Skip creating an annotated Git tag")
    release.add_argument("--no-version-gate", action="store_true", help="Skip semantic diff versus version bump consistency check")
    release.add_argument("--bundle", action="store_true", help="Write a reproducible release tarball under dist/")
    release.set_defaults(func=cmd_release)

    for git_command in ("add", "push", "pull", "branch", "checkout", "log"):
        git_parser = subparsers.add_parser(git_command, help=f"Pass through to git {git_command}")
        git_parser.add_argument("git_args", nargs=argparse.REMAINDER)
        git_parser.set_defaults(func=cmd_git, git_command=git_command)

    commit = subparsers.add_parser("commit", help="Validate/test the Skill Package, then pass through to git commit")
    commit.add_argument("-m", "--message", help="Commit message")
    commit.add_argument("--package", default=".", help="Skill Package to validate before committing")
    commit.add_argument("--no-test", action="store_true", help="Skip golden tests before committing")
    commit.add_argument("--no-version-gate", action="store_true", help="Skip semantic diff versus version bump consistency check")
    commit.add_argument("--no-verify", action="store_true", help="Skip sit validation and tests")
    commit.add_argument("git_args", nargs=argparse.REMAINDER)
    commit.set_defaults(func=cmd_commit)

    return parser


def _print_path_group(title: str, paths: dict[str, Path]) -> None:
    print(f"{title}:")
    if not paths:
        print("  <none>")
        return
    for name, path in paths.items():
        marker = "exists" if path.exists() else "missing"
        print(f"  {name}: {marker} {path}")


def _ci_compare_spec(args: argparse.Namespace) -> str | None:
    if args.compare and (args.baseline_ref or args.head_ref):
        raise SitError("Use either --compare or --baseline-ref/--head-ref, not both")
    if args.compare:
        return args.compare
    if args.baseline_ref or args.head_ref:
        return f"{args.baseline_ref or 'origin/main'}..{args.head_ref or 'HEAD'}"
    return None


def _write_ci_artifacts(directory: Path, payload: dict, summary: str) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "sit-summary.md").write_text(summary, encoding="utf-8")
    (directory / "sit-report.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (directory / "sit-report.md").write_text(render_report_markdown(payload), encoding="utf-8")
    (directory / "sit-report.html").write_text(render_report_html(payload), encoding="utf-8")


def _render_diff(
    result,
    old,
    new,
    output_format: str,
    *,
    old_source: str | None = None,
    new_source: str | None = None,
    show_prompt_diff: bool = False,
) -> str:
    if output_format == "json":
        return json.dumps(
            result.to_dict(old, new, old_source=old_source, new_source=new_source, include_text_diffs=show_prompt_diff),
            ensure_ascii=False,
            indent=2,
        ) + "\n"
    if output_format == "markdown":
        lines = [
            "## Skill Diff",
            "",
            f"- Baseline: `{old.name or '<unknown>'}@{old.version or '<unknown>'}`",
            f"- Current: `{new.name or '<unknown>'}@{new.version or '<unknown>'}`",
            f"- Risk: `{result.risk}`",
            f"- Suggested version bump: `{result.suggested_bump}`",
            "",
            "### Events",
            "",
        ]
        for event in result.events:
            lines.append(f"- `{event.message}`")
            lines.extend(f"  - `{detail}`" for detail in _event_detail_lines(event))
        if result.text_diffs:
            lines.extend(["", "### Prompt/Reference Text Summary", ""])
            lines.extend(f"- `{text_diff.summary}`" for text_diff in result.text_diffs)
        if show_prompt_diff and result.text_diffs:
            lines.extend(["", "### Prompt/Reference Unified Diff", ""])
            for text_diff in result.text_diffs:
                lines.extend([f"#### {text_diff.kind}: {text_diff.name}", "", "```diff"])
                lines.extend(text_diff.lines)
                lines.extend(["```", ""])
        return "\n".join(lines) + "\n"
    if output_format == "plain":
        lines = []
        for event in result.events:
            lines.append(event.message)
            lines.extend(_event_detail_lines(event))
        if show_prompt_diff and result.text_diffs:
            lines.extend(["", "Prompt/Reference Unified Diff:"])
            for text_diff in result.text_diffs:
                lines.append(f"--- {text_diff.kind}: {text_diff.name}")
                lines.extend(text_diff.lines)
        return "\n".join(lines) + "\n"

    lines = [
        "Skill Diff",
        f"Baseline: {old.name or '<unknown>'}@{old.version or '<unknown>'}",
        f"Current: {new.name or '<unknown>'}@{new.version or '<unknown>'}",
        f"Risk: {result.risk}",
        f"Suggested version bump: {result.suggested_bump}",
        "",
    ]
    grouped: dict[str, list[str]] = {}
    for event in result.events:
        grouped.setdefault(event.category, []).append(event.message)
    for category in sorted(grouped):
        lines.append(f"[{category}]")
        for event in sorted((event for event in result.events if event.category == category), key=lambda item: item.message):
            lines.append(f"  - {event.message}")
            lines.extend(f"    {detail}" for detail in _event_detail_lines(event))
        lines.append("")
    if result.text_diffs:
        lines.extend(["Prompt/Reference Text Summary:"])
        lines.extend(text_diff.summary for text_diff in result.text_diffs)
    if show_prompt_diff and result.text_diffs:
        lines.extend(["", "Prompt/Reference Unified Diff:"])
        for text_diff in result.text_diffs:
            lines.append(f"--- {text_diff.kind}: {text_diff.name}")
            lines.extend(text_diff.lines)
    return "\n".join(lines) + "\n"


def _event_detail_lines(event) -> list[str]:
    details = getattr(event, "details", None)
    if not isinstance(details, dict):
        return []
    return render_script_details(details, indent="")


def _render_pr_summary(
    old,
    new,
    output_format: str,
    *,
    current_spec: str | None = None,
    diff_command: str | None = None,
    baseline_source: str | None = None,
    current_source: str | None = None,
) -> str:
    if output_format == "json":
        return json.dumps(
            build_pr_summary_payload(old, new, baseline_source=baseline_source, current_source=current_source),
            ensure_ascii=False,
            indent=2,
        ) + "\n"
    if output_format == "text":
        return build_pr_summary_text(old, new)
    return build_pr_summary(old, new, current_spec=current_spec, diff_command=diff_command)


if __name__ == "__main__":
    raise SystemExit(main())
