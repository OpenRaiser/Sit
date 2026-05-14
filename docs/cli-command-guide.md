# sit CLI 命令指南

`sit` 可以理解成 Git 之上的 Skill 语义控制层：

```text
git 负责保存历史：commit / branch / push / tag
sit 负责理解 Skill：结构是否完整、schema 有没有破坏、golden test 是否通过、PR 应该怎么看、版本该怎么升
```

## 1. 接入和观察

| 命令 | 含义 | 例子 |
|---|---|---|
| `sit onboard` | 把已有 `SKILL.md` 项目接入 SitHub | `sit onboard . --remote https://github.com/OWNER/REPO.git` |
| `sit init` | 从零创建一个标准 Skill Package | `sit init paper-reader --path ./paper-reader` |
| `sit info` | 查看一个 Skill 项目的完整状态快照 | `sit info` |
| `sit doctor` | 检查项目是否已经准备好进入 SitHub/GitHub 协作闭环 | `sit doctor` |
| `sit status` | 简单查看 manifest、prompt/schema/test/report 文件状态 | `sit status` |

典型接入：

```bash
cd paper-webpage-builder
sit onboard
sit doctor
sit info
```

`doctor` 更像体检，重点检查 Git、GitHub remote、manifest、validate/test、workflow 和 reports。`info` 更像状态面板，展示 package、Git、文件、validate/test 和最近 report 状态。

## 2. 校验和测试

| 命令 | 含义 | 例子 |
|---|---|---|
| `sit validate` | 检查 Skill Package 结构是否完整 | `sit validate` |
| `sit test` | 跑 golden case，验证 expected/actual 是否符合 schema 和 match mode | `sit test` |
| `sit test --format json` | 输出机器可读测试结果 | `sit test --format json` |

示例：

```bash
sit validate
sit test
```

如果 `schemas/output.schema.json` 缺失，`validate` 会失败。如果 `tests/golden.jsonl` 里的 expected 不符合 output schema，`test` 会失败。

当前 `sit test` 还不是完整运行 Skill 的执行器，而是先做结构化 golden 回归检查。它的价值是让 Skill 的输出契约可验证。

## 3. 语义 Diff 和报告

| 命令 | 含义 | 例子 |
|---|---|---|
| `sit diff old new` | 比较两个 Skill Package 的语义变化 | `sit diff v0.1.0 v0.2.0` |
| `sit diff main..HEAD` | 比较 Git 分支/提交范围里的 Skill 变化 | `sit diff main..HEAD` |
| `sit report` | 生成 validate/test/report 汇总 | `sit report` |
| `sit report --format html` | 生成可视化 HTML 报告 | `sit report --format html --output reports/report.html` |

示例：

```bash
sit diff main..HEAD
```

它不是普通文本 diff，而是输出 Skill 语义影响，例如：

```text
SCHEMA output property added confidence (required)
RISK breaking-change
Suggested version bump: major
```

这表示 `sit` 会判断：

- 这个改动是不是 breaking change
- 版本号应该是 patch、minor 还是 major
- schema 是否变得更严格
- prompt 是否发生变化

生成可视化报告：

```bash
sit report --compare main..HEAD --format html --output reports/pr-loop.html
```

这适合在浏览器里查看本次变更的整体影响。

## 4. PR 和 CI 协作

| 命令 | 含义 | 例子 |
|---|---|---|
| `sit pr-summary` | 生成 PR 评审摘要 | `sit pr-summary main..HEAD` |
| `sit ci-summary` | 给 GitHub Actions 生成 Summary 和 artifacts | `sit ci-summary --compare origin/main..HEAD` |

示例：

```bash
sit pr-summary main..HEAD
```

输出会接近一个 PR 说明：

```text
Skill Change Summary
Validation: pass
Golden Tests: pass
Diff risk: review-required
Suggested version bump: minor
Semantic Diff:
- prompt changed
- optional field added
```

GitHub Actions 中通常这样用：

```bash
sit ci-summary \
  --baseline-ref origin/main \
  --head-ref HEAD \
  --artifact-dir reports/ci \
  >> "$GITHUB_STEP_SUMMARY"
```

它会把 SitHub 的检查结果展示到 GitHub Actions 页面里，并生成 JSON、Markdown、HTML artifact。

## 5. 发布和门禁

| 命令 | 含义 | 例子 |
|---|---|---|
| `sit commit` | 提交前先跑 validate/test/version gate，再调用 `git commit` | `sit commit -m "feat: add confidence"` |
| `sit release` | 升版本、写 release report、打 Git tag | `sit release minor` |

示例：

```bash
sit commit -m "feat: add required confidence"
```

如果新增 required 字段，但是版本只做 minor bump，`sit commit` 可能会阻止提交：

```text
semantic changes require at least a major version bump
```

因为 required 字段可能破坏旧消费者，应该配套 major bump。

发布：

```bash
sit release major
```

它会：

- 修改 `skill.yaml` 版本号
- 写 `CHANGELOG.md`
- 生成 release report
- 创建 Git tag

## 6. Git 透传命令

这些命令本质上还是调用 Git，只是统一放在 `sit` 入口下：

| 命令 | 等价于 |
|---|---|
| `sit add .` | `git add .` |
| `sit push` | `git push` |
| `sit pull` | `git pull` |
| `sit branch` | `git branch` |
| `sit checkout -b xxx` | `git checkout -b xxx` |
| `sit log --oneline` | `git log --oneline` |

示例：

```bash
sit checkout -b experiment/schema-v2
sit add .
sit commit -m "feat: update output contract"
sit push -u origin experiment/schema-v2
```

区别是：

```text
git commit 只提交。
sit commit 会先检查 Skill 是否健康。
```

## 7. 完整使用例子

假设拿到一个已有 Skill 项目：

```bash
cd paper-webpage-builder
```

第一次接入 SitHub：

```bash
sit onboard --remote https://github.com/OWNER/paper-webpage-builder.git
sit doctor
sit validate
sit test
sit report --format html --output reports/sithub-onboarding.html
```

开始改功能：

```bash
sit checkout -b experiment/add-quality-checks
# 修改 SKILL.md / schema / golden tests
sit validate
sit test
sit diff main..HEAD
sit report --compare main..HEAD --format html --output reports/pr-loop.html
sit pr-summary main..HEAD
sit add .
sit commit -m "feat: add quality checks"
sit push -u origin experiment/add-quality-checks
```

发版：

```bash
sit release minor
sit push
```

## 8. 一句话记忆

```text
sit onboard：接入项目
sit doctor/info：看状态
sit validate/test：确认结构和 golden case 没坏
sit diff/report：看这次改动的语义影响
sit pr-summary/ci-summary：接入 GitHub PR 和 CI
sit commit/release：把检查变成版本门禁
sit add/push/checkout/log：继续复用 Git
```
