from __future__ import annotations

import json
from pathlib import Path

import yaml

from .errors import SitError
from .git import is_git_repo, run_git


def init_package(name: str, *, path: str | Path | None = None, no_git: bool = False) -> Path:
    root = Path(path).expanduser().resolve() if path else Path(name).expanduser().resolve()
    if root.exists() and any(root.iterdir()):
        raise SitError(f"Target directory is not empty: {root}")

    root.mkdir(parents=True, exist_ok=True)
    for relative in (
        "prompts",
        "schemas",
        "tests",
        "reports",
        ".github/workflows",
    ):
        (root / relative).mkdir(parents=True, exist_ok=True)

    _write_text(root / "skill.yaml", _skill_yaml(name))
    _write_text(root / "README.md", f"# {name}\n\nSkill Package managed by `sit`.\n")
    _write_text(root / "prompts" / "system.md", _system_prompt())
    _write_json(root / "schemas" / "input.schema.json", _input_schema())
    _write_json(root / "schemas" / "output.schema.json", _output_schema())
    _write_text(root / "tests" / "golden.jsonl", json.dumps(_golden_case(), ensure_ascii=False) + "\n")
    _write_text(root / "CHANGELOG.md", f"# Changelog\n\n## 0.1.0\n\n- Initial {name} Skill Package.\n")
    _write_text(root / ".github" / "workflows" / "sit-ci.yaml", _github_workflow())
    _write_text(root / ".github" / "pull_request_template.md", _pull_request_template())

    if not no_git and not is_git_repo(root):
        if run_git(["init", "-b", "main"], cwd=root, check=False) != 0:
            run_git(["init"], cwd=root)

    return root


def _skill_yaml(name: str) -> str:
    manifest = {
        "name": name,
        "version": "0.1.0",
        "description": f"{name} Skill Package.",
        "prompts": {"system": "prompts/system.md"},
        "schemas": {
            "input": "schemas/input.schema.json",
            "output": "schemas/output.schema.json",
        },
        "tests": {"golden": "tests/golden.jsonl"},
        "runtime": {"model": "configurable", "temperature": 0},
        "tags": ["skill", "sit"],
    }
    return yaml.safe_dump(manifest, allow_unicode=True, sort_keys=False)


def _system_prompt() -> str:
    return """You are a structured Skill Package.

Read the input and return JSON that conforms to the output schema.
"""


def _input_schema() -> dict:
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "type": "object",
        "additionalProperties": True,
        "properties": {
            "text": {"type": "string"},
        },
    }


def _output_schema() -> dict:
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "type": "object",
        "additionalProperties": False,
        "required": ["answer"],
        "properties": {
            "answer": {"type": "string"},
        },
    }


def _golden_case() -> dict:
    return {
        "case_id": "case-001",
        "input": {"text": "hello"},
        "expected": {"answer": "hello"},
        "match_mode": "schema_only",
    }


def _github_workflow() -> str:
    return """name: Skill CI
on: [pull_request]

env:
  SIT_PACKAGE_DIR: "."
  SIT_BASELINE_REF: "origin/${{ github.base_ref }}"
  SIT_HEAD_REF: "HEAD"
  SIT_ARTIFACT_DIR: "reports/ci"

jobs:
  validate-and-test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0
      - name: Install sit
        run: python -m pip install git+https://github.com/OpenRaiser/SitHub.git
      - run: sit validate "$SIT_PACKAGE_DIR"
      - run: sit test "$SIT_PACKAGE_DIR"
      - name: Write SitHub summary
        if: always()
        run: |
          sit ci-summary \
            --package-dir "$SIT_PACKAGE_DIR" \
            --baseline-ref "$SIT_BASELINE_REF" \
            --head-ref "$SIT_HEAD_REF" \
            --artifact-dir "$SIT_ARTIFACT_DIR" \
            >> "$GITHUB_STEP_SUMMARY"
      - name: Upload SitHub artifacts
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: sithub-report
          path: ${{ env.SIT_ARTIFACT_DIR }}
"""


def _pull_request_template() -> str:
    return """## Skill Change Summary

Run this locally and paste the output:

```bash
sit pr-summary <baseline-package> <current-package>
```

## Checklist

- [ ] `sit validate` passes
- [ ] `sit test` passes
- [ ] Breaking changes are explained
- [ ] Version bump is appropriate
"""


def _write_text(path: Path, content: str) -> None:
    if path.exists():
        raise SitError(f"Refusing to overwrite existing file: {path}")
    path.write_text(content, encoding="utf-8")


def _write_json(path: Path, data: dict) -> None:
    _write_text(path, json.dumps(data, ensure_ascii=False, indent=2) + "\n")
