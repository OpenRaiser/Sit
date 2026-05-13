from __future__ import annotations

import contextlib
import io
import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from sit.cli import main


class CliTest(unittest.TestCase):
    def test_status_validate_and_test_pass_for_minimal_package(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            package = _write_package(Path(tmp), version="0.1.0")

            status_code, status_output = _run_cli(["status", str(package)])
            validate_code, validate_output = _run_cli(["validate", str(package)])
            test_code, test_output = _run_cli(["test", str(package)])

            self.assertEqual(status_code, 0)
            self.assertIn("Package: sample-skill", status_output)
            self.assertEqual(validate_code, 0)
            self.assertIn("OK  schema.output JSON schema valid", validate_output)
            self.assertEqual(test_code, 0)
            self.assertIn("SUMMARY 1/1 golden cases passed", test_output)

    def test_diff_reports_schema_and_prompt_changes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            old = _write_package(root / "old", version="0.1.0")
            new = _write_package(
                root / "new",
                version="0.2.0",
                prompt="Extract the answer and cite evidence.",
                extra_required={"confidence": {"type": "string"}},
            )

            code, output = _run_cli(["diff", str(old), str(new)])

            self.assertEqual(code, 0)
            self.assertIn("PROMPT changed extraction", output)
            self.assertIn("SCHEMA output property added confidence (required)", output)
            self.assertIn("RISK breaking-change", output)

    def test_diff_reports_recursive_schema_changes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            old = _write_package(root / "old", version="0.1.0")
            new = _write_package(root / "new", version="0.2.0")
            _write_nested_schema(old, enum_values=["paper", "web"], tag_values=["a", "b"], require_confidence=False, closed=False)
            _write_nested_schema(new, enum_values=["paper"], tag_values=["a", "b", "c"], require_confidence=True, closed=True)

            code, output = _run_cli(["diff", str(old), str(new)])

            self.assertEqual(code, 0)
            self.assertIn("SCHEMA output property added metadata.confidence (required)", output)
            self.assertIn("SCHEMA output enum removed values metadata.source: 'web'", output)
            self.assertIn("SCHEMA output enum added values metadata.tags[]: 'c'", output)
            self.assertIn("SCHEMA output additionalProperties restricted metadata", output)
            self.assertIn("RISK breaking-change", output)

    def test_diff_reports_complex_schema_ref_and_combinator_changes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            old = _write_package(root / "old", version="0.1.0")
            new = _write_package(root / "new", version="0.2.0")
            _write_complex_schema(old, include_link_payload=True, add_confidence_constraint=False)
            _write_complex_schema(new, include_link_payload=False, add_confidence_constraint=True)

            code, output = _run_cli(["diff", str(old), str(new)])

            self.assertEqual(code, 0)
            self.assertIn("SCHEMA output enum removed values classification: 'dataset'", output)
            self.assertIn("SCHEMA output oneOf branch removed payload.oneOf[1]", output)
            self.assertIn("SCHEMA output allOf branch added metadata.allOf[1]", output)
            self.assertIn("RISK breaking-change", output)

    def test_diff_reports_complex_schema_ref_target_changes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            old = _write_package(root / "old", version="0.1.0")
            new = _write_package(root / "new", version="0.2.0")
            _write_ref_target_schema(old, ref="#/definitions/reviewer")
            _write_ref_target_schema(new, ref="#/$defs/reviewer")

            code, output = _run_cli(["diff", str(old), str(new)])

            self.assertEqual(code, 0)
            self.assertIn("SCHEMA output $ref target changed reviewer: #/definitions/reviewer -> #/$defs/reviewer", output)
            self.assertIn("SCHEMA output enum added reviewer: 'lead', 'peer'", output)
            self.assertIn("RISK breaking-change", output)

    def test_diff_supports_json_and_markdown_formats(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            old = _write_package(root / "old", version="0.1.0")
            new = _write_package(root / "new", version="0.2.0", extra_required={"confidence": {"type": "string"}})

            json_code, json_output = _run_cli(["diff", str(old), str(new), "--format", "json"])
            markdown_code, markdown_output = _run_cli(["diff", str(old), str(new), "--format", "markdown"])

            self.assertEqual(json_code, 0)
            payload = json.loads(json_output)
            self.assertEqual(payload["schema_version"], "sit.diff.v1")
            self.assertEqual(payload["old"]["source"], str(old))
            self.assertEqual(payload["new"]["source"], str(new))
            self.assertEqual(payload["risk"], "breaking-change")
            self.assertEqual(payload["suggested_bump"], "major")
            self.assertTrue(any(event["breaking"] for event in payload["events"]))
            self.assertEqual(markdown_code, 0)
            self.assertIn("## Skill Diff", markdown_output)
            self.assertIn("Risk: `breaking-change`", markdown_output)

    def test_report_writes_markdown(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            package = _write_package(root / "pkg", version="0.1.0")
            output_path = root / "report.md"

            code, output = _run_cli(["report", str(package), "--output", str(output_path)])

            self.assertEqual(code, 0)
            self.assertIn("Wrote report:", output)
            report = output_path.read_text(encoding="utf-8")
            self.assertIn("# sample-skill 0.1.0 SIT Report", report)
            self.assertIn("## Golden Tests", report)
            self.assertIn("SUMMARY 1/1 golden cases passed", report)

    def test_test_command_supports_json_format(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            package = _write_package(Path(tmp) / "pkg", version="0.1.0")

            code, output = _run_cli(["test", str(package), "--format", "json"])

            self.assertEqual(code, 0)
            payload = json.loads(output)
            self.assertEqual(payload["schema_version"], "sit.test.v1")
            self.assertEqual(payload["package"]["name"], "sample-skill")
            self.assertEqual(payload["validation"]["status"], "pass")
            self.assertEqual(payload["golden_tests"]["status"], "pass")
            self.assertEqual(payload["golden_tests"]["passed"], 1)
            self.assertEqual(payload["golden_tests"]["total"], 1)

    def test_report_supports_json_format_with_diff(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            old = _write_package(root / "old", version="0.1.0")
            new = _write_package(root / "new", version="0.2.0", extra_required={"confidence": {"type": "string"}})

            code, output = _run_cli(["report", str(new), "--compare", str(old), "--format", "json"])

            self.assertEqual(code, 0)
            payload = json.loads(output)
            self.assertEqual(payload["schema_version"], "sit.report.v1")
            self.assertEqual(payload["package"]["version"], "0.2.0")
            self.assertEqual(payload["validation"]["status"], "pass")
            self.assertEqual(payload["golden_tests"]["status"], "pass")
            self.assertEqual(payload["diff"]["risk"], "breaking-change")
            self.assertEqual(payload["diff"]["suggested_bump"], "major")
            self.assertIn("python3 -m sit.cli diff", payload["reproducibility"]["diff"])

    def test_report_supports_html_format_with_visual_summary(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            old = _write_package(root / "old", version="0.1.0")
            new = _write_package(root / "new", version="0.2.0", extra_required={"confidence": {"type": "string"}})
            output_path = root / "visual.html"

            code, output = _run_cli(
                ["report", str(new), "--compare", str(old), "--format", "html", "--output", str(output_path)]
            )

            self.assertEqual(code, 0)
            self.assertIn("Wrote report:", output)
            html = output_path.read_text(encoding="utf-8")
            self.assertIn("<!doctype html>", html)
            self.assertIn("SitHub semantic control report", html)
            self.assertIn("Diff risk", html)
            self.assertIn("breaking-change", html)
            self.assertIn("Suggested bump", html)
            self.assertIn("SCHEMA output property added confidence", html)

    def test_ci_summary_outputs_markdown_with_diff(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            old = _write_package(root / "old", version="0.1.0")
            new = _write_package(root / "new", version="0.2.0", extra_required={"confidence": {"type": "string"}})

            code, output = _run_cli(["ci-summary", str(new), "--compare", str(old)])

            self.assertEqual(code, 0)
            self.assertIn("## SitHub CI Summary", output)
            self.assertIn("Package: `sample-skill@0.2.0`", output)
            self.assertIn("Diff risk: **breaking-change**", output)
            self.assertIn("Suggested version bump: `major`", output)
            self.assertIn("### Semantic Diff", output)

    def test_ci_summary_can_write_and_append_output(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            package = _write_package(root / "pkg", version="0.1.0")
            output_path = root / "summary.md"

            first_code, first_output = _run_cli(["ci-summary", str(package), "--output", str(output_path)])
            second_code, second_output = _run_cli(["ci-summary", str(package), "--output", str(output_path), "--append"])

            self.assertEqual(first_code, 0)
            self.assertEqual(second_code, 0)
            self.assertIn("Wrote CI summary:", first_output)
            self.assertIn("Wrote CI summary:", second_output)
            content = output_path.read_text(encoding="utf-8")
            self.assertEqual(content.count("## SitHub CI Summary"), 2)

    def test_init_creates_valid_package(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            package = root / "new-skill"

            code, output = _run_cli(["init", "new-skill", "--path", str(package), "--no-git"])
            validate_code, validate_output = _run_cli(["validate", str(package)])
            test_code, test_output = _run_cli(["test", str(package)])

            self.assertEqual(code, 0)
            self.assertIn("Initialized Skill Package:", output)
            self.assertTrue((package / "skill.yaml").exists())
            self.assertTrue((package / ".github" / "workflows" / "sit-ci.yaml").exists())
            workflow = (package / ".github" / "workflows" / "sit-ci.yaml").read_text(encoding="utf-8")
            self.assertIn("sit ci-summary --compare origin/main..HEAD", workflow)
            self.assertIn("GITHUB_STEP_SUMMARY", workflow)
            self.assertEqual(validate_code, 0)
            self.assertIn("OK  schema.output JSON schema valid", validate_output)
            self.assertEqual(test_code, 0)
            self.assertIn("SUMMARY 1/1 golden cases passed", test_output)

    def test_pr_summary_outputs_markdown(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            old = _write_package(root / "old", version="0.1.0")
            new = _write_package(
                root / "new",
                version="0.2.0",
                prompt="Extract the answer and cite evidence.",
                extra_required={"confidence": {"type": "string"}},
            )

            code, output = _run_cli(["pr-summary", str(old), str(new)])

            self.assertEqual(code, 0)
            self.assertIn("## Skill Change Summary", output)
            self.assertIn("Suggested version bump: `major`", output)
            self.assertIn("SCHEMA output property added confidence (required)", output)

    def test_pr_summary_supports_json_and_text_formats(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            old = _write_package(root / "old", version="0.1.0")
            new = _write_package(root / "new", version="0.2.0", extra_required={"confidence": {"type": "string"}})

            json_code, json_output = _run_cli(["pr-summary", str(old), str(new), "--format", "json"])
            text_code, text_output = _run_cli(["pr-summary", str(old), str(new), "--format", "text"])

            self.assertEqual(json_code, 0)
            payload = json.loads(json_output)
            self.assertEqual(payload["schema_version"], "sit.pr_summary.v1")
            self.assertEqual(payload["baseline"]["source"], str(old))
            self.assertEqual(payload["current"]["source"], str(new))
            self.assertEqual(payload["validation"]["status"], "pass")
            self.assertEqual(payload["golden_tests"]["status"], "pass")
            self.assertEqual(payload["risk"], "breaking-change")
            self.assertEqual(payload["diff"]["suggested_bump"], "major")
            self.assertEqual(text_code, 0)
            self.assertIn("Suggested version bump: major", text_output)
            self.assertIn("Semantic Diff:", text_output)

    def test_info_outputs_json_snapshot_without_git_repo(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            package = _write_package(Path(tmp) / "pkg", version="0.1.0")

            code, output = _run_cli(["info", str(package), "--format", "json"])

            self.assertEqual(code, 0)
            payload = json.loads(output)
            self.assertEqual(payload["schema_version"], "sit.info.v1")
            self.assertEqual(payload["package"]["name"], "sample-skill")
            self.assertEqual(payload["package"]["version"], "0.1.0")
            self.assertFalse(payload["git"]["available"])
            self.assertEqual(payload["validation"]["status"], "pass")
            self.assertEqual(payload["golden_tests"]["status"], "pass")
            self.assertEqual(payload["golden_tests"]["passed"], 1)
            self.assertEqual(payload["golden_tests"]["total"], 1)
            self.assertTrue(payload["files"]["prompts"]["extraction"]["exists"])
            self.assertTrue(payload["reports"]["exists"])

    def test_info_text_includes_git_and_dirty_state(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            package = _write_package(Path(tmp) / "git-info-skill", version="0.1.0")
            _git(package, "init")
            _git(package, "config", "user.email", "sit@example.test")
            _git(package, "config", "user.name", "SIT Test")
            _git(package, "add", ".")
            _git(package, "commit", "-m", "feat: initial skill")
            (package / "prompts" / "extraction.md").write_text("Extract the final answer.", encoding="utf-8")

            code, output = _run_cli_in(package, ["info"])

            self.assertEqual(code, 0)
            self.assertIn("Skill Package Info", output)
            self.assertIn("Package: sample-skill", output)
            self.assertIn("Git:", output)
            self.assertIn("Dirty: yes", output)
            self.assertIn("Validation: pass", output)
            self.assertIn("Golden summary: SUMMARY 1/1 golden cases passed", output)

    def test_golden_match_modes_pass_and_fail(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            package = _write_package(Path(tmp) / "pkg", version="0.1.0")
            records = [
                {"case_id": "schema", "input": {}, "expected": {"answer": "ok"}, "match_mode": "schema_only"},
                {"case_id": "exact", "input": {}, "expected": {"answer": "ok"}, "actual": {"answer": "ok"}, "match_mode": "exact"},
                {"case_id": "partial", "input": {}, "expected": {"answer": "ok"}, "actual": {"answer": "ok"}, "match_mode": "partial"},
                {
                    "case_id": "contains",
                    "input": {},
                    "expected": {"answer": "ok"},
                    "actual": {"answer": "ok with context"},
                    "match_mode": "contains",
                },
                {
                    "case_id": "contains-fail",
                    "input": {},
                    "expected": {"answer": "missing"},
                    "actual": {"answer": "ok with context"},
                    "match_mode": "contains",
                },
            ]
            (package / "tests" / "golden.jsonl").write_text(
                "\n".join(json.dumps(record) for record in records) + "\n",
                encoding="utf-8",
            )

            code, output = _run_cli(["test", str(package)])

            self.assertEqual(code, 1)
            self.assertIn("schema: schema_only match passed", output)
            self.assertIn("exact: exact match passed", output)
            self.assertIn("partial: partial match passed", output)
            self.assertIn("contains: contains match passed", output)
            self.assertIn("contains-fail: contains mismatch at answer", output)
            self.assertIn("SUMMARY 4/5 golden cases passed", output)

    def test_git_range_diff_and_pr_summary_use_committed_snapshots(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            package = _write_package(Path(tmp) / "git-range-skill", version="0.1.0")
            _git(package, "init")
            _git(package, "config", "user.email", "sit@example.test")
            _git(package, "config", "user.name", "SIT Test")
            _git(package, "add", ".")
            _git(package, "commit", "-m", "feat: initial skill")

            _upgrade_package_to_v2(package)
            _git(package, "add", ".")
            _git(package, "commit", "-m", "feat: require confidence")

            diff_code, diff_output = _run_cli_in(package, ["diff", "HEAD~1..HEAD"])
            summary_code, summary_output = _run_cli_in(package, ["pr-summary", "HEAD~1..HEAD"])
            json_code, json_output = _run_cli_in(package, ["diff", "HEAD~1..HEAD", "--format", "json"])

            self.assertEqual(diff_code, 0)
            self.assertIn("SCHEMA output property added confidence (required)", diff_output)
            self.assertIn("RISK breaking-change", diff_output)
            self.assertEqual(summary_code, 0)
            self.assertIn("Suggested version bump: `major`", summary_output)
            self.assertIn("sit diff HEAD~1..HEAD", summary_output)
            self.assertEqual(json_code, 0)
            payload = json.loads(json_output)
            self.assertEqual(payload["old"]["source"], "HEAD~1")
            self.assertEqual(payload["new"]["source"], "HEAD")

    def test_git_range_works_from_package_subdirectory_in_repo(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            package = _write_package(repo / "skills" / "sample", version="0.1.0")
            _git(repo, "init")
            _git(repo, "config", "user.email", "sit@example.test")
            _git(repo, "config", "user.name", "SIT Test")
            _git(repo, "add", ".")
            _git(repo, "commit", "-m", "feat: initial skill")

            _upgrade_package_to_v2(package)
            _git(repo, "add", ".")
            _git(repo, "commit", "-m", "feat: require confidence")

            code, output = _run_cli_in(package, ["diff", "HEAD~1..HEAD"])

            self.assertEqual(code, 0)
            self.assertIn("SCHEMA output property added confidence (required)", output)
            self.assertIn("RISK breaking-change", output)

    def test_report_compare_accepts_git_range(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            package = _write_package(Path(tmp) / "git-report-skill", version="0.1.0")
            _git(package, "init")
            _git(package, "config", "user.email", "sit@example.test")
            _git(package, "config", "user.name", "SIT Test")
            _git(package, "add", ".")
            _git(package, "commit", "-m", "feat: initial skill")

            _upgrade_package_to_v2(package)
            _git(package, "add", ".")
            _git(package, "commit", "-m", "feat: require confidence")

            code, output = _run_cli_in(package, ["report", "--compare", "HEAD~1..HEAD"])

            self.assertEqual(code, 0)
            self.assertIn("# sample-skill 0.2.0 SIT Report", output)
            self.assertIn("## Diff", output)
            self.assertIn("SCHEMA output property added confidence (required)", output)
            self.assertIn("python3 -m sit.cli diff HEAD~1..HEAD", output)

    def test_release_bumps_version_and_writes_report(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            package = _write_package(Path(tmp) / "pkg", version="0.1.0")

            code, output = _run_cli(["release", "minor", str(package), "--no-git-tag"])

            self.assertEqual(code, 0)
            self.assertIn("Released sample-skill@0.2.0", output)
            self.assertIn("git tag: skipped", output)
            manifest = (package / "skill.yaml").read_text(encoding="utf-8")
            self.assertIn("version: 0.2.0", manifest)
            self.assertTrue((package / "reports" / "release-v0.2.0.md").exists())

    def test_git_wrappers_can_add_and_commit_initialized_package(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            package = Path(tmp) / "git-skill"
            init_code, _ = _run_cli(["init", "git-skill", "--path", str(package)])
            self.assertEqual(init_code, 0)

            subprocess.run(["git", "config", "user.email", "sit@example.test"], cwd=package, check=True)
            subprocess.run(["git", "config", "user.name", "SIT Test"], cwd=package, check=True)

            add_code, _ = _run_cli_in(package, ["add", "."])
            commit_code, _ = _run_cli_in(package, ["commit", "-m", "feat: initial skill"])
            log_code, _ = _run_cli_in(package, ["log", "--oneline"])
            log_output = subprocess.run(
                ["git", "log", "--oneline"],
                cwd=package,
                check=True,
                text=True,
                capture_output=True,
            ).stdout

            self.assertEqual(add_code, 0)
            self.assertEqual(commit_code, 0)
            self.assertEqual(log_code, 0)
            self.assertIn("feat: initial skill", log_output)

    def test_commit_blocks_breaking_change_without_major_version_bump(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            package = _write_package(Path(tmp) / "gate-skill", version="0.1.0")
            _git(package, "init")
            _git(package, "config", "user.email", "sit@example.test")
            _git(package, "config", "user.name", "SIT Test")
            _git(package, "add", ".")
            _git(package, "commit", "-m", "feat: initial skill")

            _upgrade_package_to_v2(package)
            _git(package, "add", ".")

            code, stdout, stderr = _run_cli_capture(["commit", "-m", "feat: require confidence"], cwd=package)

            self.assertEqual(code, 2)
            self.assertIn("commit version gate blocked", stdout)
            self.assertIn("Reason: semantic changes require at least a major version bump", stderr)
            self.assertIn("Fix: update skill.yaml to a major bump or run `sit release major`", stderr)
            self.assertIn("SCHEMA output property added confidence (required)", stderr)

    def test_release_blocks_breaking_change_without_major_bump(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            package = _write_package(Path(tmp) / "release-gate-skill", version="0.1.0")
            _git(package, "init")
            _git(package, "config", "user.email", "sit@example.test")
            _git(package, "config", "user.name", "SIT Test")
            _git(package, "add", ".")
            _git(package, "commit", "-m", "feat: initial skill")
            _upgrade_package_to_v2(package)

            code, _stdout, stderr = _run_cli_capture(["release", "minor", str(package), "--no-git-tag"])

            self.assertEqual(code, 2)
            self.assertIn("release version gate blocked: risk=breaking-change, required=major, actual=minor", stderr)
            self.assertIn("Fix: update skill.yaml to a major bump or run `sit release major`", stderr)
            self.assertIn("version: 0.2.0", (package / "skill.yaml").read_text(encoding="utf-8"))

    def test_release_allows_major_bump_for_breaking_change(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            package = _write_package(Path(tmp) / "release-major-skill", version="0.1.0")
            _git(package, "init")
            _git(package, "config", "user.email", "sit@example.test")
            _git(package, "config", "user.name", "SIT Test")
            _git(package, "add", ".")
            _git(package, "commit", "-m", "feat: initial skill")
            _upgrade_package_to_v2(package)

            code, output = _run_cli(["release", "major", str(package), "--no-git-tag"])

            self.assertEqual(code, 0)
            self.assertIn("Released sample-skill@1.0.0", output)
            self.assertIn("version: 1.0.0", (package / "skill.yaml").read_text(encoding="utf-8"))
            changelog = (package / "CHANGELOG.md").read_text(encoding="utf-8")
            report = (package / "reports" / "release-v1.0.0.md").read_text(encoding="utf-8")
            self.assertIn("Release risk: breaking-change", changelog)
            self.assertIn("Version gate: required major, actual major", changelog)
            self.assertIn("SCHEMA output property added confidence (required)", changelog)
            self.assertIn("## Release Summary", report)
            self.assertIn("release version gate passed", report)
            self.assertIn("SCHEMA output property added confidence (required)", report)


def _run_cli(argv: list[str]) -> tuple[int, str]:
    stdout = io.StringIO()
    with contextlib.redirect_stdout(stdout):
        code = main(argv)
    return code, stdout.getvalue()


def _run_cli_in(cwd: Path, argv: list[str]) -> tuple[int, str]:
    old_cwd = Path.cwd()
    stdout = io.StringIO()
    try:
        import os

        os.chdir(cwd)
        with contextlib.redirect_stdout(stdout):
            code = main(argv)
    finally:
        os.chdir(old_cwd)
    return code, stdout.getvalue()


def _run_cli_capture(argv: list[str], *, cwd: Path | None = None) -> tuple[int, str, str]:
    old_cwd = Path.cwd()
    stdout = io.StringIO()
    stderr = io.StringIO()
    try:
        if cwd is not None:
            import os

            os.chdir(cwd)
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            code = main(argv)
    finally:
        if cwd is not None:
            import os

            os.chdir(old_cwd)
    return code, stdout.getvalue(), stderr.getvalue()


def _git(cwd: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=cwd, check=True, text=True, capture_output=True)


def _write_package(
    root: Path,
    *,
    version: str,
    prompt: str = "Extract the answer.",
    extra_required: dict[str, dict[str, str]] | None = None,
) -> Path:
    (root / "prompts").mkdir(parents=True)
    (root / "schemas").mkdir()
    (root / "tests").mkdir()
    (root / "reports").mkdir()

    (root / "skill.yaml").write_text(
        "\n".join(
            [
                "name: sample-skill",
                f"version: {version}",
                "description: Sample package for CLI tests.",
                "prompts:",
                "  extraction: prompts/extraction.md",
                "schemas:",
                "  output: schemas/output.schema.json",
                "tests:",
                "  golden: tests/golden.jsonl",
                "",
            ]
        ),
        encoding="utf-8",
    )
    (root / "prompts" / "extraction.md").write_text(prompt, encoding="utf-8")

    properties: dict[str, dict[str, str]] = {"answer": {"type": "string"}}
    required = ["answer"]
    if extra_required:
        properties.update(extra_required)
        required.extend(extra_required)

    schema = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "type": "object",
        "additionalProperties": False,
        "required": required,
        "properties": properties,
    }
    (root / "schemas" / "output.schema.json").write_text(json.dumps(schema), encoding="utf-8")

    expected = {"answer": "ok"}
    if extra_required:
        expected.update({name: "high" for name in extra_required})
    record = {"case_id": "case-1", "input": {"text": "hello"}, "expected": expected}
    (root / "tests" / "golden.jsonl").write_text(json.dumps(record) + "\n", encoding="utf-8")

    return root


def _write_nested_schema(
    root: Path,
    *,
    enum_values: list[str],
    tag_values: list[str],
    require_confidence: bool,
    closed: bool,
) -> None:
    schema_path = root / "schemas" / "output.schema.json"
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    metadata_required = ["source"]
    metadata_properties = {
        "source": {"type": "string", "enum": enum_values},
        "tags": {"type": "array", "items": {"type": "string", "enum": tag_values}},
    }
    if require_confidence:
        metadata_required.append("confidence")
        metadata_properties["confidence"] = {"type": "string"}
    schema["properties"]["metadata"] = {
        "type": "object",
        "additionalProperties": not closed,
        "required": metadata_required,
        "properties": metadata_properties,
    }
    schema_path.write_text(json.dumps(schema), encoding="utf-8")


def _write_complex_schema(root: Path, *, include_link_payload: bool, add_confidence_constraint: bool) -> None:
    schema_path = root / "schemas" / "output.schema.json"
    schema = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "type": "object",
        "additionalProperties": False,
        "required": ["answer", "classification", "payload", "metadata"],
        "properties": {
            "answer": {"type": "string"},
            "classification": {"$ref": "#/$defs/classification"},
            "payload": {
                "oneOf": [
                    {"$ref": "#/$defs/textPayload"},
                    *([{"$ref": "#/$defs/linkPayload"}] if include_link_payload else []),
                ]
            },
            "metadata": {
                "allOf": [
                    {"$ref": "#/$defs/baseMetadata"},
                    *([{"required": ["confidence"], "properties": {"confidence": {"type": "string"}}}] if add_confidence_constraint else []),
                ]
            },
        },
        "$defs": {
            "classification": {
                "type": "string",
                "enum": ["survey", "method", *([] if add_confidence_constraint else ["dataset"])],
            },
            "textPayload": {
                "type": "object",
                "additionalProperties": False,
                "required": ["text"],
                "properties": {"text": {"type": "string"}},
            },
            "linkPayload": {
                "type": "object",
                "additionalProperties": False,
                "required": ["url"],
                "properties": {"url": {"type": "string", "format": "uri"}},
            },
            "baseMetadata": {
                "type": "object",
                "additionalProperties": False,
                "required": ["source"],
                "properties": {"source": {"type": "string"}},
            },
        },
    }
    schema_path.write_text(json.dumps(schema), encoding="utf-8")


def _write_ref_target_schema(root: Path, *, ref: str) -> None:
    schema_path = root / "schemas" / "output.schema.json"
    schema = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "type": "object",
        "additionalProperties": False,
        "required": ["answer", "reviewer"],
        "properties": {
            "answer": {"type": "string"},
            "reviewer": {"$ref": ref},
        },
        "definitions": {
            "reviewer": {"type": "string"},
        },
        "$defs": {
            "reviewer": {"type": "string", "enum": ["lead", "peer"]},
        },
    }
    schema_path.write_text(json.dumps(schema), encoding="utf-8")


def _upgrade_package_to_v2(root: Path) -> None:
    manifest = (root / "skill.yaml").read_text(encoding="utf-8")
    (root / "skill.yaml").write_text(manifest.replace("version: 0.1.0", "version: 0.2.0"), encoding="utf-8")
    (root / "prompts" / "extraction.md").write_text("Extract the answer and cite evidence.", encoding="utf-8")

    schema_path = root / "schemas" / "output.schema.json"
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    schema["properties"]["confidence"] = {"type": "string"}
    schema["required"].append("confidence")
    schema_path.write_text(json.dumps(schema), encoding="utf-8")

    record = {"case_id": "case-1", "input": {"text": "hello"}, "expected": {"answer": "ok", "confidence": "high"}}
    (root / "tests" / "golden.jsonl").write_text(json.dumps(record) + "\n", encoding="utf-8")


if __name__ == "__main__":
    unittest.main()
