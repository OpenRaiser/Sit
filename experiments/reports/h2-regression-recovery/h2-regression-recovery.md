# H2 回归恢复实验

## 实验目的

本实验检验 `docs/proposal.md` 中的 H2 假设：当共享 Skill 库中合入一次有害演化时，`sit` 应该能通过精确回滚坏变更在 O(1) 步内恢复，同时避免粗粒度快照方案的工作损失，也避免无版本控制方案的缓慢重新演化过程。

## 实验设计

- 共享 Skill 包：`examples/paper-taxonomy-mapper-v0.2.0`
- 对比条件：`novc`、`periodic-snap`、`ours-sit`
- 随机种子：`0,1,2,3,4`
- 每次运行步数：`200`
- 有害 PR 注入步数：`100`
- `periodic-snap` 快照间隔：`50`
- `novc` 重新学习延迟：`30`
- 总运行次数：`15`（`3 个条件 x 5 个种子`）

实验 driver 通过向 prompt 中加入 `BAD_REGRESSION_H2_OUTPUT_DEGRADES_30_PERCENT` 标记来注入一个 bad Skill PR。确定性 evaluator 会把这个标记解释为 30% 的任务成功率退化：标记存在时成功率从 `1.0` 降到 `0.7`。

## 方法

所有条件都通过 `experiments/driver.py` 运行，并记录 JSONL 轨迹。

- `novc`：模拟无可恢复历史的直接覆盖式 Skill 库。检测到退化后，只能等待配置的重新学习延迟结束后恢复。
- `periodic-snap`：恢复最近一次全量包快照。它可以快速恢复，但会丢弃快照之后的正常演化工作。
- `ours-sit`：使用 `git revert <bad-sha>` 和 `sit release patch --no-git-tag --no-version-gate`，只移除坏 PR。

执行命令：

```bash
python3 experiments/driver.py --experiment h2 --condition all --steps 200 --bad-step 100 --snapshot-interval 50 --no-vc-recovery-delay 30 --seeds 0,1,2,3,4 --run-id h2-formal-200
```

原始聚合结果：

```text
experiments/runs/h2-formal-200/summary.json
```

## 指标定义

- `detection_step`：首次检测到成功率低于 baseline 的步数。
- `recovery_action_step`：执行或计划执行恢复动作的步数。
- `recovered_step`：成功率首次回到 baseline 的步数。
- `recovery_steps`：`recovered_step - bad_step`。
- `affected_skill_steps`：bad Skill 影响 Skill 库的步数。
- `work_lost_steps`：恢复时丢弃的正常演化工作量。

## 实验结果

| 条件 | 运行次数 | 平均恢复步数 | 平均受影响 Skill 步数 | 平均丢失工作步数 | 未恢复运行数 | 最终成功率 |
|---|---:|---:|---:|---:|---:|---:|
| NoVC | 5 | 30.0 | 30.0 | 0.0 | 0 | 1.0 |
| PeriodicSnap | 5 | 1.0 | 1.0 | 50.0 | 0 | 1.0 |
| Ours-sit | 5 | 1.0 | 1.0 | 0.0 | 0 | 1.0 |

![H2 聚合指标](h2-metrics.svg)

![H2 成功率恢复曲线](h2-success-curve.svg)

## 结果解释

`ours-sit` 达到了和 `periodic-snap` 一样快的恢复速度，同时避免了粗粒度回滚成本。两者都能在检测到 bad merge 后 1 步恢复，但 `periodic-snap` 平均会丢失 50 步正常演化工作，因为最近快照在 step 50，而 bad PR 在 step 100 注入。`ours-sit` 精确 revert 坏提交，因此平均工作损失为 0。

与 `novc` 相比，`ours-sit` 将平均恢复步数从 30 降到 1，也将平均 bad Skill 暴露步数从 30 降到 1。在当前确定性实验中，这相当于把恢复延迟和 bad Skill 暴露时间都降低了 30 倍。

## 局限性

这仍然是一个合成基础设施实验。evaluator 使用确定性的 regression marker，而不是运行真实 benchmark 任务。这个结果验证的是 driver、协议路径、恢复机制和度量管线；下一步应在保持相同 condition 设计的前提下，用真实任务成功率测量替换当前的合成成功率函数。

## 产物

- 报告目录：`experiments/reports/h2-regression-recovery`
- 指标图表：`experiments/reports/h2-regression-recovery/h2-metrics.svg`
- 恢复曲线图：`experiments/reports/h2-regression-recovery/h2-success-curve.svg`
- 原始 summary：`experiments/runs/h2-formal-200/summary.json`
