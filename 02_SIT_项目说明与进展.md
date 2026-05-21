# SitHub 项目说明与进展

日期：2026-05-14

## 1. 当前项目定义

SitHub 不是普通 CLI 项目说明文档里的“本地校验工具”。它的目标是 Skill 领域的版本控制与协作系统。

当前命名分工：

- `sit`：本地 CLI，对标 `git`。
- `SitHub`：未来 Web 协作平台，对标 GitHub。

当前阶段只实现 `sit`，但所有输出格式、包结构和报告都要为未来 SitHub 平台预留。

## 2. 需求来源

核心需求来自 `skill git.md`：

- Skill 需要版本控制和团队协作。
- 直接用 Git 不够，因为 Git 不理解 Skill 的结构和行为变化。
- 第一阶段应先走路线 A：底层依托 Git，`sit` 作为 CLI wrapper 和语义增强层。
- 后续再演进到路线 D：Git 存储 + 自建 SitHub 协作层 + GitHub 可选同步。

控制论学习总结给项目提供方法论：

- 先让系统状态可观测，再做控制。
- 用 diff/test/report 作为误差信号。
- 用 validate/test/release gate 保持稳定性。
- 用最小可行闭环替代过早平台化。
- 对大系统采用分层和分散控制。

## 3. 当前已有实现

当前代码已经补齐第一版本地闭环：

```text
sit/
  cli.py
  package.py
  init.py
  onboard.py
  info.py
  doctor.py
  gate.py
  ci.py
  git.py
  ref.py
  validate.py
  diff.py
  report.py
  summary.py
  release.py
  errors.py
tests/
  test_cli.py
examples/
  paper-taxonomy-mapper-v0.1.0/
  paper-taxonomy-mapper-v0.2.0/
```

已有命令：

- `sit init`
- `sit onboard`
- `sit info`
- `sit doctor`
- `sit status`
- `sit validate`
- `sit test`
- `sit diff`
- `sit report`
- `sit ci-summary`
- `sit pr-summary`
- `sit release`
- `sit add/commit/push/pull/branch/checkout/log`

这些命令已经覆盖第一版闭环：初始化 Skill Package、验证结构、运行 golden test、查看语义 diff、提交前 gate、生成 PR 摘要、发布版本报告。

当前 `sit diff`、`sit pr-summary`、`sit report --compare` 已支持 Git range 快照：

```bash
sit diff HEAD~1..HEAD
sit pr-summary main..HEAD
sit report --compare main..HEAD
```

当前 `sit diff` 和 `sit pr-summary` 已支持多格式输出：

```bash
sit diff main..HEAD --format text
sit diff main..HEAD --format markdown
sit diff main..HEAD --format json
sit pr-summary main..HEAD --format markdown
sit pr-summary main..HEAD --format text
sit pr-summary main..HEAD --format json
```

## 4. 当前实现与目标的差距

当前实现已经从“语义校验工具”推进到第一版 `sit` 控制闭环，但还不是完整的 `skill git.md` 目标。

关键差距：

| 目标 | 当前状态 | 下一步 |
|---|---|---|
| `sit init` | 已实现 | 增加模板类型 |
| `sit onboard` | 已实现已有 `SKILL.md` 项目的自动接入第一版 | 后续补 schema 精炼引导和 report artifact 策略 |
| `sit info` | 已实现 `text/json` 全景状态 | 后续接入更多风险信号 |
| `sit doctor` | 已实现 `text/json` 接入检查 | 后续与 `sit onboard` 串联 |
| Git 风格入口 | 已实现基础透传和 Git ref 感知 | 增加更友好的错误 |
| commit gate | 已实现 validate/test/version gate | 后续补更友好的阻断解释 |
| PR/CI 协作 | 已支持 PR summary、CI summary、`main..HEAD`、自定义 baseline/head ref、package 子目录和失败 artifact | 后续优化 GitHub 展示交互 |
| release | 已实现 bump/report/tag/version gate/release note 基础版 | 继续丰富 release artifact |
| Git ref diff | 已实现第一版 | 支持包子目录和更多 range 形式 |
| 递归 schema diff | 已实现 nested object、array、constraint、`oneOf`、`allOf`、本地 `$ref` 第一版 | 后续评估 `anyOf`、跨文件 `$ref` 和远程 `$ref` |
| match mode test | 已支持 schema_only、exact、partial、contains | 后续补 actual 生成/采集与 CI 报告 |
| 机器输出 | `diff` / `pr-summary` / `test` / `report` / `info` 已实现第一版 | 对接 GitHub Action summary |

## 5. 当前验证结果

在 `/mnt/shared-storage-user/xuxinglong-p/SitHub` 下已验证：

```bash
python3 -m sit.cli validate examples/paper-taxonomy-mapper-v0.1.0
python3 -m sit.cli test examples/paper-taxonomy-mapper-v0.1.0
python3 -m sit.cli info examples/paper-taxonomy-mapper-v0.2.0
python3 -m sit.cli info examples/paper-taxonomy-mapper-v0.2.0 --format json
python3 -m sit.cli validate examples/paper-taxonomy-mapper-v0.2.0
python3 -m sit.cli test examples/paper-taxonomy-mapper-v0.2.0
python3 -m sit.cli diff examples/paper-taxonomy-mapper-v0.1.0 examples/paper-taxonomy-mapper-v0.2.0
python3 -m sit.cli diff examples/paper-taxonomy-mapper-v0.1.0 examples/paper-taxonomy-mapper-v0.2.0 --format json
python3 -m sit.cli diff examples/paper-taxonomy-mapper-v0.1.0 examples/paper-taxonomy-mapper-v0.2.0 --format markdown
python3 -m sit.cli pr-summary examples/paper-taxonomy-mapper-v0.1.0 examples/paper-taxonomy-mapper-v0.2.0
python3 -m sit.cli pr-summary examples/paper-taxonomy-mapper-v0.1.0 examples/paper-taxonomy-mapper-v0.2.0 --format json
python3 -m unittest discover -s tests
python3 -m compileall -q sit tests
python3 -m sit.cli --version
```

结果：

- 两个 example package 的 validate 通过。
- 两个 example package 的 test 均为 3/3。
- v0.1.0 到 v0.2.0 的 diff 能识别新增 required 字段并标记 `RISK breaking-change`。
- `pr-summary` 能生成 PR Markdown，包含风险和建议 bump。
- `diff --format json/markdown` 和 `pr-summary --format json` 能输出结构化风险、建议 bump、validation/test/diff 信号。
- `sit info --format text/json` 能输出 package、Git、文件清单、validate/test 摘要和最近 report 状态。
- `sit onboard` 能从已有 `SKILL.md` 项目补齐 `skill.yaml`、schemas、golden case、GitHub Actions、PR 模板和 onboarding reports，默认不覆盖已有文件，并以 `sit doctor` 状态收尾。
- `sit doctor --format text/json` 能检查 Git、GitHub remote、manifest、validate/test、workflow 和 reports，并在工作区 dirty 时给出 warning。
- `sit diff` 能递归识别 nested object、enum、array items、additionalProperties 和边界约束变化。
- `sit diff` 能识别 `oneOf` / `allOf` 分支新增、删除、重排/内容变化，并能解析本地 `#/definitions/...` 与 `#/$defs/...` 引用后比较目标 schema。
- `sit test` 支持 `schema_only`、`exact`、`partial`、`contains` match mode，旧 golden 默认兼容为 `schema_only`；`sit test --run` 可通过 `commands.run_case` 或 `--runner` 运行 Skill 生成 actual 后再做行为回归比较。
- `sit commit` / `sit release` 能在有 Git HEAD 基线时阻断低于语义 diff 要求的 version bump，并支持 `--no-version-gate` 显式绕过。
- `sit test --format json` 输出 `sit.test.v1`；`sit report --format json` 输出 `sit.report.v1`；`sit info --format json` 输出 `sit.info.v1`。
- `sit report --format html` 能生成可视化静态 dashboard，支持风险筛选、长 diff 折叠/展开和复杂 schema path 展示；example 报告位于 `examples/paper-taxonomy-mapper-v0.2.0/reports/visual-v0.1.0-to-v0.2.0.html`。
- `sit ci-summary --compare origin/main..HEAD` 能从 report payload 生成 GitHub Actions Markdown summary；`sit ci-summary --baseline-ref ... --head-ref ... --package-dir ... --artifact-dir ...` 能支持仓库子目录包和 CI artifact。
- `sit init` 的 workflow 已自动写入 `$GITHUB_STEP_SUMMARY`，并在 `always()` 下上传 JSON/Markdown/HTML report artifact。
- version gate 阻断信息包含原因、修复建议和关键语义变更；release CHANGELOG/report 包含风险、gate、验证/测试和语义变更摘要。
- 临时 Git repo 中的 `HEAD~1..HEAD` 测试覆盖了 `diff`、`pr-summary`、`report --compare`，并覆盖了仓库子目录中的 Skill Package。
- 单元测试 36 项通过。
- compileall 通过。
- CLI 版本为 `0.17.0`。

## 6. 下一轮实现计划

### Step 1: runner 接入真实试点

- 为 `paper-webpage-builder` 增加 `commands.run_case`
- 构造能真实执行的 golden case
- 将 `sit test --run` 接入 GitHub Actions summary/report

### Step 2: release artifact 增强

- 稳定 release bundle
- 校验摘要
- 可复现归档

## 7. 当前非目标

当前不做：

- Web SitHub。
- 用户系统和权限系统。
- registry / marketplace。
- 自研 Git remote。
- 自动语义 merge。
- LLM behavior diff。

这些都要等 Git ref 闭环、机器可读 diff 和更深 test/diff 语义稳定后再做。

## 8. 工程判断

当前第一版闭环已经可以表达为：

```bash
sit init paper-taxonomy-mapper
sit info
sit checkout -b schema-v2
# edit prompts/schemas/tests
sit validate
sit test
sit diff main..HEAD
sit commit -m "schema: add confidence field"
sit push
sit pr-summary main..HEAD
sit release minor
```

下一步进入 onboarding 质量增强：让 `sit onboard` 生成的 schema、golden case 和 report artifact 策略更贴近真实 Skill 项目的长期维护需求。
