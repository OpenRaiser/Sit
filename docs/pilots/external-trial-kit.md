# External Trial Kit

This kit is for 2-3 external teams testing whether SitHub is useful before more large feature work.

## Goal

Validate whether `sit` gives real value to teams that maintain prompts, skills, or agent workflows in Git.

The trial should answer:

- Can a new user understand the value within 15 minutes?
- Can they onboard one real prompt/skill without heavy restructuring?
- Does semantic diff catch changes they would otherwise miss in review?
- Does `sit test` or `sit test --run` fit their workflow?
- Which parts feel too rigid, confusing, or unnecessary?

## Target Teams

Choose teams that already have prompt or agent artifacts and can share non-sensitive samples.

| Profile | Ideal Artifact | Why It Matters |
|---|---|---|
| Research group | Paper-writing, evaluation, data filtering, or benchmark prompts | Tests multi-prompt research workflows and table/figure-heavy outputs. |
| Product/ops team | Production prompt, response schema, regression examples | Tests review, version bump, CI summary, and safety around breaking changes. |
| Agent workflow builder | Tool-using agent prompt plus scripts/assets/references | Tests resource-aware diff and whether the package model is too rigid. |

Avoid first-time prompt users. The pilot should test SitHub, not teach prompt engineering.

## Trial Setup

Ask each team to prepare one small real project:

- 1-5 prompt or instruction files.
- Optional input/output schema if they already have one.
- 3-5 representative examples or test cases.
- Any runner script if they already have deterministic evaluation.
- Git repository preferred, but a folder is enough.

Do not ask them to rewrite everything before the session. The point is to observe adoption friction.

## 90-Minute Script

### 0-10 min: Baseline Interview

Ask:

- Where do your prompts live today?
- How do you review prompt changes?
- How do you know a prompt change broke something?
- What counts as a release or stable version?
- Which files besides prompts affect behavior?

Record the current workflow before showing `sit`.

### 10-25 min: Install and Inspect

Use one of:

```bash
python3 -m pip install -e .
python3 -m sit.cli --version
```

From their project folder:

```bash
python3 -m sit.cli doctor .
python3 -m sit.cli info . --format json
```

If the project is not a Skill Package yet:

```bash
python3 -m sit.cli onboard .
python3 -m sit.cli validate .
```

Observe whether setup blocks them.

### 25-45 min: First Real Change

Ask the team to make a realistic prompt or schema change.

Run:

```bash
python3 -m sit.cli validate .
python3 -m sit.cli test .
python3 -m sit.cli diff HEAD~1..HEAD
python3 -m sit.cli diff HEAD~1..HEAD --prompt
```

If they have a runner:

```bash
python3 -m sit.cli test . --run
```

Observe:

- Did the diff describe the change in their language?
- Did resource events appear when scripts/assets/references changed?
- Did risk and suggested bump match their expectation?
- Did the output help review, or add noise?

### 45-65 min: Review and Release Flow

Generate reviewer artifacts:

```bash
python3 -m sit.cli pr-summary HEAD~1..HEAD
python3 -m sit.cli report . --compare HEAD~1..HEAD
python3 -m sit.cli ci-summary . --compare HEAD~1..HEAD
```

If appropriate, test release without tagging:

```bash
python3 -m sit.cli release minor . --no-git-tag --bundle
```

Observe:

- Would they paste the PR summary into a real PR?
- Is the HTML/Markdown report understandable?
- Does release bundle solve a real reproducibility problem?

### 65-80 min: Friction Review

Ask them to mark every confusing point:

- Skill Package structure.
- `skill.yaml` required fields.
- schema requirement.
- golden test format.
- command names.
- output length.
- Git range assumptions.

Do not defend the tool. Record the friction as product data.

### 80-90 min: Close

Ask:

- Would you use this next week on a real prompt repo?
- What is the smallest change that would make it usable?
- What should be removed?
- Would a VS Code panel make this substantially easier?
- Is local CLI a benefit or a burden?

## Success Criteria

The pilot succeeds if at least two teams can:

- onboard one real project within 30 minutes;
- run `validate`, `test`, and `diff` without maintainer intervention;
- identify at least one useful semantic signal that Git alone did not show;
- name one concrete workflow where SitHub would reduce review or release risk.

The pilot fails if:

- teams cannot map their artifacts into a Skill Package without major rewriting;
- schema/test requirements block adoption;
- semantic diff mostly reports noise;
- users only understand the tool after a long explanation;
- they prefer a hosted product and reject local CLI as a workflow shape.

## Evidence to Collect

For each team, store a sanitized report under:

```text
reports/external-pilots/<team-or-profile>/
```

Recommended files:

- `baseline-notes.md`
- `commands.txt`
- `sit-info.json`
- `sit-diff.json`
- `sit-report.md`
- `sit-summary.md`
- `feedback.md`
- `decision.md`

Do not commit private prompts, customer data, tokens, or proprietary schemas.

## Decision Rules

After 2-3 pilots:

- If setup friction dominates, prioritize schema-optional and prompt-only package support.
- If CLI friction dominates, prioritize VS Code plugin before more CLI features.
- If semantic output is noisy, prioritize diff filtering and better summaries.
- If release/reproducibility is valued, prioritize binary distribution and release bundle polish.
- If users reject local workflow, reconsider hosted viewer/editor earlier.
