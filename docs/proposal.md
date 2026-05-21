# SitHub Proposal

> Working title: **SitHub: Agent-Native Version Control for Multi-Agent Skill Coordination**
> Date: 2026-05-20
> Status: 初稿，待 PI / 合作者评审

## 1. 一句话定位

`sit` 是 agent-native 的 git。当多个 agent 并行演化同一个共享 skill 库时，sit 让它们像人类开发者用 git 协作一样可观测、可验证、可回滚、可治理。

## 2. 研究动机

### 2.1 Skill 已成 agent 系统的一等资产

随着 agent 系统的成熟，**skill** 正在从"一段 prompt"演变为 prompt + schema + runner + golden test 的复合制品，成为 agent 系统真正可复用、可交付、可演化的最小单元。它在 agent 生态里扮演的角色，正对应人类软件开发中的"代码模块"或"library"。

skill 库 = agent 的代码仓库。这是本工作的起点。

### 2.2 单 agent 视角的问题已经被广泛研究

围绕**单个 agent 如何管理自己的 skill 库**，研究界已经形成了相对完整的工作面：

- 何时创建、更新、退役 skill 的策略
- 如何检索、组织、调度 skill
- 如何从轨迹中合成与验证 skill
- 如何把 skill 编译为运行时接口

这些工作的共同点：**决策主体是单 agent，对象是它私有的 skill bank**。它们解决的是 intra-agent skill curation 问题。

### 2.3 真正的空位：inter-agent skill coordination

而当多个 agent 同时演化同一个共享 skill 库时，一组新的问题浮现，它们的本质不是"agent 怎么学得更好"，而是"agent 之间怎么协作不出错"：


| 问题                                           | 本质           |
| -------------------------------------------- | ------------ |
| Agent A 修改了某 skill，Agent B 还在用旧版——怎么不让 B 静默崩 | 版本兼容         |
| 两个 agent 同时改同一个 skill 的不同字段，但语义冲突——怎么早发现     | 语义 diff      |
| 某次自演化引入坏 skill 污染下游——怎么定位、回滚、限制传播            | 历史与依赖        |
| 异构 agent 各自演化出有用的局部 skill——怎么合并              | fork / merge |
| 部分 agent 质量差会产出有害 skill——怎么治理                | governance   |


这些都不是 agent 算法层面的问题，而是**协作基础设施层面的问题**。

### 2.4 类比：人类软件开发的解法

人类开发者面临过完全同构的问题，并用大约三十年时间形成共识：版本控制系统（git）+ 协作平台（GitHub / GitLab）+ 持续集成（CI）+ 评审制度（PR review）。这套基础设施不解决"程序员怎么写得更好"，但它让任意写代码方法在多人协作时都能稳定运行。

agent 时代缺的就是这一层。本工作要回答的核心问题是：

> **能否为多 agent skill 协作构造一套类比 git/GitHub 的基础设施，使之像人类协作一样高效、可控？**

### 2.5 核心论点

`sit` 协议（FORK / EVOLVE / PROPOSE / VERIFY / MERGE / REVERT / RETIRE / GOVERN）是这套基础设施的最小实现。它的差异化在于**与具体 agent 算法正交**——任何 intra-agent skill 算法接入 sit 仓库，都自动获得版本历史、语义 diff、行为回归 gate、回滚、依赖追踪、PR/CI 反馈。本研究的目标是**实证证明这种基础设施对多 agent 系统有效，并量化其收益**。

## 3. 研究假设

提出 4 个可证伪假设：

- **H1（共享效率）**：在 N 个并行 agent 演化共享 skill 库的设定下，sit 协议（fork/evolve/propose/verify/merge）相对于无版本控制 / 直接覆盖 / 投票等协作策略，能在更少 agent-step 内达到相同任务成功率。
- **H2（恢复能力）**：当向 skill 库注入有害演化时，sit 能在 O(1) 步内回滚（git revert + sit release），相比无版本控制的"重新演化"（需 O(T) 步），恢复时间和受影响 skill 数量都显著降低。
- **H3（异构融合）**：当 Agent A、Agent B 各自在不同领域演化出有用 skill 时，通过 sit merge + verify gate 合并两条演化线，跨域任务成功率显著高于二者独立运行或直接拼接。
- **H4（治理价值）**：当部分 agent 质量较差时，sit 的 verify gate（结构 + 行为）+ 多 agent review 能有效压制有害 skill 比例，整体系统性能优于无 governance baseline，且不会因审查严格度过高显著降低吞吐。

## 4. 主要贡献

1. **问题定义**：把 multi-agent skill 协作形式化为一个控制系统问题，给出对应的协议动词集（FORK / EVOLVE / PROPOSE / VERIFY / MERGE / REVERT / RETIRE / GOVERN），并证明它们都能由 git 原语 + sit 语义层实现。
2. **基础设施实现**：开源 `sit` CLI 第一版（已有：14 条命令、5,478 行 Python、52 个单元测试），覆盖 80% 协议动词；提供 multi-agent driver 框架，使任意 agent 算法可接入。
3. **实证验证**：在 4 个 multi-agent 实验中验证 4 个假设，给出 baseline 对比、收敛曲线和度量分析。
4. **正交性论证**：明确 sit 与 intra-agent skill 算法的关系——sit 是基础设施，agent 算法是上层应用，二者可叠加使用。

## 5. 实验设计

### 5.1 通用实验框架

- **N 个 agent**：每个 agent = 一个 LLM + 一个本地 skill 缓存 + 一个调 sit/git 的 driver。
- **共享 skill 库**：一个中央 git repo，结构遵循 sit 的 Skill Package（`skill.yaml` + `prompts/` + `schemas/` + `tests/` + `scripts/`）。
- **任务流**：从公开 benchmark 抽样 + 自构造的 multi-version skill 任务流（基于已有试点 `paper-webpage-builder`）。每个 agent 在每个 step 收到一个任务，决定（a）用现有 skill 解决，还是（b）演化新 skill。
- **训练步数**：T = 1000 step，N ∈ {2, 4, 8}。
- **重复次数**：每个 condition 重复 5 个 random seed。

### 5.2 实验顺序与就绪度（按 `docs/sit-multi-agent-mapping.md` 评估）


| 顺序  | 实验               | 就绪度                        | 主要风险                      |
| --- | ---------------- | -------------------------- | ------------------------- |
| 1   | H2 Regression 恢复 | 最高，sit 命令 100% 现成          | bad-skill 注入器需构造，工作量小     |
| 2   | H1 共享效率          | 高，需补 multi-agent driver 框架 | baseline 选择需谨慎            |
| 3   | H3 异构融合          | 中，需约定冲突解决协议                | 跨域任务的 golden case 设计需谨慎   |
| 4   | H4 治理价值          | 中，需外部 reputation ledger    | "agent 质量差"如何量化定义需 ablate |


### 5.3 实验 1（H2，lead）：Regression 恢复

**Setup**：N=4 agent 持续演化 skill 库 200 step。在 step 100 时，driver 强制 merge 一个有害 PR（让某 skill 输出退化 30%）。观察后续步骤里：

- 系统多久检测到性能退化（首次 verify gate 失败 / 任务成功率明显下降）
- 系统多快恢复到退化前性能

**对比**：

- **NoVC**：skill 库直接覆盖，无历史。检测到退化后只能等 agent 重新演化覆盖坏 skill。
- **PeriodicSnap**：每 50 step 全量快照。检测到退化后回滚到最近快照（粗粒度）。
- **Ours-sit**：`git revert <bad-sha>` + `sit release patch`，精确回滚单个 skill；`sit deps check` 反向依赖告警限制 blast radius。

**度量**：

- 恢复步数（detection step + recovery step）
- 受影响 skill 数（blast radius，按 `sit deps check` 反向依赖图）
- 恢复后任务成功率与退化前 baseline 的差距

**预期**：Ours-sit 恢复步数比 NoVC 低 1–2 个数量级；blast radius 受 reverse-deps 限制后压缩 ≥50%。

### 5.4 实验 2（H1）：Skill 共享效率

**Setup**：N=4 agent，每个面向不同任务子分布。所有 agent 共享一个 skill 库，演化 1000 step。

**对比**：

- **Iso**：每 agent 自己的 git repo，不共享。
- **Overwrite**：共享 git repo，最后写入者胜，无 verify。
- **Vote**：共享库 + 简单 majority vote 选最佳版本。
- **Curator**：共享库 + 一个集中式 curator 模块，模拟"已有 intra-agent skill curation 算法套到多 agent"的效果。
- **Ours-sit**：fork → evolve → propose → verify → merge。

**度量**：

- 任务成功率随 step 的收敛曲线
- skill 库平均效用（每个 skill 被调用次数 × 成功率）
- skill 库大小（验证 sit 是否能有效 retire 无用 skill）
- 冲突频率与解决耗时

**预期**：Ours 的收敛曲线在所有 baseline 之上；库大小相对 Overwrite/Vote 更紧凑（因为 retire 更精确）。

### 5.5 实验 3（H3）：异构 agent 知识融合

**Setup**：Agent A 训练在领域 X 任务，Agent B 训练在领域 Y 任务，各自演化 500 step。然后引入 50 个跨域任务。

**对比**：

- **Iso**：A、B 库独立。
- **Concat**：直接拼接 A、B 的 skill 库，无 verify。
- **Ours-sit-merge**：把 A、B 的演化线 git merge，过 sit verify gate，冲突由 reviewer agent 解决。

**度量**：

- 跨域任务成功率
- 知识迁移效率（用了 sit 后多少 step 内 A 能利用 B 的发现）
- merge 冲突数量与自动 / 手动解决比例

**预期**：sit-merge 显著优于 Iso；与 Concat 相比，verify gate 能压制不兼容 skill 进入合并库。

### 5.6 实验 4（H4）：治理价值

**Setup**：N=8 agent，其中 m ∈ {0, 2, 4} 个 agent 被注入"质量差"（产出有害 skill 的概率提升）。演化 1000 step。

**对比**：

- **No-gov**：所有 propose 直接 merge。
- **Threshold-gov**：sit 的 verify gate（validate + test）。
- **Full-gov**：verify gate + multi-agent review + reputation ledger（外部组件，按提案历史成功率给 agent 权重）。

**度量**：

- 库中有害 skill 比例随 step 变化
- 整体系统任务成功率
- 治理开销（每个 propose 平均通过时间）

**预期**：Threshold-gov 把有害 skill 比例从 No-gov 显著压低；Full-gov 进一步下降但治理开销上升 1.5–2x，给出一条 Pareto 前沿。

## 6. Baseline 设计原则

每个实验的 baseline 集合按"由弱到强"排布，避免单一弱 baseline 带来的 strawman 风险：


| 实验      | 弱 baseline             | 强 baseline                                               |
| ------- | ---------------------- | -------------------------------------------------------- |
| H1 共享效率 | Iso / Overwrite / Vote | 集中式 Curator（代表已有 intra-agent skill curation 思路套到多 agent） |
| H2 恢复   | NoVC                   | PeriodicSnap（系统层常规做法）                                    |
| H3 融合   | Iso                    | Concat + 单 agent 检索                                      |
| H4 治理   | No-gov                 | Threshold-gov（sit 自身的中间档）                                |


强 baseline 的目的：证明 sit 不仅相对玩具 baseline 有提升，相对工程上合理的常规方案、相对沿用 intra-agent 思路的拓展方案，也能展现协作基础设施的独立价值。

## 7. 度量体系

定义三个一阶度量贯穿四个实验：

- **样本效率**：达到目标任务成功率所需 agent-step。
- **协调成本**：单位 skill 演化的冲突 / 回滚 / 重做次数。
- **库质量**：Pareto 前沿（库大小 vs 任务覆盖率 vs 平均 skill 效用）。

二阶度量按实验定制（恢复步数、blast radius、跨域成功率、有害 skill 比例）。

## 8. 实施计划

按 `docs/sit-multi-agent-mapping.md` 第 5 节路线，分三阶段：

**阶段 1（2 周）：基础设施完备化**

- 写 `sit.pr-summary.v1` / `sit.info.v1` / `sit.report.v1` 的 JSON schema 文档
- manifest 增加 `status: active|deprecated|retired` 字段，`sit diff` 输出对应事件
- 实现 multi-agent driver 框架（~500 行 Python）：agent loop + git/sit 命令调度 + JSON 解析

**阶段 2（3 周）：跑实验 1（H2 lead）**

- 构造 bad-skill 注入器
- 跑 H2 三种 condition × 5 seed
- 出第一张恢复曲线图

**阶段 3（4 周）：跑实验 2、3、4**

- 在阶段 2 driver 上扩展实验 1（H1）：加 Curator baseline
- 实验 3（H3）：加冲突解决 reviewer agent
- 实验 4（H4）：实现 reputation ledger 外部组件

总时长约 9 周到首版完整结果。

## 9. 风险与限制


| 风险                                            | 应对                                                 |
| --------------------------------------------- | -------------------------------------------------- |
| 任务流 benchmark 不够稳定，影响所有曲线                     | 自构造 paper-webpage-builder 多版本任务流作 sanity check     |
| LLM 调用预算                                      | 每个实验 condition × seed 控制在 ≤10k LLM 调用，总预算约 500k 调用 |
| 实验 4 reputation ledger 的具体形式有多种选择             | 在论文中以 ablation 呈现，不押注单一实现                          |
| sit 当前的 `sit diff` 只解析本地 `$ref`，可能遗漏跨文件依赖     | 实验 skill 库统一用 inline schema，避免触发该限制                |
| sit 不做语义 merge，merge 冲突依赖 git 文本冲突 + agent 解决 | H3 中明确把"冲突解决"作为 sub-protocol 测量                    |


## 10. 研究边界

- 不提出新 LLM / 新 agent 算法。
- 不与具体 intra-agent skill curation 方法做"谁的 curation 更强"的正面对比——它们解决的是 intra-agent 问题，与 sit 正交，可叠加使用。
- 不实现 SitHub Web 平台。Web 层是后续工作，本研究只到 CLI + driver 协议。
- 不解决多模态 skill 的版本控制问题。

## 11. 交付物

- 论文初稿（含 4 张曲线图 + 1 张协议-CLI 映射表）
- 开源 `sit` CLI（已有，公开仓库 `OpenRaiser/SitHub`）
- 开源 multi-agent driver + 实验代码
- 公开的 paper-webpage-builder 多版本任务流作为 reproducible benchmark

## 12. 与现有材料的对接


| 内部文档                              | 对接点                                                   |
| --------------------------------- | ----------------------------------------------------- |
| `docs/plan.md`                    | 现有实验骨架与初步相关工作梳理；本提案在其上补强 motivation、baseline 与 metric |
| `docs/sit-multi-agent-mapping.md` | 第 4 节"主要贡献"和第 5 节"实验顺序"直接引用                           |
| `00_项目枢纽.md`                      | sit CLI 当前状态、F1–F13 已完成基线在 system 章节复用                |
| `reports/project_report.md`       | 系统架构图、代码规模、试点证据复用到论文 method/system 章节                 |


## 13. 相关工作（占位）

相关工作分两层组织，**待论文撰写阶段做完整 literature review 后填充**：

- **第一层 — 单 agent skill 管理**：涵盖 intra-agent 视角下 skill 的合成、检索、验证、生命周期管理等方向。本工作与之正交：sit 是基础设施，不替代任何具体算法；任意此类算法接入 sit 仓库后均可受益。
- **第二层 — 多 agent 协作与协调**：涵盖 multi-agent 系统、agent 通信协议、知识共享、shared memory 等方向。本工作的差异化在于以**版本控制基础设施**而非"通信协议 / 共享内存"的范式切入，借鉴人类软件协作（git/GitHub/CI/PR review）的成熟设计经验。

注：当前列在 `docs/plan.md` 中的论文集合仅为初步样本，最终 related work 需要扩展到分布式版本控制系统、software engineering for ML、multi-agent reinforcement learning 协调机制等更广领域。