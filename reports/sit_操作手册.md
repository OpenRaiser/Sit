# sit CLI 操作手册

以 `paper-webpage-builder` 项目为例的完整演示指南。

---

## 0. 环境准备

```bash
# 安装 sit（从 SitHub 仓库）
cd /mnt/shared-storage-user/xuxinglong-p/SitHub
pip install -e .

# 验证安装
sit --version
# → sit 0.19.0

# 进入演示项目
cd /mnt/shared-storage-user/xuxinglong-p/paper-webpage-builder
```

---

## 1. 查看包状态：`sit info`

**用途**：一览 Skill Package 的完整状态（包信息、Git、文件、验证、测试）。

```bash
sit info .
```

**输出示例**：
```
Skill Package Info

Package: paper-webpage-builder
Version: 0.5.0
Description: Build polished single-page academic project webpages...

Git:
  Branch: experiment/sithub-pr-loop
  Commit: 5c11542
  Dirty: yes

Files:
  Prompts:
    skill: exists SKILL.md
    module_patterns: exists references/module_patterns.md
    design_principles: exists references/design_principles.md
  Schemas:
    input: exists schemas/input.schema.json
    output: exists schemas/output.schema.json
  Tests:
    golden: exists tests/golden.jsonl

Validation: pass
Golden tests: pass
Golden summary: SUMMARY 3/3 golden cases passed
```

**JSON 格式**（供脚本消费）：
```bash
sit info . --format json
```

---

## 2. 结构验证：`sit validate`

**用途**：检查 Skill Package 的结构完整性（manifest 路径、schema 合法性、golden case 格式）。

```bash
sit validate .
```

**输出示例**：
```
OK  name: paper-webpage-builder
OK  version: 0.5.0
OK  manifest exists: skill.yaml
OK  prompt.skill exists: SKILL.md
OK  prompt.module_patterns exists: references/module_patterns.md
OK  prompt.design_principles exists: references/design_principles.md
OK  schema.input exists: schemas/input.schema.json
OK  schema.output exists: schemas/output.schema.json
OK  test.golden exists: tests/golden.jsonl
OK  schema.input JSON schema valid
OK  schema.output JSON schema valid
OK  test.golden JSONL parsed: 3 cases
OK  command.run_case: configured
```

**什么时候会失败**：
- `skill.yaml` 中声明的文件不存在
- JSON Schema 语法错误
- golden.jsonl 格式不合法

---

## 3. 行为测试：`sit test`

**用途**：运行 golden test cases，验证 Skill 输出是否符合预期。

### 3.1 静态测试（对比 expected vs actual）

```bash
sit test .
```

**输出示例**：
```
Skill Tests
Result: pass

OK  latex-project-page: partial match passed
OK  pdf-with-assets-page: partial match passed
OK  existing-webpage-refresh: partial match passed
SUMMARY 3/3 golden cases passed
```

### 3.2 Runner-backed 测试（实际运行 Skill）

```bash
sit test . --run
```

这会调用 `skill.yaml` 中配置的 `commands.run_case`：
```yaml
commands:
  run_case: "python3 scripts/sit_run_case.py --input {input} --output {output}"
```

Runner 执行每个 golden case 的 input，生成 actual output，再与 expected 对比。

### 3.3 Match 模式说明

| 模式 | 含义 | 适用场景 |
|------|------|----------|
| `schema_only` | actual 只需通过 output schema 验证 | 早期开发，输出不稳定 |
| `partial` | expected 中的字段必须出现在 actual 中 | 推荐默认，允许额外字段 |
| `exact` | actual 必须与 expected 完全一致 | 严格回归测试 |
| `contains` | expected 的值必须是 actual 对应值的子串 | 文本类输出 |

---

## 4. 语义 Diff：`sit diff`

**用途**：对比两个 Git 版本之间的语义变化，自动分类风险等级。

### 4.1 基本用法

```bash
# 对比最近一次提交
sit diff HEAD~1..HEAD

# 对比任意两个分支/tag
sit diff main..HEAD
sit diff v0.4.0..v0.5.0
```

**输出示例**（v0.4.0 → v0.5.0）：
```
Skill Diff
Baseline: paper-webpage-builder@0.4.0
Current: paper-webpage-builder@0.5.0
Risk: review-required
Suggested version bump: minor

[manifest]
  - MANIFEST changed version: '0.4.0' -> '0.5.0'

[prompt]
  - PROMPT changed skill: SKILL.md -> SKILL.md (+17 -8; headings: ...)

[script]
  - SCRIPT added scripts/convert_figures.py (review required)
    summary: Convert paper figures into web-ready files with a stable manifest
    cli args: source_dir, target_dir, --dpi, --manifest, --no-multipage
    functions: have, slugify, gather_sources, rasterize_pdf_with_pymupdf...
  - SCRIPT added scripts/extract_tables.py (review required)
    summary: Extract every LaTeX table into a JSON ledger
  - SCRIPT added scripts/scan_pdf.py (review required)
    summary: Extract a compact content inventory from a paper PDF
  - SCRIPT changed scripts/scan_paper.py (review required)
    changes: added functions: read_text_with_warning, read_with_inputs

[risk]
  - RISK review-required

Prompt/Reference Text Summary:
PROMPT summary skill: +17 -8; headings: Paper Webpage Builder, Core Rule, Workflow
```

### 4.2 包含 Prompt 文本 Diff

```bash
sit diff HEAD~1..HEAD --prompt
```

在基本 diff 之外，额外展示 prompt 文件的逐行增删。

### 4.3 输出格式

```bash
sit diff HEAD~1..HEAD --format json     # 机器可读
sit diff HEAD~1..HEAD --format markdown  # PR 友好
sit diff HEAD~1..HEAD --format plain     # 旧版逐行
```

### 4.4 风险分类规则

| 风险等级 | 触发条件 | 建议 bump |
|----------|----------|-----------|
| `breaking-change` | required 字段新增/删除、type 变更、enum 缩减 | major |
| `review-required` | prompt 修改、脚本变更、optional 字段变化 | minor |
| `no-change` | 无语义变化 | patch |

---

## 5. 生成报告：`sit report`

**用途**：生成完整的变更报告（包含验证、测试、diff、复现命令）。

### 5.1 Markdown 报告

```bash
sit report . --compare HEAD~1..HEAD --format markdown
```

### 5.2 HTML 交互式报告

```bash
sit report . --compare HEAD~1..HEAD --format html -o reports/review.html
```

HTML 报告支持：
- 风险等级筛选
- 长 diff 折叠/展开
- Schema path 高亮
- 复现命令一键复制

### 5.3 JSON 报告（CI 集成）

```bash
sit report . --compare HEAD~1..HEAD --format json -o reports/report.json
```

---

## 6. PR 摘要：`sit pr-summary`

**用途**：生成 PR 描述，供 GitHub PR body 使用。

```bash
sit pr-summary main..HEAD
```

**输出**：Markdown 格式的变更摘要，包含风险等级、版本建议、测试结果和关键变更列表。

---

## 7. CI 摘要：`sit ci-summary`

**用途**：生成 GitHub Actions Step Summary。

```bash
sit ci-summary . --compare main..HEAD --artifact-dir reports/ci
```

会在 `reports/ci/` 下生成：
- `sit-report.md`
- `sit-report.json`
- `sit-report.html`
- `sit-summary.md`

---

## 8. 版本门禁：`sit commit`

**用途**：带语义检查的 git commit。如果版本 bump 不匹配变更风险，会阻断提交。

```bash
# 正常提交（version gate 通过）
sit commit -m "feat: add PDF extraction scripts"

# 如果 gate 阻断，会提示：
#   sit: error: version gate: current bump is patch but semantic diff requires minor
#   Hint: update version in skill.yaml to at least 0.5.0, or use --no-version-gate

# 强制绕过（不推荐）
sit commit -m "wip: draft" --no-version-gate
```

---

## 9. 版本发布：`sit release`

**用途**：发布新版本，自动生成 changelog、tag 和可选 bundle。

```bash
# 发布 minor 版本
sit release minor .

# 发布并打包 bundle
sit release minor . --bundle
```

**执行动作**：
1. 检查 version gate
2. 更新 `skill.yaml` 中的 version
3. 生成 release report + CHANGELOG 条目
4. 创建 Git commit + annotated tag
5. （如果 `--bundle`）生成 `dist/paper-webpage-builder-v0.5.0.tar.gz`

**Bundle 内容**：
```
paper-webpage-builder-v0.5.0/
├── manifest.json      # 文件列表 + sha256
├── reproduce.sh       # validate + test 复现命令
├── skill.yaml
├── SKILL.md
├── schemas/
├── tests/
├── scripts/
└── reports/
```

---

## 10. 依赖检查：`sit deps check`

**用途**：检查本地 Skill 之间的依赖兼容性。

```bash
sit deps check .
```

需要在项目中创建 `deps.yaml`：
```yaml
dependencies:
  - name: upstream-skill
    path: ../upstream-skill
    version: ">=0.3.0 <1.0.0"
```

---

## 11. 接诊检查：`sit doctor`

**用途**：检查已有项目的 SitHub 接入状态。

```bash
sit doctor .
```

**输出示例**：
```
SitHub Doctor

[git]       OK  Git repository detected
[github]    OK  GitHub remote configured
[manifest]  OK  skill.yaml exists and valid
[validate]  OK  All validations pass
[test]      OK  Golden tests pass (3/3)
[workflow]  OK  .github/workflows/sit-ci.yaml exists
[reports]   OK  Reports directory exists with content
```

---

## 12. Git 透传命令

`sit` 透传常用 Git 命令，无需切换工具：

```bash
sit add schemas/output.schema.json
sit commit -m "schema: add keywords field"
sit push
sit pull
sit branch feature/new-field
sit checkout main
sit log --oneline -5
```

---

## 完整演示流程（5 分钟）

```bash
cd /mnt/shared-storage-user/xuxinglong-p/paper-webpage-builder

# 1. 查看当前状态
sit info .

# 2. 验证结构
sit validate .

# 3. 运行测试
sit test .

# 4. 查看最近一次提交的语义变化
sit diff HEAD~1..HEAD

# 5. 查看详细 prompt diff
sit diff HEAD~1..HEAD --prompt

# 6. 生成 HTML 报告
sit report . --compare HEAD~1..HEAD --format html -o /tmp/demo-report.html

# 7. 生成 PR 摘要
sit pr-summary HEAD~1..HEAD

# 8. 查看 JSON 格式（机器可读）
sit diff HEAD~1..HEAD --format json | python3 -m json.tool | head -30
```

---

## 关键概念速查

| 概念 | 说明 |
|------|------|
| Skill Package | prompts + schemas + tests + scripts 的标准化组合 |
| `skill.yaml` | 包清单，声明所有文件路径和命令 |
| Golden Test | 预期输入→输出对，用于行为回归检测 |
| Semantic Diff | 不是文本 diff，而是理解 schema/prompt/script 语义的变更分析 |
| Version Gate | 提交/发布时检查版本号是否匹配变更风险 |
| Runner | 通过 `commands.run_case` 配置的外部执行器 |
| Bundle | 可复现的版本交付包（tar.gz + manifest + reproduce.sh） |

---

## 故障排查

| 问题 | 解决 |
|------|------|
| `sit: command not found` | `pip install -e /path/to/SitHub` |
| `version gate blocked` | 更新 `skill.yaml` 中的 version，或 `--no-version-gate` |
| `validate failed: file not found` | 检查 `skill.yaml` 中的路径是否正确 |
| `test failed: schema mismatch` | 检查 `schemas/output.schema.json` 是否与 golden case 一致 |
| `diff shows no baseline` | 确保有 Git 历史（至少 2 个 commit） |
