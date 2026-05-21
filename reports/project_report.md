# SitHub 项目可视化报告

---

## 1. 项目主题

**SitHub：AI Skill Package 的 Git/GitHub**

`sit` 是一个 Git-native CLI，为 AI Skill 包（prompts、schemas、golden tests、runners、reports）提供语义版本控制。Git 记录文件变更，`sit` 在其上增加语义层：schema breaking 检测、prompt 行为漂移可视化、golden regression 反馈、版本门禁和发布报告。

类比关系：

```
Git : 代码版本控制  =  sit : Skill 语义版本控制
GitHub : 代码协作平台  =  SitHub : Skill 协作平台（未来）
```

---

## 2. 研究动机

AI Skill（prompt + schema + test + runner）正在成为新的软件交付单元，但现有工具链存在盲区：


| 问题                    | 具体表现                                                                            |
| --------------------- | ------------------------------------------------------------------------------- |
| Schema 变更不可见          | JSON schema 从 optional 改为 required 是 breaking change，但 `git diff` 只显示一行 JSON 变化 |
| Prompt 行为漂移           | 一句话的 prompt 修改可能改变整个输出行为，无法从文本 diff 判断影响                                        |
| Golden regression 无反馈 | 没有机制在提交前检测行为回归                                                                  |
| 版本语义缺失                | 不知道该 bump patch/minor/major，发布后下游才发现不兼容                                         |
| 脚本变更被忽略               | runner 脚本修改影响行为，但不在 prompt/schema diff 中体现                                      |


**核心洞察**：Skill 协作是一个控制系统——需要可观测性（状态感知）、误差信号（变更检测）、反馈动作（测试+门禁）和稳定性约束（版本语义）。

---

## 3. 核心贡献

### 3.1 设计理念：控制论式 Skill 协作

将 Skill 生命周期建模为闭环控制系统：

```
                    ┌─────────────────────────────────┐
                    │         Skill Package            │
                    │  (prompts, schemas, tests, etc.) │
                    └──────────┬──────────────────────┘
                               │
              ┌────────────────▼────────────────┐
              │        可观测性 (Observability)    │
              │  sit status / info / validate     │
              └────────────────┬────────────────┘
                               │
              ┌────────────────▼────────────────┐
              │        误差信号 (Error Signal)     │
              │  sit diff → breaking / review     │
              │  sit test → pass / fail           │
              └────────────────┬────────────────┘
                               │
              ┌────────────────▼────────────────┐
              │        反馈动作 (Feedback)         │
              │  version gate / pr-summary        │
              │  release report / CI summary      │
              └────────────────┬────────────────┘
                               │
              ┌────────────────▼────────────────┐
              │        稳定性 (Stability)          │
              │  release tag + bundle + reproduce  │
              └───────────────────────────────────┘
```

### 3.2 技术贡献


| 能力              | 说明                                                                                  |
| --------------- | ----------------------------------------------------------------------------------- |
| 递归 Schema Diff  | 支持 nested object、`oneOf`/`allOf`/`anyOf`、本地 `$ref` 解析，自动分类 breaking/review-required |
| Prompt 行为摘要     | 增删行数、关键标题、模板变量变化，可选 LLM 解释                                                          |
| Golden Test 四模式 | `schema_only` / `exact` / `partial` / `contains` + runner-backed 行为回归               |
| Version Gate    | commit/release 时自动检查版本 bump 是否匹配变更风险                                                |
| 多格式报告           | text / markdown / JSON / HTML，同一 payload 多种渲染                                       |
| Release Bundle  | `tar.gz` + `manifest.json` + `reproduce.sh`，可复现交付                                   |
| 依赖管理            | `deps.yaml` 本地路径依赖 + schema 兼容性预警 + 反向依赖扫描                                          |
| 资源感知 Diff       | scripts/assets/references 变更纳入语义 diff                                               |


---

## 4. 系统架构

### 4.1 CLI 命令全景

```
sit init          创建新 Skill Package
sit standardize   将已有项目转为标准包
sit onboard       保守接入已有 SKILL.md 项目
sit doctor        检查接入状态
├── sit validate  结构验证（manifest + schema + golden）
├── sit test      行为验证（golden match + runner）
├── sit diff      语义 diff（schema + prompt + resource）
├── sit report    生成报告（Markdown / JSON / HTML）
├── sit pr-summary  PR 摘要
├── sit ci-summary  CI 摘要
├── sit commit    带 version gate 的提交
├── sit release   版本发布 + bundle + changelog
└── sit deps check  依赖兼容性检查
```

### 4.2 Skill Package 标准结构

```
my-skill/
├── skill.yaml              # 包清单（name, version, prompts, schemas, tests, commands）
├── prompts/
│   └── system.md           # Prompt 文件
├── schemas/
│   ├── input.schema.json   # 输入 JSON Schema
│   └── output.schema.json  # 输出 JSON Schema
├── tests/
│   └── golden.jsonl        # Golden test cases
├── scripts/
│   └── run_case.py         # Runner 脚本
├── assets/                 # 静态资源
├── references/             # 参考文档
├── reports/                # 生成的报告
└── CHANGELOG.md            # 自动生成的变更日志
```

### 4.3 语义 Diff 工作流

```
Baseline (v0.1.0)          Current (v0.2.0)
      │                          │
      └──────── sit diff ────────┘
                    │
         ┌──────────────────────┐
         │    DiffEvent Stream   │
         │                      │
         │  SCHEMA: +required   │ → breaking
         │  PROMPT: +3 lines    │ → review-required
         │  SCRIPT: modified    │ → review-required
         │  GOLDEN: +2 fields   │ → changed
         └──────────┬───────────┘
                    │
         ┌──────────▼───────────┐
         │  Risk Classification  │
         │                      │
         │  breaking-change     │ → suggest major
         │  review-required     │ → suggest minor
         │  no-change           │ → suggest patch
         └──────────────────────┘
```

---

## 5. 代码规模与技术栈


| 指标         | 数值                              |
| ---------- | ------------------------------- |
| CLI 源码     | 5,478 行 Python（18 个模块）          |
| 测试代码       | 1,546 行（68 个测试用例）               |
| VS Code 扩展 | 234 行 TypeScript                |
| Demo 页面    | 1,210 行 HTML/JS                 |
| Git 提交数    | 21 commits                      |
| 开发周期       | 2026-05-13 ~ 2026-05-18（6 天）    |
| Python 版本  | 3.10+                           |
| 依赖         | PyYAML + jsonschema（仅 2 个运行时依赖） |


**模块代码量分布：**


| 模块                  | 行数  | 职责                                                 |
| ------------------- | --- | -------------------------------------------------- |
| `diff.py`           | 837 | 语义 diff 引擎（核心）                                     |
| `report.py`         | 727 | 报告生成（Markdown/JSON/HTML）                           |
| `cli.py`            | 595 | 命令行入口与调度                                           |
| `onboard.py`        | 580 | 项目接入与标准化                                           |
| `validate.py`       | 423 | 结构验证                                               |
| `release.py`        | 332 | 版本发布与 bundle                                       |
| `deps.py`           | 300 | 依赖管理                                               |
| `script_summary.py` | 274 | 脚本静态分析                                             |
| `gate.py`           | 258 | 版本门禁                                               |
| 其他                  | 952 | info, doctor, init, ref, summary, ci, git, package |


---

## 6. 当前进展

### 6.1 已完成功能（本地控制回路已闭环）

```
✅ sit init / standardize / onboard / doctor
✅ sit validate（manifest + schema + golden 结构验证）
✅ sit test（4 种 match mode + runner-backed 行为回归）
✅ sit diff（递归 schema + prompt text + resource-aware）
✅ sit report（Markdown / JSON / HTML 多格式）
✅ sit pr-summary / ci-summary
✅ sit commit / release（version gate + bundle + changelog）
✅ sit deps check（本地依赖 + schema 兼容性）
✅ VS Code Extension（Info / Validate / Test / Diff / Refresh）
✅ Demo HTML（3 场景交互式体验）
✅ PyInstaller dry-run 入口
```

### 6.2 真实试点验证


| 试点                                 | 状态   | 验证内容                                                            |
| ---------------------------------- | ---- | --------------------------------------------------------------- |
| `paper-taxonomy-mapper` (in-tree)  | ✅ 完成 | schema breaking diff, golden test, report                       |
| `paper-webpage-builder` (external) | ✅ 完成 | runner-backed test, PR loop, keywords walkthrough, quality loop |


**试点闭环证据：**

- F1: `sit test --run` 通过 `commands.run_case` 做 runner-backed 行为回归
- F2: 完整 PR 演示（新增 optional `keywords` 字段 → diff → commit gate → push → merge PR #2）
- F2.5: 基于 GGBench 反馈修复 skill 质量规则，版本升至 `0.4.0`

### 6.3 示例：语义 Diff 输出

`paper-taxonomy-mapper` v0.1.0 → v0.2.0 的 `sit diff` 输出：

```
PACKAGE  paper-taxonomy-mapper@0.1.0 -> paper-taxonomy-mapper@0.2.0
MANIFEST changed description
MANIFEST changed version: '0.1.0' -> '0.2.0'
PROMPT   changed classify
SCHEMA   changed output
SCHEMA   output allOf branch changed allOf[0]
SCHEMA   output oneOf branch removed allOf[0].notes.oneOf[1]
SCHEMA   output property added confidence (required)     ← breaking
SCHEMA   output property added evidence (required)       ← breaking
SCHEMA   output property added research_area (required)  ← breaking
SCHEMA   output $ref target changed paper_type
TEST     changed golden
GOLDEN   expected changed benchmark-001

Risk: breaking-change
Suggested bump: major
```

### 6.4 开发时间线

```
05-13  ████ 项目初始化 + 基础 CLI + schema diff
05-14  ██████ 复杂 schema diff (oneOf/allOf/$ref) + HTML report
05-15  █████ runner-backed test + release bundle + deps
05-16  ████ VS Code extension + external pilot
05-17  ███ resource-aware diff + script summary + demo upgrade
05-18  ██ 文档整理 + 外部试用包
```

---

## 7. 待完成事项


| 优先级 | 事项                        | 说明                                           |
| --- | ------------------------- | -------------------------------------------- |
| P0  | 外部团队试点                    | 2-3 个外部团队用 `external-trial-kit.md` 做 90 分钟试用 |
| P1  | `sit diff --explain`      | LLM 生成行为变化摘要（可选，无 API key 不阻塞）               |
| P1  | VS Code Extension Host 验证 | 当前环境无 `code` CLI，需手动验证                       |
| P2  | PyInstaller 真实 binary     | 当前只有 dry-run，未产出实际二进制                        |
| P2  | 渐进式 Skill 成熟度             | schema-optional、prompt-only 等轻量接入路径          |
| P3  | SitHub Web 平台             | 线上协作层（第二阶段）                                  |


---

## 8. 项目定位

```
                    ┌─────────────────────┐
                    │    SitHub (未来)     │  ← Skill 协作平台
                    │  Registry + Review   │
                    └──────────┬──────────┘
                               │
                    ┌──────────▼──────────┐
                    │     sit CLI(当前)    │  ← 本地语义版本控制
                    │  diff/test/gate/     │
                    │  report/release      │
                    └──────────┬──────────┘
                               │
                    ┌──────────▼──────────┐
                    │        Git           │  ← 文件版本控制
                    │  commit/branch/push  │
                    └─────────────────────┘
```

`sit` 不替代 Git，而是在 Git 之上增加 Skill 语义理解。就像 ESLint 不替代编辑器，而是在编辑器之上增加代码质量反馈。

---

