# sit

[English](README.md) | [中文](README_zh.md)

**AI Skill 包的 Git 原生版本管理。**

`sit` 为提示词(prompt)、模式(schema)、黄金测试(golden test)和发布产物提供语义化版本管理。它能识别变更内容、评估风险等级，并在提交和发布前执行门禁检查。

```bash
pip install sit-toolkit
```

## 解决什么问题

用纯 Git 管理 prompt 或 schema，你只看到 `+13 -2` 行。你不知道这是修了个 typo 还是改了核心行为。`sit` 知道。

```
$ sit diff v0.3.0..v0.4.0

Skill Diff
Baseline: paper-webpage-builder@0.3.0
Current: paper-webpage-builder@0.4.0
Risk: review-required
Suggested version bump: minor

[prompt]
  - PROMPT changed SKILL.md (+13 -2; headings: Core Rule, Workflow)

[script]
  - SCRIPT changed scripts/scan_paper.py (review required)

[reference]
  - REFERENCE changed references/design_principles.md (+27 -3)
```

## 快速开始

```bash
# 新建包
sit init my-skill && cd my-skill

# 已有项目
sit standardize .

# 验证、测试、审查
sit validate . && sit test .
sit diff HEAD~1..HEAD
sit pr-summary HEAD~1..HEAD

# 发布
sit release minor . --bundle
```

## 命令

**生命周期:** `sit init`、`sit standardize`、`sit onboard`、`sit doctor`

**质量检查:** `sit validate`、`sit test`、`sit test --run`、`sit deps check`

**Diff 与审查:** `sit diff`、`sit pr-summary`、`sit report`、`sit ci-summary`

**发布:** `sit commit`、`sit release`

**Git 透传:** `sit add`、`sit push`、`sit pull`、`sit branch`、`sit checkout`、`sit log`

## Agent 集成

`sit` 通过三种接口向 AI agent 暴露能力:

| 接口 | 用法 |
|---|---|
| **Python SDK** | `from sit.sdk import Sit` — 直接 API 调用 |
| **MCP Server** | `pip install 'sit-toolkit[mcp]'` — 7 个工具，stdio 传输 |
| **LLM Tool-Use** | `from sit.tool_use import get_tools_openai` — OpenAI 和 Anthropic schema |

<details>
<summary>Python SDK 示例</summary>

```python
from sit.sdk import Sit

s = Sit("./my-skill-package")
s.info()            # 包元信息
s.validate()        # 结构检查
s.test()            # 黄金测试
s.diff("./old")     # 语义 diff
s.pr_summary("./old")  # PR 摘要
s.report(compare="./old")  # 完整报告
```
</details>

<details>
<summary>MCP Server 配置</summary>

```bash
pip install 'sit-toolkit[mcp]'
sit-mcp-server
```

```json
{
  "mcpServers": {
    "sit": { "command": "sit-mcp-server" }
  }
}
```
</details>

<details>
<summary>LLM Tool-Use schema</summary>

```python
from sit.tool_use import get_tools_openai, get_tools_anthropic

tools = get_tools_openai()      # OpenAI 格式
tools = get_tools_anthropic()   # Anthropic 格式
```
</details>

## CI 集成

`sit init` 会生成 GitHub Actions workflow，自动验证、测试，并在 PR 中发布语义化摘要:

```yaml
- run: sit validate "$SIT_PACKAGE_DIR"
- run: sit test "$SIT_PACKAGE_DIR"
- run: sit test "$SIT_PACKAGE_DIR" --run
- run: sit ci-summary "$SIT_PACKAGE_DIR" --compare origin/main..HEAD >> "$GITHUB_STEP_SUMMARY"
```

## 许可证

Apache-2.0。参见 [LICENSE](LICENSE)。
