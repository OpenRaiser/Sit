<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/OpenRaiser/Sit/main/.github/assets/brand/sit-logo-horizontal-concept-dark.png">
    <source media="(prefers-color-scheme: light)" srcset="https://raw.githubusercontent.com/OpenRaiser/Sit/main/.github/assets/brand/sit-logo-horizontal-concept-light.png">
    <img src="https://raw.githubusercontent.com/OpenRaiser/Sit/main/.github/assets/brand/sit-logo-horizontal-concept-light.png" alt="sit semantic safety for AI skills" width="640">
  </picture>
</p>

[English](README.md) | [中文](README_zh.md)

**给会修改 prompt、schema、脚本和 Skill 包的 AI agent 准备的 Git 原生安全层。**

Git 能告诉你 prompt 改了几行。`sit` 会告诉你：这是 typo、行为变化、schema 契约变化、测试期望变化，还是发布风险。

```bash
pip install sit-toolkit
sit diff HEAD..WORKTREE
sit review HEAD..WORKTREE
```

当人或 AI agent 持续演进可复用 Skill 时，用 `sit` 在不替换 Git 的前提下获得语义 diff、golden test、版本门禁、PR review 和可复现发布。

![sit 将原始 Git diff 转成 Skill 语义审查信号](https://raw.githubusercontent.com/OpenRaiser/Sit/main/.github/assets/brand/sit-readme-hero-flat.png)

## 为什么需要 sit？

AI Skill 包不只是一个 prompt。一个真实 Skill 往往包含：

- `SKILL.md` 和参考说明
- 输入/输出 JSON schema
- golden 行为测试
- 验证脚本、资产处理脚本
- 发布报告和可复现 bundle

普通 Git 看到的是文件行。`sit` 看到的是 Skill 的行为边界：

```text
SCHEMA output property added keywords (optional)
GOLDEN expected changed latex-project-page
GOLDEN expected changed pdf-with-assets-page
GOLDEN expected changed existing-webpage-refresh
Risk: review-required
Suggested version bump: minor
Golden tests: pass
```

上面的例子来自真实包 [paper-webpage-builder](https://github.com/xxllovemkm/paper-webpage-builder)：一个面向 agent 的论文网页生成 Skill 修改了输出契约和预期行为。`sit` 把这次变更转成可审查的 PR 信号，而不是让 reviewer 从原始 diff 里猜意图。

![paper-webpage-builder 案例：Git 看到行，sit 看到行为](https://raw.githubusercontent.com/OpenRaiser/Sit/main/.github/assets/brand/sit-case-paper-webpage-builder-flat.png)

## 60 秒上手

已有 prompt 或 Skill 项目：

```bash
pip install sit-toolkit
sit standardize .
sit validate .
sit test .
sit diff HEAD..WORKTREE
sit review HEAD..WORKTREE
```

新建 Skill 包：

```bash
sit init my-skill
cd my-skill
sit install-hooks .
```

Skill 改动后，通过 `sit` 提交：

```bash
sit add .
sit commit --bump minor -m "improve webpage quality checks"
sit release minor . --bundle
```

Git 仍然负责存储和历史。`sit` 增加的是语义层：包结构、测试、diff、版本门禁、PR 摘要和发布报告。

## sit 能抓住什么

| 变更 | sit 会报告什么 |
|---|---|
| Prompt 或 reference 修改 | 改了哪些 heading、prompt 摘要、行为风险 |
| JSON schema 修改 | 字段增删、required 变化、enum 变化、breaking risk |
| Golden test 更新 | case 级 expected output 变化和 pass/fail |
| 脚本变化 | CLI 参数、函数/类/import、外部命令、review risk |
| 版本号不匹配 | commit/release 前检查 required bump vs actual bump |
| 本地依赖 | `deps.yaml` 兼容性和反向依赖提示 |
| 可复现发布 | bundle archive、sha256 manifest、`reproduce.sh` |

## 为 agent 设计

`sit` 给 agent 一个明确的 Skill 修改后闭环：

![sit agent safety loop](https://raw.githubusercontent.com/OpenRaiser/Sit/main/.github/assets/brand/sit-agent-loop-flat.png)

```bash
git status --short
sit validate .
sit test .
sit diff HEAD..WORKTREE
sit review HEAD..WORKTREE
```

一条命令添加项目说明和 MCP 配置：

```bash
sit onboard --agent ./my-skill
```

它会生成：

- `AGENTS.md`，给 Codex 和其他能读取仓库说明的 agent 使用
- `.mcp.json`，给 Claude Code、Cursor 等 MCP-aware 编辑器使用
- 一个本地工作流，要求 agent 在交付前验证、测试并审查语义变化

### Agent 接口

| 接口 | 用途 |
|---|---|
| 自动发现 | `sit onboard --agent` 接入 Codex、Claude Code、Cursor 等工具 |
| Python SDK | `from sit.sdk import Sit` 直接调用 |
| MCP server | `pip install 'sit-toolkit[mcp]'`，提供 12 个 stdio 工具 |
| LLM tool-use schema | `from sit.tool_use import get_tools_openai`，提供 OpenAI/Anthropic 兼容工具定义 |

Python SDK 示例：

```python
from sit.sdk import Sit

s = Sit("./my-skill-package")
s.info()
s.validate()
s.test()
s.diff_range("HEAD..WORKTREE")
s.review_range("HEAD..WORKTREE")
s.report_range("HEAD..WORKTREE")
```

MCP 配置：

```json
{
  "mcpServers": {
    "sit": { "command": "sit-mcp-server" }
  }
}
```

## 核心工作流

```bash
# 查看包状态
sit info .
sit doctor .

# 验证和测试行为
sit validate .
sit test .
sit test --run

# 审查语义变化
sit diff HEAD..WORKTREE
sit diff --staged
sit review main..HEAD
sit pr-summary main..HEAD
sit report . --compare main..HEAD --format html

# 安全提交和发布
sit install-hooks .
sit commit --bump minor -m "update skill behavior"
sit release minor . --bundle
```

## CI 集成

`sit init` 会生成 GitHub Actions workflow。也可以手动添加：

```yaml
- run: sit validate "$SIT_PACKAGE_DIR"
- run: sit test "$SIT_PACKAGE_DIR"
- run: sit test "$SIT_PACKAGE_DIR" --run
- run: sit ci-summary "$SIT_PACKAGE_DIR" --compare origin/main..HEAD >> "$GITHUB_STEP_SUMMARY"
```

当前包在 Python 3.10、3.11、3.12、3.13 上运行 `ruff`、`mypy` 和 `pytest`。

## 命令地图

**生命周期:** `sit init`、`sit standardize`、`sit onboard`、`sit doctor`

**质量检查:** `sit validate`、`sit test`、`sit test --run`、`sit deps check`

**Diff 与审查:** `sit diff`、`sit review`、`sit pr-summary`、`sit report`、`sit ci-summary`

**发布与安全:** `sit install-hooks`、`sit commit`、`sit release`、`sit undo`

**Git 透传:** `sit add`、`sit push`、`sit pull`、`sit branch`、`sit checkout`、`sit log`

## 安装

```bash
pip install sit-toolkit
```

可选 MCP 支持：

```bash
pip install 'sit-toolkit[mcp]'
```

要求：

- Python 3.10+
- Git
- 可选：支持 MCP 的编辑器或 agent runtime

## 项目状态

`sit` 当前聚焦本地 CLI 和 agent 集成闭环。它不替换 Git 的存储、分支、远端或 merge。Git 仍然是事实来源；`sit` 在 Git 之上增加 Skill-aware validation、semantic review、version gate 和 release artifacts。

## 许可证

Apache-2.0。参见 [LICENSE](LICENSE)。
