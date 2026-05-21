# SitHub / sit 项目框架

## 1. 一句话定位

`sit` 是 Skill 领域的 Git 风格本地工具；`SitHub` 是未来 Skill 领域的 GitHub 风格协作平台。

第一阶段不造平台，不重写 Git。第一阶段要证明：在 Git 之上增加 Skill 语义层，就能显著改善 Skill 的版本控制、团队协作、评审、测试、发布和复现。

## 2. 为什么不是直接用 Git

Skill 是结构化可执行知识资产，不是普通代码文本。它通常包含：

- prompt / system instruction
- 输入输出 schema
- tool / connector 配置
- model runtime 参数
- golden tests
- 依赖的其他 skill 或知识库版本
- 运行报告和发布记录

Git 能保存这些文件的历史，但不知道变更含义：

- schema 字段从 optional 变 required 是 breaking change。
- prompt 加一句“注重预算控制”会改变行为边界。
- golden case 失败是行为回归。
- model 版本变化会影响复现性。
- 两个字段分别修改但教学策略相互冲突，Git 不会报冲突。

所以 SitHub 的价值不在“存历史”，而在 Git 之上的 Skill 语义控制层。

## 3. 工程控制论设计原则

本项目采用控制论式架构，不把 CLI 命令视为零散功能，而把 Skill 协作视为闭环控制系统。

### 3.1 可观测性

系统必须知道当前 Skill 的状态。

对应功能：

- `sit status`
- `sit info`
- `sit validate`
- manifest/schema/prompt/test 路径解析
- Git ref / tag / commit provenance

### 3.2 误差信号

系统必须把变更风险转化为明确误差信号。

对应功能：

- schema breaking change
- prompt diff
- golden regression
- dependency mismatch
- runtime/model drift
- missing version bump

### 3.3 反馈控制

系统必须把误差信号送回协作流程。

对应功能：

- `sit test`
- `sit pr-summary`
- GitHub Actions summary
- release note
- review checklist

### 3.4 稳定性

系统必须防止已发布 Skill 的行为静默漂移。

对应功能：

- pre-commit validate
- required schema diff risk
- match mode tests
- release gate
- tag + report + reproducibility command

### 3.5 最优控制

系统不追求一次做全平台，而是在当前约束下选择最能降低风险的动作。

当前选择：

- Git 负责历史、分支、remote、merge。
- `sit` 负责 Skill 语义。
- GitHub/GitLab 负责早期线上 PR。
- SitHub Web 后置。

### 3.6 冗余和容错

高风险变更不能只靠人工看 diff。

对应功能：

- schema validation + golden tests
- PR summary + CI summary
- report + reproducibility command
- future: behavior diff / LLM judge / dependency impact check

### 3.7 大系统分散控制

Skill 生态最终是大系统：多个 skill、多个团队、多个版本互相依赖。

对应功能：

- deps.yaml / dependency metadata
- version pin
- registry metadata
- depended-by graph
- future SitHub dependency dashboard

## 4. 系统分层

```text
Layer 0  Git substrate
         Commit, branch, tag, remote, merge, history.

Layer 1  Skill package convention
         skill.yaml, prompts, schemas, tests, deps, reports.

Layer 2  sit semantic CLI
         validate, diff, test, status, info, pr-summary, release.

Layer 3  hosted collaboration through existing platforms
         GitHub PR, GitHub Actions, GitLab CI.

Layer 4  SitHub platform, later
         Web diff viewer, review workflow, registry, dashboard, classroom/lab UX.
```

第一阶段只实现 Layer 1 和 Layer 2，并兼容 Layer 3。

## 5. 标准 Skill Package

推荐目录：

```text
skill-name/
  skill.yaml
  README.md
  prompts/
    system.md
    user_template.md
    few_shots/
  schemas/
    input.schema.json
    output.schema.json
  tests/
    golden.jsonl
  deps.yaml
  reports/
  CHANGELOG.md
  .github/
    workflows/sit-ci.yaml
    pull_request_template.md
```

`skill.yaml` 最小形态：

```yaml
name: paper-taxonomy-mapper
version: 0.1.0
description: Classify AI research papers into a taxonomy.

prompts:
  system: prompts/system.md

schemas:
  input: schemas/input.schema.json
  output: schemas/output.schema.json

tests:
  golden: tests/golden.jsonl

runtime:
  model: configurable
  temperature: 0

tags:
  - research
  - taxonomy
```

Golden case 推荐形态：

```json
{"case_id":"case-001","input":{},"expected":{},"match_mode":"schema_only"}
```

`match_mode` 的路线：

- `schema_only`：只检查 expected 或 actual 是否符合 output schema。
- `exact`：精确匹配 expected。
- `partial`：只匹配 expected 中出现的字段。
- `contains`：文本字段包含关键片段。
- `llm_judge`：后续扩展，需显式配置 evaluator。

## 6. CLI 命令模型

### 6.1 Git 风格透传命令

这些命令应尽量保持 Git 心智模型：

```bash
sit init
sit add
sit commit
sit push
sit pull
sit branch
sit checkout
sit log
```

原则：

- 不隐藏 Git，只减少 Skill 协作中的重复动作。
- `sit commit` 前运行 `sit validate`；可配置是否运行 `sit test`。
- Git 命令失败时保留原始错误信息。

### 6.2 Skill 语义命令

这些是 `sit` 与裸 Git 的差异化：

```bash
sit status
sit info
sit validate
sit diff
sit test
sit report
sit pr-summary
sit release patch|minor|major
sit deps check
```

最小闭环：

```text
sit init -> edit -> sit validate -> sit test -> sit diff
-> sit commit -> sit push -> sit pr-summary -> review -> sit release
```

`sit diff`、`sit pr-summary` 和 `sit report --compare` 应同时支持两种输入：

```bash
sit diff old-package new-package
sit diff main..HEAD
sit pr-summary main..HEAD
sit report --compare main..HEAD
```

目录输入用于本地示例和离线对比；Git range 输入用于真实 PR 工作流。

`sit diff` 和 `sit pr-summary` 应输出三种格式：

```bash
--format text
--format markdown
--format json
```

格式分工：

- `text`：本地终端快速阅读。
- `markdown`：GitHub PR、报告和人工 review。
- `json`：CI、后续 SitHub Web 和自动 gate。

## 7. 语义 Diff

`sit diff` 是第一核心能力。

它应输出至少三种格式：

- terminal：人读。
- markdown：PR / report 用。
- json：未来 SitHub Web 和 CI 用。

Diff 维度：

- manifest diff：name、version、description、runtime、tags。
- schema diff：properties、required、type、enum、items、additionalProperties、nested object。
- prompt diff：文本变更、模板变量变更、few-shot 变更。
- test diff：golden case 新增、删除、修改、match mode 变化。
- deps diff：依赖新增、删除、版本范围变化。

风险分类：

- `breaking-change`
- `review-required`
- `non-breaking`
- `no-change`

版本建议：

- required 字段新增、字段删除、类型收窄：major。
- 可选字段新增、prompt 行为边界扩大、golden case 增加：minor。
- 文案修复、测试说明、非行为性 metadata：patch。

## 8. 团队协作流程

早期使用 GitHub/GitLab 承载线上协作：

```text
1. sit init
2. sit branch feature/schema-v2
3. edit prompts/schemas/tests
4. sit validate
5. sit test
6. sit diff main..HEAD --format markdown
7. sit commit -m "schema: add confidence field"
8. sit push
9. sit pr-summary > PR description
10. reviewer 根据 summary、CI、diff 做评审
11. sit release minor|major
```

GitHub Actions 第一版：

```yaml
name: Skill CI
on: [pull_request]
jobs:
  validate-and-test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: pip install sit-toolkit
      - run: sit validate
      - run: sit test
      - run: sit diff main..HEAD --format=markdown >> $GITHUB_STEP_SUMMARY
```

## 9. 路线图

### Phase A0: 当前基线（已完成）

- 本地 CLI 骨架。
- `status/validate/test/diff/report`。
- 本地 example packages。

### Phase A1: Git 风格可用（基础闭环已完成）

- `sit init`
- `sit info`
- Git 薄封装：`add/commit/push/pull/branch/checkout/log`
- pre-commit validate
- 待补：更友好的错误输出

### Phase A2: 协作可用（目录对比版已完成）

- `sit pr-summary`
- GitHub PR template
- GitHub Actions template
- GitHub Actions summary (`sit ci-summary`)
- 已补：`main..HEAD` 支持、diff markdown/json output

### Phase A3: 发布可用（基础版已完成）

- `sit release`
- version bump
- Git tag
- CHANGELOG
- report provenance
- breaking-change/version bump gate
- 待补：更详细 release note

### Phase A4: 语义加深

- recursive schema diff（第一版已完成）
- match modes（`schema_only`、`exact`、`partial`、`contains` 第一版已完成）
- dependency check
- machine-readable package spec

### Phase D: SitHub 平台

需求被验证后再做：

- Web diff viewer
- Web review workflow
- Skill registry
- dependency graph
- classroom/lab dashboard
- fork / contribute-back

## 10. 成功标准

第一阶段成功标准不是“做出平台”，而是：

- 开发者能用 `sit` 初始化一个 Skill Package。
- 团队能通过 GitHub PR 看到 Skill 语义摘要。
- schema breaking change 不会静默进入 main。
- golden regression 能阻止明显行为回退。
- release 能绑定 Git tag、version、report 和复现命令。
- 后续 SitHub Web 能直接消费 CLI 输出的 JSON/Markdown。
