Motivation
多 agent 系统中 skill 的并行演化是现实需求
现有方案: 无协调 / 集中式 → 效率低 / 可扩展性差
洞察: Git 解决了人类开发者的协调问题，类似协议可解决 agent 的
贡献: 提出 sit 协议 + 实证验证
Experiment
1. Skill 共享效率
Setup:
- N 个 agent，每个独立面对不同类型的任务
- 所有 agent 共享一个 skill 库
- 训练 T 步
对比条件:
  Baseline A: 独立技能库 (每个 agent 维护自己的，不共享)
  Baseline B: 共享库 + 直接覆盖 (最后写入者胜)
  Baseline C: 共享库 + 投票选最佳版本
  Ours: 共享库 + sit 协议 (fork/evolve/propose/verify/merge)
测量指标:
- 任务成功率随时间的收敛曲线
- Skill 库的质量 (平均效用)
- Skill 库的大小 (sit 是否能有效 retire 无用 skill)
- Skill 冲突频率和解决质量
2. Regression 恢复
Setup:
- 多 agent 持续演化 skill 库
- 在某个时刻注入一个有害演化 (故意让 skill 退化)
对比:
  Baseline: 无版本控制 → 需要从头重新演化
  Ours: sit revert → 精确回滚到退化前版本
测量:
- 恢复到退化前性能所需的步数
- 退化影响的传播范围 (sit 是否能限制 blast radius)
3. 异构 Agent 知识融合
Setup:
- Agent A 擅长领域 X，Agent B 擅长领域 Y
- 存在跨领域任务需要两者的 skill
对比:
  Baseline: 两个 agent 各自的 skill 库独立，不互通
  Ours: sit merge → 将 A 的 skill 演化和 B 的 skill 演化合并
测量:
- 跨领域任务的成功率
- 知识迁移效率 (用了 sit 后，agent 多快能利用其他 agent 的发现)
4. Governance 的价值
Setup:
- N 个 agent 自由演化 skill
- 部分 agent "质量差" (会产出有害/低效 skill)
对比:
  No governance: 所有 propose 都直接 merge
  Threshold governance: verify 通过才 merge (sit 的 CI)
  Full governance: verify + 多 agent review + 历史信用分
测量:
- 库中有害 skill 的比例随时间变化
- 整体系统任务性能
Related Work
From Context to Skills: Can Language Models Learn from Context Skillfully?
https://arxiv.org/pdf/2604.27660
- Ctx2Skill，一种无需人工监督或外部反馈即可从复杂上下文中自主发现、提炼和选择特定技能的自进化框架，旨在解决语言模型在上下文学习（Context Learning）中面临的两个核心挑战：手动技能注释成本高昂与缺乏自动化技能构建所需的反馈信号。
SkillOS: Learning Skill Curation for Self-Evolving Agents【Skill, Google】
https://arxiv.org/pdf/2605.06614
- 论文提出SkillOS——一种基于经验驱动的强化学习（RL）训练方法，通过以下机制学习技能策划能力： 模块化架构：将冻结的代理执行器（Agent Executor）与可训练的技能策划器（Skill Curator）解耦，前者负责任务执行，后者通过文件I/O操作管理外部技能库（SkillRepo） 分组任务流训练：构建基于技能相关性的任务组（grouped task streams），使早期轨迹更新的技能能通过后续相关任务进行评估，提供长程学习信号 复合奖励设计：结合任务结果、函数调用有效性、技能质量和库紧凑性等多维信号，将延迟和间接的反馈转化为有效的学习信号 通过这种方式，SkillOS旨在使代理能够从经验中自动学习如何有效地策划、更新和管理技能库，从而实现真正的自我进化能力。SkillOS 将技能策划形式化为长程、以执行器为基础的学习问题，通过分组相关任务构建训练实例，并结合下游任务结果与中间奖励，将延迟且间接的反馈转化为技能策划的有效学习信号。
Skill1: Unified Evolution of Skill-Augmented Agents via Reinforcement Learning
https://arxiv.org/pdf/2605.06130
- 技能增强型智能体（skill-augmented agents）在持续技能库维护过程中面临的优化瓶颈与目标冲突问题。论文提出Skill1框架，核心贡献在于实现统一进化（unified evolution）： 训练**单一策略（single policy）同时覆盖技能选择、利用和提炼三个阶段； 基于单一任务结果信号（task-outcome signal）**分解出各阶段的学习信号：利用低频趋势（low-frequency trend）奖励选择，利用高频变化（high-frequency variation）奖励提炼，从而确保三种能力向共享目标协同优化。
SkillRet: A Large-Scale Benchmark for Skill Retrieval in LLM Agents
https://arxiv.org/pdf/2605.05726
- 论文引入了SKILLRET，一个专门用于LLM代理技能检索的大规模基准，其特点包括：规模：包含17,810个经过筛选的公共代理技能，组织成6个主要类别和18个子类别的两级分类体系。数据分割：提供63,259个训练样本和4,997个评估查询，且训练集和评估集的技能池互不相交，支持检索导向的模型训练和受控评估。现实特征：捕捉了真实检索环境的特征，包括长上下文技能文档（中位数1,583个token）和失衡的技能分布。
Group of Skills: Group-Structured Skill Retrieval for Agent Skill Libraries
https://arxiv.org/pdf/2605.06978
- GOSKILLS 将检索单位从原子技能转变为锚点中心的技能组（anchor-centered groups），通过离线图构建与在线推理生成显式执行合同。
Ace-Skill: Bootstrapping Multimodal Agents with Prioritized and Clustered Evolution
https://arxiv.org/pdf/2605.08887
- 论文提出 ACE-SKILL 框架，将计算资源分配与知识组织视为耦合优化问题，通过协同演化的方式将其转变为良性循环（virtuous cycle）： 优先采样器（Prioritized Sampler）：基于贝叶斯熟练度估计（lazy-decay proficiency tracking），主动将 rollout 资源导向信息量大且掌握不足的样本； 聚类组织器（Clustered Organizer）：通过语义聚类将知识隔离到相干的簇中，每个簇维护双粒度知识（实例级经验与类别级技能），减少检索噪声并提升任务对齐性。
Swarm Skills: A Portable, Self-Evolving Multi-Agent System Specification for Coordination Engineering
https://arxiv.org/pdf/2605.10052
- 论文提出Swarm Skills规范——首个扩展Anthropic Skills标准的多智能体语义规范，将多智能体工作流转化为具备"角色定义（Roles）、工作流（Workflow）、执行边界（Execution Bounds）"五大组件的便携资产，并内置Evolution Experience语义结构。配套提出的自进化算法通过CREATE（轨迹蒸馏）、PATCH（摩擦驱动的增量优化）和 Governance（基于E -U -F 多维评分的精简/重建/回滚）机制，实现协调协议的持续自主精炼，无需人工介入。
SkillMaster: Toward Autonomous Skill Mastery in LLM Agents
https://arxiv.org/pdf/2605.08693
- 论文提出了 SKILLMASTER 框架，通过以下机制实现技能管理的内生化和可学习化： 轨迹感知的技能审查（Trajectory-informed Skill Review）：允许智能体基于已完成 episodes 的证据，通过工具调用（tool calls）主动提议、更新或保留技能 反事实效用奖励（Counterfactual Skill Utility Reward）：通过在相关探测任务（probe tasks）上比较技能修改前后的性能差异，为技能编辑决策提供显式的质量信号 DualAdv-GRPO 优化算法：分别为任务执行动作和技能编辑决策估计独立的优势（advantages），实现异构阶段的解耦优化 该方法将技能管理从外部维护流程转变为智能体策略内部的优化问题，使 LLM 智能体从"使用技能"进化为"掌握技能"的自改进系统。
SkillEvolver: Skill Learning as a Meta-Skill
https://arxiv.org/pdf/2605.10500
- 论文提出的核心问题是：智能体能否在有限的部署时试验（deployment-time trials）内，将程序性知识获取并封装为可重用的技能制品，而无需重新训练模型权重？ 具体挑战包括： 如何在仅有少量探索试验（如4次）的条件下完成技能创作； 如何通过实际部署反馈（而非仅作者自身的反思）识别技能缺陷，包括"静默绕过"（skill appears valid but is never invoked）等部署特定故障； 如何确保学习到的技能是可迁移的制品（prose + code），可被不同智能体加载，而非嵌入模型参数的知识。为此，论文提出 SkillEvolver——一个轻量级的元技能（meta-skill）框架，通过"创作-部署-审计-精炼"的闭环，将技能学习本身视为一种技能，使标准CLI智能体能够在线完成领域特定技能的进化。
SearchSkill: Teaching LLMs to Use Search Tools with Evolving Skill Banks
https://arxiv.org/pdf/2605.09038
- LLMs在使用搜索工具时缺乏高质量的查询规划能力。论文提出SEARCHSKILL框架，通过显式的技能选择机制（skill-conditioned query planning）将搜索工具使用分解为"选择技能→执行技能"两个阶段，并维护一个可进化的技能库（SkillBank）来捕获和重用有效的搜索模式，从而将搜索行为从"无差别动作"转变为"受技能引导的显式规划"。
Dynamic Skill Lifecycle Management for Agentic Reinforcement Learning
https://arxiv.org/pdf/2605.10923
- 论文主张，技能应**根据其边际外部贡献（Marginal External Contribution, MEC）动态经历保留（Retain）、**退役（Retire）或扩展（Expand）的生命周期操作，从而在学习过程中自适应地确定模型参数与外部模块化技能之间的最优能力边界，而非强制走向完全积累或零技能推理的终点。
Skill-R1: Agent Skill Evolution via Reinforcement Learning
https://arxiv.org/pdf/2605.09359
- Skill-R1 将技能演化形式化为基于可验证奖励的双层强化学习问题，通过冻结任务模型与训练轻量级技能生成器的解耦架构，实现了对开源与闭源模型均兼容的实例级递归优化。实验表明，该方法在多步推理与工具使用任务上显著优于传统方法，为智能体技能的高效进化提供了可扩展的替代方案。
SkillGen: Verified Inference-Time Agent Skill Synthesis
https://arxiv.org/pdf/2605.10999
- 论文提出 SKILLGEN，一个多智能体框架，其核心创新包括： 对比行为归纳（Contrastive Behavioral Induction）：通过对比成功与失败轨迹，提取可复用的成功模式、识别反复出现的失败模式，并发现"邻近成功案例中存在但失败案例中缺失"的关键行为。 干预式验证（Interventional Verification）：将技能建模为对基线智能体的干预，通过在验证子集上计算修复数（repairs）与回归数（regressions）之差 Gm(s)=n01(s)−n10(s) ，实证验证技能的净效应。 生成-验证-精炼循环（Generation-Verification-Refinement Loop）：迭代生成候选技能，基于结构化反馈（保留/移除/添加/强调）进行精炼，并通过验证门（verification gate）仅部署具有正净效应的技能。 简言之，该论文将技能合成重新定义为基于对比归纳的干预优化问题，确保生成的技能不仅是轨迹的总结，而是经过实证验证、能够提升整体性能的可审计人工制品。
MMSkills: Towards Multimodal Skills for General Visual Agents
https://arxiv.org/pdf/2605.13527
- 解决视觉智能体（Visual Agents）缺乏有效的多模态程序性知识表示与利用机制的问题。现有技能系统主要将可重用行为编码为文本提示、代码或学习例程，难以满足视觉决策中对视觉证据的依赖。提出MMSkill包结构，包含：可重用文本程序（P）运行时状态卡片（S，包含何时使用/不使用、可见线索、验证线索）多视角关键帧（K，包含全帧、聚焦裁剪、前后对比视图）。
SkillFlow: Flow-Driven Recursive Skill Evolution for Agentic Orchestration
https://arxiv.org/pdf/2605.14089
- 论文提出SkillFlow框架，其核心贡献包括： 采用Tempered Trajectory Balance (TTB)损失函数，实现与奖励成比例的轨迹采样（reward-proportional sampling），保留多样化的编排策略而非坍缩到单一模式； 联合学习反向策略（backward policy），在零额外推理成本下提供透明的逐步信用分配（per-step credit assignment）； 基于流诊断（flow diagnostics）的递归技能进化机制，从训练信号本身直接推导何时进化、进化什么技能以及缺口位于何处，形成从训练信号到自主能力增长的闭环。
SkillSmith: Compiling Agent Skills into Boundary-Guided Runtime Interfaces
https://arxiv.org/pdf/2605.15215
- 论文提出了SkillSmith，一个边界优先的编译器-运行时框架（boundary-first compiler-runtime framework）。该框架通过离线将技能包编译为最小可执行接口（minimal executable interfaces），提取细粒度的操作边界（operational boundaries），使智能体能够在运行时动态访问和执行仅相关的组件，从而最小化不必要的上下文注入和冗余推理开销。