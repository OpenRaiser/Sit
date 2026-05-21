# External Pilot Feedback Form

Use this form once per trial team. Keep answers concrete and evidence-based.

## Team Profile

- Team or profile:
- Date:
- Trial facilitator:
- Artifact type:
- Repository/folder shape:
- Sensitive data removed: yes/no

## Baseline Workflow

- Where do prompts or skills live today?
- How are changes reviewed?
- How are regressions detected?
- How are stable versions or releases marked?
- Which files affect behavior besides prompts?

## Setup

| Question | Answer |
|---|---|
| Could they install or run `sit`? | |
| Could they locate or create `skill.yaml`? | |
| Did `sit onboard` help? | |
| Did validation errors make sense? | |
| Setup time in minutes | |

## Command Results

Record command outcomes, not full private output.

| Command | Pass/Fail | Notes |
|---|---|---|
| `sit doctor .` | | |
| `sit info . --format json` | | |
| `sit validate .` | | |
| `sit test .` | | |
| `sit test . --run` | | |
| `sit diff HEAD~1..HEAD` | | |
| `sit diff HEAD~1..HEAD --prompt` | | |
| `sit pr-summary HEAD~1..HEAD` | | |
| `sit report . --compare HEAD~1..HEAD` | | |
| `sit release minor . --no-git-tag --bundle` | | |

## Semantic Diff Quality

Rate 1-5.

| Signal | Score | Notes |
|---|---:|---|
| Prompt change summary | | |
| Schema change detection | | |
| Script/asset/reference detection | | |
| Risk level | | |
| Suggested version bump | | |
| PR summary usefulness | | |
| Report usefulness | | |

## Adoption Friction

Mark each as none / minor / blocking.

| Area | Rating | Evidence |
|---|---|---|
| Skill Package structure | | |
| `skill.yaml` fields | | |
| JSON Schema requirement | | |
| golden test format | | |
| runner setup | | |
| Git range usage | | |
| terminal output | | |
| Python/package installation | | |

## Product Direction Questions

- Would a VS Code plugin make this materially easier?
- Is local CLI a benefit or a burden?
- Would a static web viewer be useful before installation?
- Is schema optional support required for adoption?
- Does the team need multi-prompt or workflow-level packaging?
- Would they prefer hosted SaaS over Git-native local tooling?

## Verbatim Quotes

Use short direct quotes only when they clarify a decision.

- Quote 1:
- Quote 2:
- Quote 3:

## Outcome

Choose one:

- Adopt now
- Adopt after small changes
- Revisit later
- Not a fit

## Required Product Actions

List concrete actions with priority.

| Priority | Action | Evidence |
|---|---|---|
| P0 | | |
| P1 | | |
| P2 | | |
