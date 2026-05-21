# skill git

## 🧑‍💻 User

我觉得skill需要做版本控制+团队协作，需要搞一套它的git

---
## 🤖 Assistant

# Skill 版本控制 + 协作系统：设计空间分析

## 核心论点的合理性

这个想法是成立的。Skill（无论是 AI agent skill、RPA skill、还是 low-code 模块）本质上是一种**结构化的可执行知识资产**，它具备：

- 多人共同迭代
- 需要回滚
- 存在分支实验
- 有依赖关系
- 需要 review/审批流程
- 有发布（publish）vs 草稿（draft）的生命周期

这些特征与代码几乎完全同构，所以"给它搞一套 git"是自然的推导。

---

## 但 Skill ≠ 代码：差异点决定了你不能直接用 Git

| 维度 | 代码 (Git 原生对象) | Skill |
|------|---------------------|-------|
| 存储格式 | 纯文本行 | 结构化对象（JSON/YAML + 嵌套资源：prompt、schema、config、连接器引用） |
| Diff 粒度 | 行级 | 语义级（改了一个 slot 的类型 vs 改了整段 prompt 的意图） |
| Merge 冲突 | 文本冲突 → 人解决 | 结构冲突（两人各加了同名参数但类型不同）+ 语义冲突（两个 prompt 版本在行为上矛盾） |
| 依赖 | import/package.json | 其他 skill、外部 API、模型版本、知识库版本 |
| 测试/验证 | CI 跑 test | 需要 sandbox 执行 + 可能需要 LLM 评估 |
| 用户群体 | 开发者（熟悉 CLI） | 可能包含非技术人员（PM、运营、领域专家） |
| 发布语义 | tag/release | 可能需要灰度、A/B、按租户分发 |

**关键推论**：你需要的不是 "Git for Skill"，而是 **"Git 语义 + 结构化对象感知 + 非技术者可用的 UI + 领域特定 diff/merge"**。

---

## 架构设计空间

### 层级一：存储层（对应 Git Object Store）

```
Option A: 底层直接用 Git
  - Skill 序列化为文件树（skill.yaml + prompts/ + schema/ + tests/）
  - 用 Git 做版本存储
  - 上层包装 UI
  - 优点：免费拿到 branch/merge/history 全套
  - 缺点：merge 冲突处理对非技术用户灾难性体验；大二进制资产（嵌入的知识库切片）不适合 Git

Option B: 自建版本化对象存储
  - 每个 Skill 版本是 immutable snapshot（content-addressed，类似 Git blob）
  - DAG 结构记录历史
  - 结构化 diff 引擎自己写
  - 优点：完全控制 diff/merge 语义
  - 缺点：重造轮子成本高

Option C: Git 底层 + 自定义 merge driver + 语义 diff 层
  - 用 Git 存储但注册 custom diff/merge driver
  - UI 层展示结构化 diff 而非行级 diff
  - 这是实际最务实的路线（Terraform、Kubernetes manifest 生态走的路）
```

### 层级二：协作层（对应 GitHub/GitLab）

| 功能 | 对应的 Skill 语义 |
|------|-------------------|
| Branch | Skill 变体 / 实验版 |
| Pull Request | Skill 变更提案（附带测试结果、行为对比） |
| Code Review | Prompt review、参数 schema review、权限变更审批 |
| CI/CD | Skill 自动化测试（sandbox 执行、golden-set 评估、regression check） |
| Release/Tag | 发布版本号，可被其他 skill 依赖 |
| Fork | 基于别人的 skill 派生自己的版本 |
| Blame | 谁在什么时候改了这段 prompt |
| Revert | 回滚到上一个稳定版 |

### 层级三：治理层（Git 生态薄弱但 Skill 需要的）

- **权限模型**：谁能编辑 prompt？谁能改 schema？谁能发布？（比 Git 的 CODEOWNERS 更细粒度）
- **审计合规**：每次变更的 reason、关联的 issue/ticket
- **依赖图谱**：Skill A 依赖 Skill B v2.3，B 升级到 v3.0 时 A 的维护者收到通知
- **运行时绑定**：版本控制的是定义，但部署环境可能 pin 不同版本

---

## 语义 Diff 的核心难题

这是整套系统最有技术深度的部分：

### 结构化 Diff

```yaml
# v1
parameters:
  - name: location
    type: string
    required: true

# v2
parameters:
  - name: location
    type: object
    properties:
      city: string
      country: string
    required: true
  - name: date_range
    type: string
    required: false
```

行级 diff 会显示一堆绿红行。你需要的语义 diff 是：
- `location` 类型从 `string` 变为 `object`（⚠️ breaking change）
- 新增可选参数 `date_range`（non-breaking）

### Prompt Diff（更难）

```
# v1
你是一个旅行助手，帮用户规划行程。

# v2
你是一个资深旅行顾问，帮用户规划详细行程，注重预算控制。
```

行级 diff 能看到文字变化，但**行为变化**是什么？这里可能需要：
- LLM 辅助的 "behavior diff" 描述（"新版本会更关注预算，回答会更详细"）
- 对 golden test set 跑两个版本的输出对比
- 类似 visual regression testing 的 "semantic regression testing"

---

## 先例与参考系统

| 系统 | 做了什么 | 可借鉴 |
|------|----------|--------|
| **Terraform** | 基础设施即代码的 plan/apply + state versioning | 声明式对象的 diff 展示、plan preview |
| **Figma** | 设计文件的版本历史 + 多人协作 | 非文本资产的分支/版本 UI、非技术者友好 |
| **dbt** | SQL 模型的版本控制 + DAG | 依赖图可视化、变更影响分析 |
| **Weights & Biases / MLflow** | 模型实验追踪 | 实验分支、metric 对比、artifact 版本化 |
| **Notion / Confluence** | 文档版本历史 | 非技术者的版本 UI（但太弱，没有真正的 branch/merge） |
| **Retool / Appsmith** | Low-code 应用版本控制 | 结构化 UI 组件的 Git 集成 |
| **PromptLayer / Humanloop / LangSmith** | Prompt 版本管理 | Prompt 的 A/B、评估、版本历史 |

**最接近你想法的现有产品**：Humanloop / PromptLayer 已经在做 prompt 级别的版本控制，但它们：
- 只管 prompt，不管整个 skill（含 schema、工具链、编排逻辑）
- 协作模型弱（没有真正的 branch/merge/PR）
- 没有依赖管理

---

## 如果你要做这件事：路线图建议

### Phase 0：最小验证
- Skill 定义序列化为 YAML/JSON 文件树
- 直接用 Git 仓库 + GitHub PR 流程
- 手写一个 CLI 做 `skill diff`（结构化输出）
- 验证：团队是否真的在用 branch/PR？冲突频率如何？

### Phase 1：可用产品
- Web UI 包装 Git 操作（非技术者不碰 CLI）
- 结构化 diff 视图（参数变更、prompt 变更、连接器变更分面展示）
- 基础 CI：每次 PR 跑 golden-set 测试
- 发布/回滚一键操作

### Phase 2：差异化
- LLM 辅助的 behavior diff（"这次修改可能导致回答更简短"）
- 依赖图 + breaking change 检测
- Skill marketplace 上的 fork/contribute-back 流程
- 多环境部署（dev/staging/prod）绑定不同版本

### Phase 3：生态
- Skill package registry（类 npm）
- Semantic versioning 自动判定（根据 schema 变更自动 bump major/minor/patch）
- 跨组织协作（开源 skill 生态）

---

## 开放性问题 / 你需要明确的设计决策

1. **Skill 的粒度是什么？** 一个函数级别？一个 agent 级别？一个多步编排级别？粒度决定了版本控制的原子单位。

2. **用户是谁？** 如果是开发者 → 可以激进用 Git；如果包含非技术人员 → 需要 Figma 级别的 UX 抽象。

3. **Merge 策略？** 结构化对象的 merge 是否可以做到自动？还是所有冲突都需要人工裁决？（大概率需要领域感知的 auto-merge 规则）

4. **运行时版本绑定？** 是「最新发布版自动生效」还是「消费者显式 pin 版本」？这影响 breaking change 的传播模型。

5. **测试的 ground truth 是什么？** 代码有 assertion，Skill 的 "正确性" 标准是什么？golden output？人工评分？metric 阈值？

---

## 一句话总结

你的直觉是对的——Skill 作为知识资产需要版本控制和协作。但执行上，核心壁垒不在 "存历史"（Git 能做），而在 **语义 diff、非技术者 UX、行为回归测试** 这三件事上。谁先把这三件事做到好用，谁就是 Skill 领域的 GitHub。

---
## 🧑‍💻 User

能不能找几个例子给我讲讲，最好是AI科研场景或AI教育场景

---
## 🤖 Assistant

# Skill 版本控制在 AI 科研 / AI 教育场景的具体例子

---

## 例子一：AI 科研 — 多人协作的论文阅读与综述 Agent Skill

### 场景设定

一个 NLP 实验室（5人团队）在做大模型安全方向的 survey。他们构建了一套 Agent Skill 体系：

```
skill: paper_reader
  ├── pdf_parser         （提取论文结构）
  ├── claim_extractor    （提取核心论断）
  ├── method_summarizer  （总结方法论）
  ├── taxonomy_mapper    （将论文归入分类体系）
  └── contradiction_finder（发现论文间矛盾观点）
```

### 为什么需要版本控制

**场景 A：分类体系迭代**

- 第 1 周：博士生 A 定义了 taxonomy_mapper 的分类体系 v1（按攻击类型分：injection, jailbreak, data poisoning）
- 第 2 周：博士生 B 读了 20 篇新论文，发现需要加一层维度（按防御阶段分：pre-training, fine-tuning, inference-time）
- 第 3 周：导师 review 后觉得 B 的分类体系在某个子类上过细，要求合并 A 和 B 的版本

**没有版本控制时的灾难：**
- B 直接覆盖了 A 的 prompt，A 之前跑的 200 篇论文的分类结果和当前 skill 对不上了
- 导师说"回到上周三的那版"，没人记得上周三是什么样
- taxonomy 的 schema 变了，下游的 contradiction_finder 依赖旧 schema 的字段名，静默失败

**有版本控制时的工作流：**

```
main ──────────────────────────────────────── v1.0 (published)
  │
  ├── branch: bo-add-defense-stage-dim ────── PR #3
  │     commit 1: 添加 defense_stage 维度
  │     commit 2: 调整 prompt 处理多标签情况
  │     commit 3: 补充 5 条 golden test cases
  │     
  │     [CI]: 对 50 篇已标注论文跑 regression
  │     [Review]: 导师 comment "adversarial training 应该归到 fine-tuning 而非 pre-training"
  │     
  └── merge → main v1.1
        │
        [自动通知]: contradiction_finder 维护者收到依赖变更通知
        [breaking change 检测]: taxonomy schema 新增字段，non-breaking（向后兼容）
```

### 语义 Diff 示例

```diff
# taxonomy_mapper prompt diff (v1.0 → v1.1)

  你是一个AI安全论文分类专家。
  请将论文归入以下分类体系：
  
  ## 攻击类型维度
  - prompt_injection
  - jailbreak
  - data_poisoning
  - model_stealing
  
+ ## 防御阶段维度
+ - pre_training（数据清洗、对齐数据策展）
+ - fine_tuning（RLHF、adversarial training、safety fine-tuning）
+ - inference_time（过滤器、guardrails、constrained decoding）
+
  输出格式：JSON
```

**行为 Diff（LLM 生成的摘要）：**
> 新版本会为每篇论文额外输出 `defense_stage` 字段。对纯攻击论文，该字段为 null。对防御论文，可能输出多个阶段标签。预期影响：输出 token 数增加约 15%，分类延迟增加约 0.3s/篇。

---

## 例子二：AI 科研 — 实验 Prompt 的 A/B 分支管理

### 场景设定

一个做 LLM-as-Judge 研究的团队，核心 skill 是 `evaluation_judge`：用 GPT-4 对模型输出打分。

### 版本控制解决的问题

研究员 C 有个假设：在 judge prompt 中加入 chain-of-thought 要求会提高评分一致性。但他不确定，需要同时保留两个版本对比。

```
main (v2.1) ─── 当前线上版，团队所有人日常用
  │
  ├── branch: cot-judge-experiment
  │     修改: prompt 末尾加 "请先逐步分析再给分"
  │     修改: output schema 增加 reasoning 字段
  │     测试: 对 500 条人工标注样本跑两个版本
  │     结果: Cohen's Kappa 从 0.72 → 0.78 ✓
  │     
  ├── branch: rubric-detailed-v2
  │     修改: 将 "fluency" 评分标准从 1 段扩展为 5 段（每个分数一段描述）
  │     测试: 同样 500 条
  │     结果: Kappa 0.72 → 0.74，但 token 消耗 +40%
  │
  └── 团队会议决定: merge cot-judge, 不 merge rubric-detailed
```

**关键点**：如果没有分支管理，C 改了 prompt 跑完实验，D 同时在改评分标准，两人互相覆盖。更糟的是——实验论文里需要报告"我们用的 judge prompt 具体是哪个版本"，没有版本号就无法复现。

### 这里版本控制还解决了科研可复现性

```yaml
# experiment_config.yaml (提交到论文 repo)
judge_skill: evaluation_judge@v2.1-cot  # 精确 pin 版本
model_under_test: llama-3-70b
dataset: mt-bench-v1.0
date: 2024-11-15
```

**任何人拿到这个配置 + skill 版本号，就能精确复现实验结果。**

---

## 例子三：AI 教育 — 自适应教学 Skill 的多教师协作

### 场景设定

一个在线教育平台，用 AI tutor 教高中物理。核心 skill 体系：

```
skill: physics_tutor
  ├── concept_explainer      （解释概念）
  ├── misconception_detector （检测学生误解）
  ├── problem_scaffolder     （分步引导解题）
  ├── difficulty_adjuster    （动态调整难度）
  └── socratic_questioner    （苏格拉底式提问）
```

### 协作场景

**参与者：**
- 物理教师 A（10年教龄，擅长力学）
- 物理教师 B（5年教龄，擅长电磁学）
- 教学设计师 C（非物理背景，负责教学法）
- AI 工程师 D（负责 skill 技术实现）

**冲突场景举例：**

教师 A 修改了 `concept_explainer` 的 prompt，要求解释牛顿第三定律时先举"推墙"的例子：

```yaml
# 教师 A 的修改
examples_strategy: "先给日常生活实例（推墙感受反作用力），再给抽象表述"
```

同时，教学设计师 C 修改了同一个 skill 的教学策略层：

```yaml
# 教学设计师 C 的修改
pedagogy: "先给出抽象定义，再让学生自己举例（建构主义路线）"
```

**这是一个语义冲突**——不是文本格式冲突，而是教学理念冲突。Git 的 text merge 不会报冲突（因为改的是不同字段），但行为上完全矛盾。

**你需要的系统应该：**
1. 检测到 `examples_strategy` 和 `pedagogy` 存在语义耦合（都影响解释顺序）
2. 自动触发 review 流程，标记为"教学策略冲突"
3. 让教研组长（人类）决策

### 版本分支用于 A/B 教学实验

```
main ─── 所有学生默认使用
  │
  ├── branch: constructivist-v1 （建构主义路线）
  │     分配给: 随机 30% 学生
  │     追踪指标: 概念理解测试得分、学生参与度、提问次数
  │
  ├── branch: direct-instruction-v1 （直接教学路线）
  │     分配给: 随机 30% 学生
  │     追踪指标: 同上
  │
  └── 4 周后数据分析 → merge 胜出版本到 main
```

**这本质上是教学实验的版本化管理**，和科研中的实验管理同构。

---

## 例子四：AI 教育 — 题目生成 Skill 的质量回归

### 场景设定

`problem_generator` skill 根据知识点自动出题。

### 灾难性回归案例（没有版本控制时真实发生的）

```
时间线:
Day 1: skill 正常，生成的力学题目难度适中
Day 3: 工程师 D "优化"了 prompt，加了一句"确保题目有区分度"
Day 5: 教师发现学生大量投诉"题目太难了"
Day 7: 没人记得 Day 3 改了什么，因为中间还有两次其他修改
Day 10: 终于定位问题，但回滚后发现 Day 4 的修改（加了答案格式约束）也丢了
```

**有版本控制 + CI 的世界：**

```
commit abc123: "加区分度要求" by 工程师 D
  │
  [CI 自动跑]: 用 100 道已标注难度的参考题做 regression
  [结果]: 平均难度从 3.2/5 飙升到 4.6/5 ❌ 超出阈值
  [自动 block]: PR 无法 merge，通知教师 review
  
教师 A review: "区分度的表述要改，应该说'适合中等水平学生，但允许有一道提高题'"
  │
  commit def456: 修改表述 → CI 通过（难度 3.4/5 ✓）→ merge
```

---

## 例子五：AI 科研 — 多模态数据标注 Skill 的跨团队共享

### 场景设定

一个大学有三个课题组都在做多模态大模型研究：
- 课题组 X：做医学影像 + 报告理解
- 课题组 Y：做遥感图像 + 文字描述
- 课题组 Z：做视频 + 字幕对齐

他们都需要一个 `image_description_evaluator` skill 来评估生成描述的质量。

### Fork + 贡献回主干的工作流

```
[校级 skill registry]

image_description_evaluator@v1.0  (通用版)
  │
  ├── fork by 课题组 X → medical_image_eval@v1.0
  │     修改: 加入医学术语准确性评估维度
  │     修改: 加入解剖位置一致性检查
  │     独有 golden set: 放射科报告标注
  │
  ├── fork by 课题组 Y → remote_sensing_eval@v1.0
  │     修改: 加入空间关系描述准确性
  │     修改: 加入比例尺/方向一致性
  │
  └── 课题组 X 发现自己写的"描述完整性评估"维度是通用的
        │
        └── Pull Request → 主干 image_description_evaluator
              [review by 课题组 Y, Z]: "这个维度对我们也有用" ✓
              merge → v1.1
```

**这就是 Skill 版本的开源协作模型**——和 GitHub 上 fork → PR → merge 完全同构，但对象是 prompt + schema + test set 而非代码。

---

## 例子六：AI 教育 — 学生自己的 Skill 作为学习成果物

### 场景设定（这个角度比较新颖）

一门"AI 应用设计"课程，作业是让学生构建自己的 Skill。

```
课程结构:
Week 1-2: 个人开发 → 每个学生有自己的 skill repo
Week 3-4: 组队协作 → 团队 fork + 集成
Week 5: 互评 → 其他组 review 你的 PR
Week 6: 整合为班级 skill library
```

### 需要版本控制的教学理由

| 教学需求 | 版本控制能力 |
|----------|-------------|
| 教师查看学生迭代过程 | commit history（比只交最终版更能评估学习过程） |
| 学生互评 | PR + review comment |
| 抄袭检测 | diff 对比 + 时间线分析 |
| 优秀作品沉淀 | tag 标记 + fork 下一届继续迭代 |
| 分步骤打分 | 每个 commit 对应一个 rubric 检查点 |
| 展示进步 | v1 vs v5 的行为对比（"你看你第一版的 prompt 多粗糙"） |

**教师视角的 Dashboard：**

```
学生 小明 - skill: math_word_problem_solver
├── v0.1 (Week 1): 基础 prompt，准确率 40%
├── v0.2 (Week 1): 加了 few-shot examples，准确率 55%
├── v0.3 (Week 2): 加了 chain-of-thought，准确率 72%
├── v0.4 (Week 3): 队友贡献了 error-checking step，准确率 78%
└── v1.0 (Week 5): final submission，准确率 81%

学习轨迹可视化 ✓
每步改进的 diff 可追溯 ✓
```

---

## 跨例子的共性需求总结

| 需求 | 例1 科研综述 | 例2 实验Prompt | 例3 教学协作 | 例4 质量回归 | 例5 跨组共享 | 例6 学生作业 |
|------|:-:|:-:|:-:|:-:|:-:|:-:|
| 历史回溯 | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| 分支实验 | ✓ | ✓ | ✓ | | | |
| 多人 merge | ✓ | | ✓ | | ✓ | ✓ |
| 语义 diff | ✓ | ✓ | ✓ | | | ✓ |
| CI/回归测试 | ✓ | ✓ | | ✓ | | |
| 依赖管理 | ✓ | | | | ✓ | |
| 发布/灰度 | | | ✓ | ✓ | ✓ | |
| 可复现性 | ✓ | ✓ | | | | |
| Fork/PR 生态 | | | | | ✓ | ✓ |
| 非技术者 UX | | | ✓ | | | ✓ |

---

## 在这两个场景里，现状有多痛？

### 科研场景现状（我的高置信度判断）

- 大多数团队把 prompt 存在 Notion / 飞书文档 / Google Doc 里，"版本"靠文件名后缀 `_v2_final_final2`
- 少数技术型团队放在 Git 里，但没有结构化 diff，PR review 时看一大坨 JSON 变更
- 实验可复现性形同虚设——论文写"we use GPT-4 with a carefully designed prompt"，但 prompt 迭代了 30 版，没人知道哪版对应哪个实验数据
- **痛点排序**：可复现性 > 分支管理 > 多人冲突

### 教育场景现状

- AI 教学 skill 基本是"一个人维护一个 Google Sheet / Prompt 文档"
- 教师之间分享靠复制粘贴
- 学生作业交一个最终版 PDF/文档，过程不可追溯
- **痛点排序**：协作共享 > 质量回归 > 学生过程追踪

---

## 给你的行动建议

如果你要在这两个场景切入：

**科研场景的 MVP：**
- 就是一个 "Prompt/Skill 的 Git repo + 结构化 diff viewer + 和论文实验绑定的版本 pin"
- 目标用户：AI 实验室 PI 和博士生
- 最小可用：VS Code 插件 + CLI + 一个 web diff viewer

**教育场景的 MVP：**
- 类 GitHub Classroom 但对象是 Skill 而非代码
- 教师一键创建 assignment template → 学生 fork → 提交 PR → 教师 review + 评分
- 最小可用：Web IDE（类 Replit 简洁度）+ 版本历史 + 教师 dashboard

这两个场景的用户画像差异大，但底层引擎（版本存储 + diff + 分支）是共用的。如果你资源有限，建议引擎统一，UI 层分两套皮。

---
## 🧑‍💻 User

我打算把我这套叫sit、对标git，但是不是还是得依托github才能做线上的版本管理

---
## 🤖 Assistant

# sit 的线上托管：必须依赖 GitHub 吗？

不是必须的。但这里有一个关键架构决策需要拆清楚。

---

## 先理清类比关系

| Git 生态 | sit 生态（你要做的） |
|----------|---------------------|
| git（本地引擎，CLI） | sit（本地引擎，CLI） |
| .git 目录（本地存储） | .sit 目录（本地存储） |
| GitHub / GitLab（远程托管 + 协作） | **??? — 这是你真正要回答的问题** |
| git protocol / SSH / HTTPS（传输协议） | sit 的同步协议 |

你说"对标 git"，但你用户真正需要的体验其实是**对标 GitHub**——没有人裸用 git，用户要的是 push/pull/PR/review/dashboard 那一整套。

所以你面临的决策不是"要不要 GitHub"，而是**线上协作层怎么实现**。

---

## 四条路线，从轻到重

### 路线 A：sit 底层直接是 Git，线上就用 GitHub

```
架构:
sit CLI ──(封装)──→ git 命令
.sit/ ──(实际就是)──→ .git/
sit push ──(实际就是)──→ git push to GitHub
线上协作 ──(直接用)──→ GitHub PR / Review / Actions
```

**你做的事：**
- sit 是一个 CLI wrapper，把 skill 的结构化操作翻译成 git 操作
- `sit init` → 创建 git repo + 特定目录结构
- `sit diff` → 读取 skill yaml，展示结构化 diff（本地渲染）
- `sit push` → `git push`
- 线上 review → 直接跳转 GitHub PR 页面

**优点：**
- 开发成本极低，一个人两周能出 MVP
- 免费拿到 GitHub 全套基建（权限、CI、hosting、API）
- 用户已有 GitHub 账号，零迁移成本

**缺点：**
- GitHub PR 页面展示的是行级文本 diff，不是你的结构化语义 diff
- 你的非技术用户（教师、教学设计师）要面对 GitHub 界面——劝退
- 你的品牌完全被 GitHub 淹没，sit 沦为一个 CLI 工具而非平台
- 受制于 GitHub 的 API 限制和产品决策

**适合阶段**：Day 0 验证，科研用户早期采用

---

### 路线 B：sit 底层用 Git，但自建 Web 层替代 GitHub

```
架构:
sit CLI ──(封装)──→ git 命令
.sit/ ──(实际就是)──→ .git/
sit push ──→ 推送到你自建的 Git 服务器（Gitea / bare repo / 自建）
线上协作 ──→ 你自己的 Web UI（SitHub）
```

**你做的事：**
- 后端托管一个 Git 服务器（可以用 Gitea 二次开发，或直接裸 Git + SSH）
- 前端自建 Web UI，展示结构化 diff、Skill 可视化、review 流程
- sit push/pull 走 Git 协议，但远端不是 github.com 而是 sit.yourdomain.com

**优点：**
- 完全控制 UI 体验，可以做 Skill 语义 diff、行为对比、教师 dashboard
- 品牌独立
- 底层还是 Git，可以和 GitHub 双向同步（高级用户可选）

**缺点：**
- 需要运维托管服务
- 需要自建用户系统、权限系统
- Gitea 二次开发有维护负担

**适合阶段**：产品化阶段，当你确认 PMF 之后

**这条路线有成功先例：**
- **Gitee**（底层 Git，自建 Web 层，对标 GitHub 做国内市场）
- **Hugging Face Hub**（底层 Git LFS，自建 Web 层，专门服务模型/数据集）
- **DVC（Data Version Control）**（CLI 层封装 Git，远端存储可选 S3/GCS/自建）

---

### 路线 C：sit 底层不用 Git，完全自建

```
架构:
sit CLI ──→ 自己的版本化引擎
.sit/ ──→ 自己的对象存储格式（content-addressed DAG）
sit push ──→ 推送到自建后端
线上协作 ──→ 自己的 Web UI
```

**你做的事：**
- 从零实现版本控制引擎（snapshot、diff、branch、merge）
- 自建传输协议
- 自建存储后端
- 自建 Web UI

**优点：**
- 完全控制一切，diff/merge 可以做到 Skill 原生语义级别
- 不受 Git 的文本假设限制（Git 的 diff 和 merge 都假设对象是文本行）
- 可以做到 Git 做不到的事：比如 Skill 的参数级 merge、prompt 的语义冲突检测

**缺点：**
- 工程量巨大，Git 的核心引擎是几十年的积累
- 生态为零，没有 IDE 集成、没有第三方工具
- 用户心智成本高——又要学一套新东西

**适合阶段**：除非你有明确证据证明 Git 的数据模型根本不能满足 Skill 的需求，否则不建议走这条路

---

### 路线 D（推荐）：混合架构 — Git 存储 + 自建协作层 + GitHub 作为可选同步源

```
架构:

                    ┌─────────────────────┐
                    │   SitHub (你的平台)    │
                    │  - 结构化 Diff 视图    │
                    │  - Skill 可视化编辑    │
                    │  - Review / 评审流程   │
                    │  - CI: Skill 回归测试  │
                    │  - Dashboard          │
                    └──────────┬────────────┘
                               │
                    Git protocol (标准)
                               │
              ┌────────────────┼────────────────┐
              │                │                │
         sit CLI          VS Code 插件      Web Editor
              │                │                │
         .sit/ (.git/)    .sit/ (.git/)    (server-side)
              │
              │  (可选) git remote add github ...
              │  (可选) git remote add sithub ...
              ▼
        可同时推送到 GitHub 和 SitHub
```

**核心思路：**
- 存储层 = Git（不重造轮子）
- 传输层 = Git 协议（兼容一切）
- 协作层 = 你自己的 Web 平台（SitHub），这是价值所在
- GitHub = 可选的镜像/备份/兼容层（对高级用户）

**用户故事：**

```bash
# 科研用户（技术型）
sit init my-judge-skill
sit add .
sit commit -m "v1: baseline judge prompt"
sit remote add origin https://sithub.io/lab/judge-skill
sit push origin main
# 然后去 sithub.io 上做 review、看结构化 diff

# 同时可以
git remote add github https://github.com/lab/judge-skill
git push github main
# 代码也在 GitHub 有一份，论文可以引用 GitHub 链接
```

```
# 教育用户（非技术型）
1. 登录 sithub.io
2. 在 Web Editor 里编辑 Skill
3. 点击"保存新版本"（背后是 commit）
4. 点击"提交给老师"（背后是 create PR）
5. 老师在线 review、打分
# 用户完全不知道底层是 Git
```

---

## 关于 SitHub 的技术选型

如果你走路线 D，SitHub 的服务端怎么搞：

| 组件 | 推荐方案 | 理由 |
|------|----------|------|
| Git 托管引擎 | **Gitea（Go，可嵌入）** 或 **gitolite + 自建 API** | Gitea 是最轻量的自托管 Git 服务器，API 完整，二次开发友好 |
| 结构化 Diff 引擎 | 自建（解析 YAML/JSON，计算 structural diff） | 这是你的核心差异化，没有现成方案 |
| Web UI | 前端框架自选（React/Vue） | 重点投入 diff 可视化和 Skill 编辑器 |
| CI/测试 | 自建 runner（类 GitHub Actions 但跑 Skill 测试） | 可先简化为 webhook + Docker container |
| 存储 | Git repo on disk + 对象存储（S3）放大文件 | Git LFS 模式处理 golden test set 等大资产 |

---

## 名字的问题

你叫 sit，那线上平台自然叫 **SitHub**。这个命名有几个注意点：

| 维度 | 分析 |
|------|------|
| 记忆性 | sit 简短，容易记，对标 git 用户秒懂 |
| 国际化 | sit 在英语中是"坐"，无负面含义，可用 |
| 域名 | sithub.io / sithub.dev 需要检查可用性 |
| 商标 | sit 太通用，商标注册可能有困难，建议查一下 |
| CLI 冲突 | Linux 上有没有已有命令叫 sit？（快速查：没有主流命令占用这个名字，可行） |

---

## 我的建议路径

```
Month 1-2:  路线 A
            sit CLI 封装 Git
            sit diff 做本地结构化 diff
            推到 GitHub，手动 review
            找 2-3 个实验室内测

Month 3-4:  路线 A → D 过渡
            搭建 SitHub Web 最小版
            核心功能: 结构化 diff 在线查看 + PR 流程
            底层 Gitea 或 bare Git
            科研用户开始用线上 review

Month 5-6:  路线 D 完整版
            Web Editor（非技术用户可用）
            Skill CI（自动回归测试）
            教育场景的 Classroom 功能
            
Month 7+:   生态
            Skill Registry（类 npm/PyPI）
            公开 Skill 发现和 fork
            VS Code 插件
```

**核心原则**：存储层不要自己造，Git 已经解决了。你的价值在 Git 之上的语义层——diff、merge、测试、可视化、协作 UX。GitHub 不是你的竞争对手，它是你早期的基建提供商，后期的可选兼容层。

---
## 🧑‍💻 User

我觉得确实先从A入手就够了，先基于git封装，然后提供额外的、可用于skill的信息，支持围绕skill的团队协作、版本控制

---
## 🤖 Assistant

# sit 路线 A 的具体实现方案

## 核心定位

sit = Git + Skill 感知层

Git 管版本存储和传输，sit 在上面加三件事：
1. **Skill 结构约定**（文件组织 + schema）
2. **Skill 语义信息**（结构化 diff、依赖声明、变更类型标注）
3. **Skill 协作增强**（commit 规范、review 辅助信息、测试钩子）

---

## 目录结构约定

```
my-skill/
├── .sit/
│   ├── config.yaml          # sit 元配置
│   └── hooks/               # sit 特有钩子
├── .git/                    # 标准 Git，不动
├── skill.yaml               # Skill 主定义（核心文件）
├── prompts/
│   ├── system.md            # system prompt
│   ├── user_template.md     # user prompt 模板
│   └── few_shots/
│       ├── example_01.yaml
│       └── example_02.yaml
├── schema/
│   ├── input.json           # 输入参数 schema
│   └── output.json          # 输出 schema
├── tests/
│   ├── golden/              # golden test cases
│   │   ├── case_01.yaml
│   │   └── case_02.yaml
│   └── eval_config.yaml     # 评估配置
├── deps.yaml                # 依赖的其他 skill
├── CHANGELOG.md             # 自动/手动维护
└── README.md
```

### skill.yaml 长这样

```yaml
name: paper_taxonomy_mapper
version: 1.2.0
description: 将AI安全论文归入分类体系
authors:
  - name: 张三
    role: maintainer
  - name: 李四
    role: contributor

model:
  provider: openai
  name: gpt-4o
  temperature: 0.2

entry: prompts/system.md
input_schema: schema/input.json
output_schema: schema/output.json

tags:
  - research
  - nlp
  - survey
```

---

## CLI 命令设计

### 原则：和 Git 命令保持平行，不造新心智模型

```bash
# 初始化
sit init                      # = git init + 生成 .sit/ + skill.yaml 模板

# 日常操作（直接透传 Git）
sit add .                     # = git add .
sit commit -m "msg"           # = git commit（但会先跑 sit 的 pre-commit 校验）
sit push                      # = git push
sit pull                      # = git pull
sit branch experiment-cot     # = git branch
sit checkout experiment-cot   # = git checkout
sit log                       # = git log（但增强显示 skill 版本号变更）

# sit 特有命令（Git 不提供的）
sit diff                      # 结构化 diff，不是行级 diff
sit status                    # 除了 git status，还显示 skill 层面的变更摘要
sit validate                  # 校验 skill.yaml、schema 一致性
sit test                      # 跑 golden test cases
sit release patch|minor|major # bump 版本号 + tag + changelog
sit deps check                # 检查依赖 skill 版本兼容性
sit info                      # 展示当前 skill 的全景信息
```

---

## `sit diff` — 核心差异化功能

这是你和裸 Git 拉开差距的第一个命令。

### 裸 `git diff` 看到的

```diff
- "type": "string",
+ "type": "object",
+ "properties": {
+   "city": {"type": "string"},
+   "country": {"type": "string"}
+ },
```

### `sit diff` 看到的

```
╔══════════════════════════════════════════════════╗
║  Skill Diff: paper_taxonomy_mapper              ║
║  Comparing: main ← branch/bo-new-taxonomy      ║
╠══════════════════════════════════════════════════╣
║                                                  ║
║  📋 Schema Changes                              ║
║  ┌────────────────────────────────────────────┐ ║
║  │ [BREAKING] input.location                  │ ║
║  │   type: string → object{city, country}     │ ║
║  │                                            │ ║
║  │ [ADDED] input.date_range                   │ ║
║  │   type: string, required: false            │ ║
║  └────────────────────────────────────────────┘ ║
║                                                  ║
║  📝 Prompt Changes                              ║
║  ┌────────────────────────────────────────────┐ ║
║  │ system.md: +12 lines, -2 lines            │ ║
║  │ Summary: 新增「防御阶段」分类维度          │ ║
║  │ [view full diff: sit diff --prompt]        │ ║
║  └────────────────────────────────────────────┘ ║
║                                                  ║
║  🧪 Tests                                       ║
║  ┌────────────────────────────────────────────┐ ║
║  │ +3 new golden cases                        │ ║
║  │ 0 modified, 0 deleted                      │ ║
║  └────────────────────────────────────────────┘ ║
║                                                  ║
║  ⚠️  Breaking change detected.                  ║
║  Suggested version bump: MAJOR (1.x → 2.0)     ║
║                                                  ║
╚══════════════════════════════════════════════════╝
```

### 实现方式

```python
# 伪代码
def sit_diff(ref_a, ref_b):
    # 1. 读取两个版本的 skill.yaml, schema/, prompts/
    old = parse_skill(ref_a)
    new = parse_skill(ref_b)
    
    # 2. Schema diff（结构化比较 JSON Schema）
    schema_changes = diff_json_schema(old.input_schema, new.input_schema)
    for change in schema_changes:
        classify(change)  # BREAKING / NON-BREAKING / DEPRECATION
    
    # 3. Prompt diff（文本 diff + 可选 LLM 摘要）
    prompt_diff = text_diff(old.system_prompt, new.system_prompt)
    if user_wants_summary:
        summary = llm_summarize_diff(prompt_diff)
    
    # 4. Test diff
    test_changes = diff_file_list(old.tests, new.tests)
    
    # 5. Version bump 建议
    if any_breaking(schema_changes):
        suggest = "MAJOR"
    elif any_addition(schema_changes) or significant_prompt_change(prompt_diff):
        suggest = "MINOR"
    else:
        suggest = "PATCH"
    
    render(schema_changes, prompt_diff, test_changes, suggest)
```

---

## `sit commit` 的增强

### Pre-commit 自动校验

```bash
$ sit commit -m "新增防御阶段维度"

[sit validate] ✓ skill.yaml 格式正确
[sit validate] ✓ input.json 是合法 JSON Schema
[sit validate] ✓ output.json 是合法 JSON Schema
[sit validate] ✓ prompts/system.md 中的变量引用与 input schema 一致
[sit validate] ⚠️  schema 有 breaking change，但 version 未 bump
              → 建议执行 sit release major 或手动修改 skill.yaml version

Proceed with commit? [Y/n]
```

### Commit message 规范（类 Conventional Commits）

```
sit commit 建议格式:

  prompt: 优化分类维度描述           → prompt 变更
  schema: 添加 defense_stage 字段    → schema 变更  
  test: 补充电磁学相关 golden case   → 测试变更
  config: 切换模型为 gpt-4o-mini     → 配置变更
  fix: 修复多标签输出格式错误        → bug fix
  feat: 支持多语言论文输入           → 新功能
```

sit 可以提供 `sit commit` 交互模式引导用户选择变更类型。

---

## `sit test` — 回归测试

```bash
$ sit test

Running golden tests...
  case_01: ✓ (match)
  case_02: ✓ (match)  
  case_03: ✗ (output schema mismatch)
    Expected: {"attack_type": "jailbreak", "defense_stage": null}
    Got:      {"attack_type": "jailbreak"}  ← 缺少 defense_stage 字段

1/3 failed. Skill may have regression.
```

### tests/golden/case_01.yaml 格式

```yaml
name: "典型 jailbreak 攻击论文"
input:
  paper_title: "Universal and Transferable Adversarial Attacks on Aligned Language Models"
  paper_abstract: "..."
expected_output:
  attack_type: "jailbreak"
  defense_stage: null
match_mode: exact  # exact | contains | schema_only | llm_judge
```

---

## 团队协作怎么跑（在 GitHub 上）

### 工作流

```
1. sit init + git remote add origin (GitHub repo)
2. 每人各自 branch:
   sit branch feature/xxx
   sit checkout feature/xxx
   
3. 改完后:
   sit validate ✓
   sit test ✓
   sit commit -m "prompt: ..."
   sit push
   
4. 去 GitHub 开 PR
   PR 描述模板（sit 自动生成）:
   ┌─────────────────────────────────────┐
   │ ## Skill Change Summary             │
   │ (auto-generated by sit)             │
   │                                     │
   │ **Schema**: 1 breaking change       │
   │ **Prompt**: system.md modified      │
   │ **Tests**: +3 new cases, 0 fails    │
   │ **Suggested bump**: MAJOR           │
   │                                     │
   │ ### Detailed Diff                   │
   │ [结构化 diff 内容]                   │
   └─────────────────────────────────────┘

5. Reviewer 在 GitHub 上 review
   （虽然 GitHub 显示的是行级 diff，但 PR description 里有结构化摘要）
   
6. Merge → sit release
```

### GitHub Actions 集成

```yaml
# .github/workflows/sit-ci.yaml
name: Skill CI
on: [pull_request]

jobs:
  validate-and-test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: sit-tool/setup-sit@v1
      - run: sit validate
      - run: sit test
      - run: sit diff main..HEAD --format=markdown >> $GITHUB_STEP_SUMMARY
```

这样每个 PR 自动跑校验和测试，结果显示在 GitHub PR 页面。

---

## `sit info` — 全景展示

```bash
$ sit info

╔═══════════════════════════════════════════╗
║  paper_taxonomy_mapper v1.2.0            ║
║  by 张三, 李四                            ║
╠═══════════════════════════════════════════╣
║  Model: gpt-4o (temp=0.2)               ║
║  Input: paper_title, paper_abstract      ║
║  Output: attack_type, defense_stage      ║
║                                          ║
║  Branches: 3 (main, exp/cot, exp/rubric)║
║  Commits: 27                             ║
║  Last modified: 2h ago by 李四           ║
║  Tests: 15 golden cases, last run ✓      ║
║                                          ║
║  Dependencies:                           ║
║    pdf_parser@^2.0.0 ✓ (resolved 2.1.3) ║
║    claim_extractor@^1.5.0 ✓             ║
║                                          ║
║  Depended by:                            ║
║    contradiction_finder@1.0.0            ║
╚═══════════════════════════════════════════╝
```

---

## MVP 范围建议（4周可交付）

### Week 1-2: 骨架

| 命令 | 实现 |
|------|------|
| `sit init` | 生成目录结构 + skill.yaml 模板 |
| `sit add/commit/push/pull` | 透传 Git（加 pre-commit 校验） |
| `sit validate` | 校验 skill.yaml + schema 一致性 |
| `sit diff` | 结构化 diff（schema 级别，不含 LLM 摘要） |

### Week 3: 测试 + 发布

| 命令 | 实现 |
|------|------|
| `sit test` | 跑 golden cases（exact match + schema match） |
| `sit release` | bump version + git tag + 更新 CHANGELOG |
| `sit status` | 增强 git status |

### Week 4: 协作层

| 功能 | 实现 |
|------|------|
| PR 模板自动生成 | `sit pr-summary` 输出 markdown |
| GitHub Actions 模板 | `sit init` 时自动生成 CI yaml |
| `sit info` | 全景展示 |

### 技术栈建议

```
语言: Python（最快出活）或 Rust（如果你想做成高性能 CLI 工具分发）
      → MVP 阶段强烈建议 Python，用 Click 做 CLI
依赖: 
  - GitPython（调 Git）
  - PyYAML / ruamel.yaml（解析 skill 定义）
  - jsonschema（校验 schema）
  - rich（终端美化输出，那些框框都能做）
分发:
  - pip install sit-tool（先上 PyPI）
  - 后期考虑 homebrew / standalone binary
```

---

## 从 A 到 D 的自然演进触发点

不要提前做 SitHub，但要提前在架构上预留。具体来说：

| 当你观察到... | 就该启动... |
|--------------|------------|
| 用户抱怨 GitHub PR 页面看不懂 Skill diff | 做一个 Web diff viewer（哪怕是静态页面） |
| 非技术用户（教师）入场 | 做 Web Editor |
| 多个 repo 之间有依赖关系要管理 | 做 Skill Registry |
| 用户想发现/复用别人的 Skill | 做 SitHub 的 Explore 功能 |

在 A 阶段要做的架构预留：
- `sit diff --format=json` 输出机器可读格式（将来 Web 前端消费）
- skill.yaml 中的 `registry` 字段先定义好（将来接 registry）
- Git remote 命名约定（`origin` = GitHub, 将来可加 `sithub` remote）

---

## 一句话

先做一个好用的 CLI，让人觉得"用了 sit 之后管 Skill 比裸 Git 舒服太多"——这就够启动了。平台化是验证需求之后的事。
