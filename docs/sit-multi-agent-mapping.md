# sit ↔ Multi-Agent 协议动词映射表

> 目的：把 `sit` 现有 CLI 能力映射到 `docs/plan.md` 描述的 multi-agent skill 协作协议动词，盘点四个实验各自的 readiness、可直接复用的 primitive、必须新增的 primitive。结论将决定是先用现有命令跑实验、还是先扩 CLI。
>
> 命名约定：协议层动词（论文里写的）大写斜体，CLI 层命令（代码里实现的）`code` 字体。

## 1. 协议层 vs CLI 层：核心映射

把 plan.md 的协议动词分两类：**结构性动词**（fork / propose / merge / revert）和**语义性动词**（evolve / verify / governance / retire）。前者是 git 已有的，sit 主要做包装；后者是 sit 的差异化所在。

| 协议动词 | 含义（多 agent 视角） | sit / git 现有 primitive | gap |
|---|---|---|---|
| **FORK** | Agent 从主线拉出私有 skill 演化分支 | `git checkout -b <agent-id>/<skill>` + `sit info` 校验起点 | 无 gap，git 原语足够 |
| **EVOLVE** | Agent 在分支上修改 prompt / schema / runner | 编辑文件 + `sit validate` + `sit test` | 无 gap，但需要 agent-loop 包装层（见第 4 节） |
| **PROPOSE** | Agent 把演化提案推到中央仓库 | `sit commit`（带 version gate）+ `git push` + `sit pr-summary` | 现有 PR summary 是给人看的；agent 消费需要 `sit.summary.v1` JSON schema 稳定化 |
| **VERIFY** | 自动检验：结构 / 行为 / 兼容 | `sit validate` + `sit test --run` + `sit diff` 的 risk 分类 + version gate | 无 gap。这是 sit 最强的部分 |
| **MERGE** | 选定提案并入主线 | `git merge` + `sit release` + `sit deps check` 反向依赖告警 | 无 gap。注意：sit 不做语义 merge，冲突由 git 报，由 agent 解决 |
| **REVERT** | 回滚到指定历史版本 | `git revert <sha>` 或 `git reset` + `sit release` 重出版本 | 无 gap。第 2 个实验的核心 |
| **RETIRE** | 删除 / 归档无用 skill | 删除 manifest 条目 + `sit diff` 标 breaking + `sit release major` | 部分 gap：sit 现在不专门标注 "retired"，需要 manifest 加 `status: retired` 字段 |
| **GOVERN** | 准入门槛：质量 / 信用 / 多人审 | `sit commit` 的 version gate + GitHub PR review + Actions CI | 部分 gap：信用分（agent reputation）目前不在 sit 内，建议放到实验框架里实现 |

## 2. 14 条 sit CLI 在协议中的角色

| sit 命令 | 协议层角色 | agent 用法 |
|---|---|---|
| `sit init` | bootstrap 中央仓库的 skill package 骨架 | 实验初始化阶段调用一次 |
| `sit standardize` / `sit onboard` | 把已有 prompt-only 资产升级为可被多 agent 协作的 package | 引入历史 baseline skill 时使用 |
| `sit info --format json` | **agent 的可观测性入口**：返回 `sit.info.v1` | agent 决策 evolve 前读当前状态 |
| `sit status` | 简版 info | 不推荐 agent 用（文本输出） |
| `sit validate` | VERIFY 第一层：结构 | EVOLVE 后必跑，失败即 reject |
| `sit test` / `sit test --run` | VERIFY 第二层：行为回归 | EVOLVE 后必跑，定义"是否退化" |
| `sit diff` / `sit diff <range>` | **PROPOSE 的语义载荷**：返回 risk + suggested bump + diff event 流 | agent 写 PR 时附带；reviewer agent 据此决策 |
| `sit report --format json` | VERIFY 输出可机读 `sit.report.v1` | 实验里作为 trajectory 标注 |
| `sit pr-summary --format json` | PROPOSE 包装：把 diff + risk + version 建议打成一个对象 | 多 agent 间传递的"提案对象" |
| `sit ci-summary` | GOVERN 的 CI 反馈渠道 | reviewer agent 读取 |
| `sit commit` | PROPOSE：带 version gate 的提交点 | 阻断不匹配 bump 的演化 |
| `sit release` | MERGE 后落版 + bundle + reverse-deps 告警 | 触发对下游 agent 的 broadcast |
| `sit deps check` | GOVERN：跨 skill 兼容性 | reverse-dep agent 读取 |
| `sit doctor` | GOVERN：仓库接入健康度 | 实验中作为系统级 metric |
| `git add/commit/push/pull/branch/checkout/log` | 结构性动词的底座 | FORK/PROPOSE/MERGE/REVERT 全部依赖 |

## 3. 四个实验的 readiness 评估

### 实验 1：Skill 共享效率

| 协议动作 | 实验中的对应 | sit 现状 | 必须补齐 |
|---|---|---|---|
| Baseline A 独立库 | 每个 agent 独立 git repo | git 原生 | 无 |
| Baseline B 直接覆盖 | 强制 `git push -f` | git 原生 | 无 |
| Baseline C 投票 | 实验框架自实现 voting layer | sit 之外 | voting harness（实验代码） |
| Ours：fork/evolve/propose/verify/merge | `git checkout -b` → 编辑 → `sit commit` → `git push` → reviewer agent 读 `sit pr-summary --format json` → `git merge` → `sit release` | **基本就绪** | (1) 多 agent driver 框架（实验代码）；(2) "reviewer agent" 的决策接口 |

**Readiness：高。** 6–7 成现成。补的主要是实验框架（agent loop + driver），不是 sit。

### 实验 2：Regression 恢复

| 协议动作 | 实验中的对应 | sit 现状 | 必须补齐 |
|---|---|---|---|
| 注入有害演化 | 实验 driver 在某 step 强行 merge bad PR | 实验代码 | bad-skill 注入器 |
| Baseline 无版本控制 | 直接覆盖式 skill 库 | sit 之外 | baseline harness |
| Ours: revert | `git revert <bad-sha>` + `sit release patch` | git + sit 原生 | 无 |
| 度量：blast radius | `sit deps check` 反向依赖 + 行为回归测量 | sit 已有 | 度量脚本 |

**Readiness：最高。** 这个实验最容易出强结果，建议作为 lead experiment。差距只在实验 driver。

### 实验 3：异构 Agent 知识融合

| 协议动作 | 实验中的对应 | sit 现状 | 必须补齐 |
|---|---|---|---|
| Agent A/B 各自演化 | 两个独立分支 | git 原生 | 无 |
| sit merge | `git merge` + `sit diff` 双向校验 + `sit test` 跨域验证 | git + sit 原生 | (1) 跨域 golden case 设计；(2) 冲突解决策略——sit 不自动语义 merge，需要约定 agent 解决冲突的协议 |
| 度量：知识迁移效率 | 任务成功率随 step 数 | 实验代码 | 度量脚本 |

**Readiness：中。** sit 命令够用，但"如何让两个 agent 合并各自的演化"这一步在 sit 之外，需要实验里定义合并策略（最简：A 接受 B 的所有提案过 verify gate）。

### 实验 4：Governance 的价值

| 协议动作 | 实验中的对应 | sit 现状 | 必须补齐 |
|---|---|---|---|
| No governance | 关闭 `sit commit` gate + 跳过 verify | `--no-version-gate` 已支持，verify 可跳 | 无 |
| Threshold governance | 默认 `sit commit` + `sit test` + version gate | sit 已有 | 无 |
| Full governance | 上面 + 多 agent review + 历史信用分 | sit 之外 | (1) reviewer agent；(2) **agent reputation ledger**（信用分账本） |

**Readiness：中。** 前两档现成，第三档需要在 sit 之外加 reputation ledger。建议这个 ledger 作为外部组件，不进 CLI——保持 sit 是"基础设施"，治理策略是"上层应用"。

## 4. 协议层缺什么

跨 4 个实验汇总，sit 当前为多 agent 协作准备的能力清单里只缺 4 件事，按优先级：

1. **Agent loop driver**（实验代码，不入 CLI）—— 让 agent 能循环调用 sit 命令，读 JSON 输出，决策下一步。这是所有实验的骨架。
2. **`sit pr-summary --format json` schema 稳定化**（已有，需文档化）—— 它就是 agent 间传递的"提案对象"。需要把 `sit.pr-summary.v1` schema 写进 `docs/`。
3. **Manifest 加 `status: active|deprecated|retired`**（CLI 微扩）—— 让 RETIRE 在 sit 里可观测，配合 `sit diff` 输出 retired 事件。
4. **Reputation ledger**（外部组件，不入 CLI）—— 实验 4 的 Full governance 档需要。建议放在实验仓库里，不进 sit 主仓。

**关键判断：sit 不要变成 multi-agent 框架本身，它继续做"基础设施"。** 实验代码（driver、reviewer agent、reputation ledger）放在外部，靠 sit 的 JSON 输出做接口。这样论文 method section 可以写："we don't propose a new agent algorithm; we propose an infrastructure-level coordination protocol that any agent algorithm can plug into."

## 5. 下一步

按这张表，下一轮实操的最小集合是：

1. 写 `sit.pr-summary.v1` 与 `sit.info.v1` 的 JSON schema 文档（半天工作量）
2. 用实验 2（regression 恢复）做 lead experiment：写一个 ~200 行的 Python driver，调 sit + git 命令，注入 bad PR，记录恢复曲线
3. 实验 1/3/4 在实验 2 的 driver 上扩展

完成 1+2 就可以写论文 introduction + lead result，把 sit 的"agent-native git"定位立起来。
