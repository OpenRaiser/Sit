# paper-taxonomy-mapper 0.2.0 SIT Report

Date: 2026-05-13

## Package

- Name: `paper-taxonomy-mapper`
- Version: `0.2.0`
- Root: `/mnt/shared-storage-user/xuxinglong-p/SitHub/examples/paper-taxonomy-mapper-v0.2.0`
- Manifest: `/mnt/shared-storage-user/xuxinglong-p/SitHub/examples/paper-taxonomy-mapper-v0.2.0/skill.yaml`
- Description: Classify AI research paper snippets with taxonomy, domain, evidence, and confidence.

## Validation

- Result: pass
- `OK  name: paper-taxonomy-mapper`
- `OK  version: 0.2.0`
- `OK  manifest exists: /mnt/shared-storage-user/xuxinglong-p/SitHub/examples/paper-taxonomy-mapper-v0.2.0/skill.yaml`
- `OK  prompt.classify exists: /mnt/shared-storage-user/xuxinglong-p/SitHub/examples/paper-taxonomy-mapper-v0.2.0/prompts/classify.md`
- `OK  schema.output exists: /mnt/shared-storage-user/xuxinglong-p/SitHub/examples/paper-taxonomy-mapper-v0.2.0/schemas/output.schema.json`
- `OK  test.golden exists: /mnt/shared-storage-user/xuxinglong-p/SitHub/examples/paper-taxonomy-mapper-v0.2.0/tests/golden.jsonl`
- `OK  schema.output JSON schema valid`
- `OK  test.golden JSONL parsed: 3 cases`

## Golden Tests

- Result: pass
- `OK  survey-001: schema_only match passed`
- `OK  benchmark-001: schema_only match passed`
- `OK  method-001: schema_only match passed`
- `SUMMARY 3/3 golden cases passed`

## Diff

- Baseline: `paper-taxonomy-mapper@0.1.0`
- Current: `paper-taxonomy-mapper@0.2.0`
- `PACKAGE paper-taxonomy-mapper@0.1.0 -> paper-taxonomy-mapper@0.2.0`
- `MANIFEST changed description: 'Classify AI research paper snippets into a compact taxonomy.' -> 'Classify AI research paper snippets with taxonomy, domain, evidence, and con...`
- `MANIFEST changed version: '0.1.0' -> '0.2.0'`
- `PROMPT changed classify: classify.md -> classify.md`
- `SCHEMA changed output: output.schema.json -> output.schema.json`
- `SCHEMA output allOf branch changed allOf[0]`
- `SCHEMA output oneOf branch removed allOf[0].notes.oneOf[1]`
- `SCHEMA output allOf branch added allOf[1]`
- `SCHEMA output property added confidence (required)`
- `SCHEMA output property added evidence (required)`
- `SCHEMA output property added research_area (required)`
- `SCHEMA output $ref target changed paper_type: #/definitions/paper_type -> #/$defs/paper_type`
- `TEST changed golden: golden.jsonl -> golden.jsonl`
- `GOLDEN expected changed benchmark-001`
- `GOLDEN expected changed method-001`
- `GOLDEN expected changed survey-001`
- `RISK breaking-change`

## Reproducibility

- Re-run validation with:
  `python3 -m sit.cli validate /mnt/shared-storage-user/xuxinglong-p/SitHub/examples/paper-taxonomy-mapper-v0.2.0`
- Re-run golden schema tests with:
  `python3 -m sit.cli test /mnt/shared-storage-user/xuxinglong-p/SitHub/examples/paper-taxonomy-mapper-v0.2.0`
- Re-run package diff with:
  `python3 -m sit.cli diff /mnt/shared-storage-user/xuxinglong-p/SitHub/examples/paper-taxonomy-mapper-v0.1.0 /mnt/shared-storage-user/xuxinglong-p/SitHub/examples/paper-taxonomy-mapper-v0.2.0`
