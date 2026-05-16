# SIT Project Instructions

This folder is the working space for SitHub and its local CLI, `sit`.

Before doing any work in this folder, agents must:

1. Read `00_项目枢纽.md`.
2. Add a short entry to the "当前处理摘要" section describing the intended action before making changes.
3. Execute the action.
4. Update `00_项目枢纽.md` with any new files, decisions, validation results, or unresolved questions.

The hub file is the first retrieval target for this project. Keep it current and concise.
Do not read `docs/history/` by default. Only open history archives when you need to trace a specific decision, PR, bug, or the user explicitly asks for historical detail.

Do not silently overwrite project assumptions. If a change modifies the CLI scope, package specification, diff/test semantics, versioning model, storage model, or pilot integration, record the change in the hub before applying it elsewhere.

## Current Direction

SitHub aims to become the Git/GitHub-style version-control and collaboration system for Skill Packages.

The first stage is the local CLI `sit`. It should not reimplement Git storage, commits, branches, remotes, or merge. Git remains the underlying version history; `sit` adds the Skill semantic layer: package structure, validation, semantic diff, golden tests, PR summaries, release reports, and version pinning.

The completed local loop now includes:

- `sit init`
- `sit onboard`
- `sit info`
- `sit doctor`
- Git thin wrappers: `sit add`, `sit commit`, `sit push`, `sit pull`, `sit branch`, `sit checkout`, `sit log`
- `sit pr-summary`
- `sit release`
- Git range snapshots: `sit diff main..HEAD`, `sit pr-summary main..HEAD`, `sit report --compare main..HEAD`
- formatted semantic outputs: `sit diff --format text|markdown|json`, `sit pr-summary --format markdown|text|json`
- machine-readable status outputs: `sit test --format json`, `sit report --format json`, `sit info --format json`
- visual report output: `sit report --format html`
- interactive HTML report filters, collapsible long diffs, and schema path badges
- GitHub Actions summary: `sit ci-summary --compare origin/main..HEAD`
- CI configuration for custom baseline refs, package subdirectories, and failure artifacts
- recursive schema diff and golden test match modes
- runner-backed `sit test --run` behavior regression
- complex schema diff for `oneOf`, `allOf`, and local `$ref`
- commit/release version gate for breaking-change and version bump consistency
- friendlier version-gate errors and richer release notes
- resource-aware diff events for `scripts/`, `assets/`, and `references/`
- prompt/reference text summaries and `sit diff --prompt`
- Git range report source labels that hide temporary snapshot paths in Markdown/HTML
- `sit release --bundle` reproducibility archives with sha256 manifest and `reproduce.sh`
- `sit deps check` for local `deps.yaml` path dependencies and non-blocking commit warnings
- release reverse-dependency hints for sibling Skill packages
- PyInstaller binary build dry-run via `scripts/build_binary.py`

The next CLI milestone should focus on:

- external pilot preparation before more large CLI feature expansion
- VS Code plugin minimum loop using existing JSON outputs
- gradual Skill Package adoption: schema-optional and prompt-only package paths
- user-facing docs cleanup that separates product usage from internal control-theory planning
- real PyInstaller build verification once PyInstaller is installed
- a second real Skill pilot for `deps.yaml`, release bundles, and reverse dependencies

The first validation packages are local generic examples:

- `examples/paper-taxonomy-mapper-v0.1.0`
- `examples/paper-taxonomy-mapper-v0.2.0`

## File Discipline

When adding or modifying implementation files:

1. Keep changes scoped to the `sit` CLI, Skill Package examples, or project documentation.
2. Keep generated outputs under explicit report/output paths.
3. Do not delete design docs, reports, schemas, prompts, or golden tests to make validation pass.
4. If a test or schema becomes obsolete, record the reason in `00_项目枢纽.md` before changing it.
5. Prefer small, inspectable CLI behavior over platform features. Do not start SitHub Web until the local control loop works.

## Validation Expectations

For project documentation changes:

- Check that `AGENTS.md` and `00_项目枢纽.md` agree on current scope.
- Check that referenced paths exist when possible.

For future CLI changes:

- Run the relevant command against the local example Skill Packages under `examples/`.
- Record command outcomes in `00_项目枢纽.md`.
