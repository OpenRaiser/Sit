# Quickstart: 3 Minutes with sit

A hands-on walkthrough of the core `sit` workflow: **init → validate → test → change → diff → pr-summary**.

## Prerequisites

```bash
pip install sit-toolkit
```

## Step 1: Create a Skill Package

```bash
sit init hello-skill
cd hello-skill
```

This generates a scaffold:

```
hello-skill/
  skill.yaml              # manifest: name, version, paths
  prompts/system.md       # the prompt
  schemas/                # input & output JSON schemas
  tests/golden.jsonl      # deterministic test cases
```

## Step 2: Validate & Test

```bash
sit validate   # check manifest paths, schemas, golden files
sit test       # run golden expected-vs-schema tests
```

Both should pass. If not, check that `skill.yaml` paths match your files.

## Step 3: Commit the Initial Scaffold

```bash
git add .
git commit -m "init: hello-skill scaffold"
```

## Step 4: Make a Change on a Feature Branch

```bash
git checkout -b feature/improve-prompt
```

Edit `prompts/system.md` — add a line:

```diff
 You are a greeting assistant.

 Read the user's input and return a JSON object with a single field "greeting" that says hello to the user by name.
+
+Always end the greeting with an exclamation mark.
```

Then commit:

```bash
git add .
git commit -m "feat: improve greeting prompt"
```

## Step 5: Diff & PR Summary

```bash
sit diff main..HEAD          # semantic diff of the skill package
sit pr-summary main..HEAD    # generate a Markdown PR summary
```

`sit diff` shows what changed in the skill contract (manifest, prompts, schemas, tests).
`sit pr-summary` produces a ready-to-paste PR description.

## Step 6: Merge with Confidence

```bash
git checkout main
git merge feature/improve-prompt
```

Or push the branch and open a GitHub PR — the included `.github/workflows/sit-ci.yaml` will run `sit validate` and `sit test` automatically.

## What's Next

| Want to... | Command |
|------------|---------|
| Check full package state | `sit info` |
| Generate a validation report | `sit report` |
| Onboard an existing project | `sit onboard` |
| Compare two versions | `sit diff v0.1.0..v0.2.0` |
| Bump version & release | `sit release patch` |

See the [full CLI reference](../../docs/cli-command-guide.md) for all commands and options.
