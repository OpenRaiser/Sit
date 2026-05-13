# SIT Project Instructions

This folder is the working space for SitHub and its local CLI, `sit`.

Before doing any work in this folder, agents must:

1. Read `00_项目枢纽.md`.
2. Add a short entry to the "处理记录" section describing the intended action before making changes.
3. Execute the action.
4. Update `00_项目枢纽.md` with any new files, decisions, validation results, or unresolved questions.

The hub file is the first retrieval target for this project. Keep it current and concise.

Do not silently overwrite project assumptions. If a change modifies the CLI scope, package specification, diff/test semantics, versioning model, storage model, or pilot integration, record the change in the hub before applying it elsewhere.

## Current Direction

SitHub aims to become the Git/GitHub-style version-control and collaboration system for Skill Packages.

The first stage is the local CLI `sit`. It should not reimplement Git storage, commits, branches, remotes, or merge. Git remains the underlying version history; `sit` adds the Skill semantic layer: package structure, validation, semantic diff, golden tests, PR summaries, release reports, and version pinning.

The completed local loop now includes:

- `sit init`
- `sit info`
- Git thin wrappers: `sit add`, `sit commit`, `sit push`, `sit pull`, `sit branch`, `sit checkout`, `sit log`
- `sit pr-summary`
- `sit release`
- Git range snapshots: `sit diff main..HEAD`, `sit pr-summary main..HEAD`, `sit report --compare main..HEAD`
- formatted semantic outputs: `sit diff --format text|markdown|json`, `sit pr-summary --format markdown|text|json`
- machine-readable status outputs: `sit test --format json`, `sit report --format json`, `sit info --format json`
- visual report output: `sit report --format html`
- GitHub Actions summary: `sit ci-summary --compare origin/main..HEAD`
- recursive schema diff and golden test match modes
- complex schema diff for `oneOf`, `allOf`, and local `$ref`
- commit/release version gate for breaking-change and version bump consistency
- friendlier version-gate errors and richer release notes

The next CLI milestone should focus on:

- CI configuration enhancements: custom baseline ref, package subdirectory, failure artifacts
- HTML report interaction enhancements: risk filters and collapsible long diffs

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
