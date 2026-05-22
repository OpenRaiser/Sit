from __future__ import annotations

import argparse
import json
from html import escape
from pathlib import Path
from statistics import mean
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SUMMARY = REPO_ROOT / "experiments" / "runs" / "h2-formal-200" / "summary.json"
DEFAULT_OUTPUT_DIR = REPO_ROOT / "experiments" / "reports" / "h2-regression-recovery"
CONDITION_ORDER = ["novc", "periodic-snap", "ours-sit"]
CONDITION_LABELS = {
    "novc": "NoVC",
    "periodic-snap": "PeriodicSnap",
    "ours-sit": "Ours-sit",
}
CONDITION_COLORS = {
    "novc": "#d95f02",
    "periodic-snap": "#7570b3",
    "ours-sit": "#1b9e77",
}


def main() -> int:
    args = _parser().parse_args()
    summary_path = args.summary.resolve()
    output_dir = args.output_dir.resolve()
    data = json.loads(summary_path.read_text(encoding="utf-8"))
    output_dir.mkdir(parents=True, exist_ok=True)

    metrics_svg = output_dir / "h2-metrics.svg"
    curve_svg = output_dir / "h2-success-curve.svg"
    report_path = output_dir / "h2-regression-recovery.md"

    metrics_svg.write_text(_metrics_svg(data), encoding="utf-8")
    curve_svg.write_text(_success_curve_svg(data), encoding="utf-8")
    report_path.write_text(_report_markdown(data, summary_path=summary_path, output_dir=output_dir), encoding="utf-8")

    print(f"Wrote report: {report_path}")
    print(f"Wrote chart: {metrics_svg}")
    print(f"Wrote chart: {curve_svg}")
    return 0


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate H2 regression recovery report and SVG charts.")
    parser.add_argument("--summary", type=Path, default=DEFAULT_SUMMARY, help="H2 batch summary.json")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR, help="Directory for report and charts")
    return parser


def _report_markdown(data: dict[str, Any], *, summary_path: Path, output_dir: Path) -> str:
    rows = _condition_rows(data)
    runs = data.get("runs", [])
    steps = int(runs[0].get("steps", 0)) if runs else 0
    bad_step = int(runs[0].get("bad_step", 0)) if runs else 0
    seeds = sorted({str(index) for index, _run in enumerate(runs[:5])})
    run_count = len(runs)

    table = "\n".join(
        [
            "| 条件 | 运行次数 | 平均恢复步数 | 平均受影响 Skill 步数 | 平均丢失工作步数 | 未恢复运行数 | 最终成功率 |",
            "|---|---:|---:|---:|---:|---:|---:|",
            *[
                (
                    f"| {CONDITION_LABELS[row['condition']]} | {row['runs']} | {row['recovery_steps']:.1f} | "
                    f"{row['affected_skill_steps']:.1f} | {row['work_lost_steps']:.1f} | "
                    f"{row['unrecovered_runs']} | {row['final_success_rate']:.1f} |"
                )
                for row in rows
            ],
        ]
    )

    command = (
        "python3 experiments/driver.py --experiment h2 --condition all --steps 200 "
        "--bad-step 100 --snapshot-interval 50 --no-vc-recovery-delay 30 "
        "--seeds 0,1,2,3,4 --run-id h2-formal-200"
    )
    summary_rel = _rel(summary_path)
    output_rel = _rel(output_dir)

    return f"""# H2 回归恢复实验

## 实验目的

本实验检验 `docs/proposal.md` 中的 H2 假设：当共享 Skill 库中合入一次有害演化时，`sit` 应该能通过精确回滚坏变更在 O(1) 步内恢复，同时避免粗粒度快照方案的工作损失，也避免无版本控制方案的缓慢重新演化过程。

## 实验设计

- 共享 Skill 包：`examples/paper-taxonomy-mapper-v0.2.0`
- 对比条件：`novc`、`periodic-snap`、`ours-sit`
- 随机种子：`0,1,2,3,4`
- 每次运行步数：`{steps}`
- 有害 PR 注入步数：`{bad_step}`
- `periodic-snap` 快照间隔：`50`
- `novc` 重新学习延迟：`30`
- 总运行次数：`{run_count}`（`3 个条件 x 5 个种子`）

实验 driver 通过向 prompt 中加入 `BAD_REGRESSION_H2_OUTPUT_DEGRADES_30_PERCENT` 标记来注入一个 bad Skill PR。确定性 evaluator 会把这个标记解释为 30% 的任务成功率退化：标记存在时成功率从 `1.0` 降到 `0.7`。

## 方法

所有条件都通过 `experiments/driver.py` 运行，并记录 JSONL 轨迹。

- `novc`：模拟无可恢复历史的直接覆盖式 Skill 库。检测到退化后，只能等待配置的重新学习延迟结束后恢复。
- `periodic-snap`：恢复最近一次全量包快照。它可以快速恢复，但会丢弃快照之后的正常演化工作。
- `ours-sit`：使用 `git revert <bad-sha>` 和 `sit release patch --no-git-tag --no-version-gate`，只移除坏 PR。

执行命令：

```bash
{command}
```

原始聚合结果：

```text
{summary_rel}
```

## 指标定义

- `detection_step`：首次检测到成功率低于 baseline 的步数。
- `recovery_action_step`：执行或计划执行恢复动作的步数。
- `recovered_step`：成功率首次回到 baseline 的步数。
- `recovery_steps`：`recovered_step - bad_step`。
- `affected_skill_steps`：bad Skill 影响 Skill 库的步数。
- `work_lost_steps`：恢复时丢弃的正常演化工作量。

## 实验结果

{table}

![H2 聚合指标](h2-metrics.svg)

![H2 成功率恢复曲线](h2-success-curve.svg)

## 结果解释

`ours-sit` 达到了和 `periodic-snap` 一样快的恢复速度，同时避免了粗粒度回滚成本。两者都能在检测到 bad merge 后 1 步恢复，但 `periodic-snap` 平均会丢失 50 步正常演化工作，因为最近快照在 step 50，而 bad PR 在 step 100 注入。`ours-sit` 精确 revert 坏提交，因此平均工作损失为 0。

与 `novc` 相比，`ours-sit` 将平均恢复步数从 30 降到 1，也将平均 bad Skill 暴露步数从 30 降到 1。在当前确定性实验中，这相当于把恢复延迟和 bad Skill 暴露时间都降低了 30 倍。

## 局限性

这仍然是一个合成基础设施实验。evaluator 使用确定性的 regression marker，而不是运行真实 benchmark 任务。这个结果验证的是 driver、协议路径、恢复机制和度量管线；下一步应在保持相同 condition 设计的前提下，用真实任务成功率测量替换当前的合成成功率函数。

## 产物

- 报告目录：`{output_rel}`
- 指标图表：`{output_rel}/h2-metrics.svg`
- 恢复曲线图：`{output_rel}/h2-success-curve.svg`
- 原始 summary：`{summary_rel}`
"""


def _condition_rows(data: dict[str, Any]) -> list[dict[str, Any]]:
    conditions = data.get("conditions", {})
    rows = []
    for condition in CONDITION_ORDER:
        item = conditions.get(condition, {})
        runs = [run for run in data.get("runs", []) if run.get("condition") == condition]
        rows.append(
            {
                "condition": condition,
                "runs": int(item.get("runs", len(runs))),
                "recovery_steps": float(item.get("mean_recovery_steps", _mean_run(runs, "recovery_steps"))),
                "affected_skill_steps": float(item.get("mean_affected_skill_steps", _mean_run(runs, "affected_skill_steps"))),
                "work_lost_steps": float(item.get("mean_work_lost_steps", _mean_run(runs, "work_lost_steps"))),
                "unrecovered_runs": int(item.get("unrecovered_runs", 0)),
                "final_success_rate": _mean_run(runs, "final_success_rate"),
            }
        )
    return rows


def _metrics_svg(data: dict[str, Any]) -> str:
    rows = _condition_rows(data)
    metrics = [
        ("recovery_steps", "Recovery steps"),
        ("affected_skill_steps", "Affected Skill steps"),
        ("work_lost_steps", "Work lost steps"),
    ]
    width = 980
    height = 520
    margin_left = 92
    margin_top = 72
    chart_width = 820
    chart_height = 330
    max_value = max(row[key] for row in rows for key, _label in metrics)
    y_max = max(10.0, _round_up(max_value))
    group_width = chart_width / len(metrics)
    bar_width = 46
    baseline_y = margin_top + chart_height
    parts = [_svg_header(width, height), _svg_text(30, 36, "H2 Regression Recovery Metrics", size=24, weight="700")]
    parts.append(_svg_text(30, 60, "Lower is better. Values are means across 5 seeds.", size=13, color="#555"))
    parts.extend(_axis_grid(margin_left, margin_top, chart_width, chart_height, y_max))

    for metric_index, (key, label) in enumerate(metrics):
        group_x = margin_left + metric_index * group_width
        parts.append(_svg_text(group_x + group_width / 2, baseline_y + 48, label, size=13, anchor="middle"))
        for row_index, row in enumerate(rows):
            value = float(row[key])
            x = group_x + group_width / 2 - (bar_width * 1.5) + row_index * (bar_width + 12)
            bar_h = 0 if y_max == 0 else chart_height * (value / y_max)
            y = baseline_y - bar_h
            color = CONDITION_COLORS[row["condition"]]
            parts.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{bar_width}" height="{bar_h:.1f}" fill="{color}" rx="3"/>')
            parts.append(_svg_text(x + bar_width / 2, y - 8, f"{value:.0f}", size=12, anchor="middle", color="#222"))

    parts.extend(_legend(width - 270, 28))
    parts.append("</svg>\n")
    return "\n".join(parts)


def _success_curve_svg(data: dict[str, Any]) -> str:
    runs = data.get("runs", [])
    if not runs:
        return _empty_svg("No H2 run data")
    steps = int(runs[0]["steps"])
    bad_step = int(runs[0]["bad_step"])
    rows = _condition_rows(data)
    width = 980
    height = 520
    margin_left = 92
    margin_top = 72
    chart_width = 820
    chart_height = 330
    parts = [_svg_header(width, height), _svg_text(30, 36, "H2 Success-Rate Recovery Curves", size=24, weight="700")]
    parts.append(_svg_text(30, 60, "Synthetic evaluator: bad Skill marker drops success from 1.0 to 0.7.", size=13, color="#555"))
    parts.extend(_success_grid(margin_left, margin_top, chart_width, chart_height, steps))

    for row in rows:
        condition = row["condition"]
        condition_runs = [run for run in runs if run.get("condition") == condition]
        recovered = mean(float(run["recovered_step"]) for run in condition_runs)
        points = _curve_points(bad_step, recovered, steps)
        path = []
        for step, score in points:
            x = margin_left + chart_width * (step / steps)
            y = margin_top + chart_height * ((1.0 - score) / 0.4)
            path.append(f"{x:.1f},{y:.1f}")
        color = CONDITION_COLORS[condition]
        parts.append(f'<polyline points="{" ".join(path)}" fill="none" stroke="{color}" stroke-width="4" stroke-linejoin="round"/>')

    bad_x = margin_left + chart_width * (bad_step / steps)
    parts.append(f'<line x1="{bad_x:.1f}" y1="{margin_top}" x2="{bad_x:.1f}" y2="{margin_top + chart_height}" stroke="#333" stroke-dasharray="5 5"/>')
    parts.append(_svg_text(bad_x + 6, margin_top + 18, "bad PR", size=12, color="#333"))
    parts.extend(_legend(width - 270, 28))
    parts.append("</svg>\n")
    return "\n".join(parts)


def _axis_grid(x: int, y: int, width: int, height: int, y_max: float) -> list[str]:
    parts = []
    for tick in range(0, 6):
        value = y_max * tick / 5
        yy = y + height - height * tick / 5
        parts.append(f'<line x1="{x}" y1="{yy:.1f}" x2="{x + width}" y2="{yy:.1f}" stroke="#e8e8e8"/>')
        parts.append(_svg_text(x - 12, yy + 4, f"{value:.0f}", size=11, anchor="end", color="#555"))
    parts.append(f'<line x1="{x}" y1="{y}" x2="{x}" y2="{y + height}" stroke="#222"/>')
    parts.append(f'<line x1="{x}" y1="{y + height}" x2="{x + width}" y2="{y + height}" stroke="#222"/>')
    return parts


def _success_grid(x: int, y: int, width: int, height: int, steps: int) -> list[str]:
    parts = []
    for score in (0.7, 0.8, 0.9, 1.0):
        yy = y + height * ((1.0 - score) / 0.4)
        parts.append(f'<line x1="{x}" y1="{yy:.1f}" x2="{x + width}" y2="{yy:.1f}" stroke="#e8e8e8"/>')
        parts.append(_svg_text(x - 12, yy + 4, f"{score:.1f}", size=11, anchor="end", color="#555"))
    for step in (0, steps // 2, steps):
        xx = x + width * (step / steps)
        parts.append(f'<line x1="{xx:.1f}" y1="{y}" x2="{xx:.1f}" y2="{y + height}" stroke="#f1f1f1"/>')
        parts.append(_svg_text(xx, y + height + 24, str(step), size=11, anchor="middle", color="#555"))
    parts.append(f'<line x1="{x}" y1="{y}" x2="{x}" y2="{y + height}" stroke="#222"/>')
    parts.append(f'<line x1="{x}" y1="{y + height}" x2="{x + width}" y2="{y + height}" stroke="#222"/>')
    parts.append(_svg_text(x + width / 2, y + height + 52, "step", size=13, anchor="middle", color="#333"))
    parts.append(_svg_text(x - 62, y + height / 2, "success", size=13, anchor="middle", color="#333", rotate=-90))
    return parts


def _curve_points(bad_step: int, recovered_step: float, steps: int) -> list[tuple[float, float]]:
    return [
        (0, 1.0),
        (bad_step - 1, 1.0),
        (bad_step, 0.7),
        (recovered_step, 0.7),
        (recovered_step + 1, 1.0),
        (steps, 1.0),
    ]


def _legend(x: int, y: int) -> list[str]:
    parts = []
    for index, condition in enumerate(CONDITION_ORDER):
        yy = y + index * 24
        parts.append(f'<rect x="{x}" y="{yy}" width="14" height="14" fill="{CONDITION_COLORS[condition]}" rx="2"/>')
        parts.append(_svg_text(x + 22, yy + 12, CONDITION_LABELS[condition], size=13))
    return parts


def _svg_header(width: int, height: int) -> str:
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" role="img">\n'
        '<rect width="100%" height="100%" fill="#fff"/>'
    )


def _svg_text(
    x: float,
    y: float,
    text: str,
    *,
    size: int = 12,
    anchor: str = "start",
    color: str = "#111",
    weight: str = "400",
    rotate: int | None = None,
) -> str:
    transform = f' transform="rotate({rotate} {x:.1f} {y:.1f})"' if rotate is not None else ""
    return (
        f'<text x="{x:.1f}" y="{y:.1f}" text-anchor="{anchor}" fill="{color}" '
        f'font-family="Arial, sans-serif" font-size="{size}" font-weight="{weight}"{transform}>'
        f"{escape(text)}</text>"
    )


def _empty_svg(message: str) -> str:
    return "\n".join([_svg_header(720, 200), _svg_text(32, 100, message, size=18), "</svg>\n"])


def _round_up(value: float) -> float:
    if value <= 10:
        return 10
    if value <= 50:
        return 50
    return ((int(value) + 49) // 50) * 50


def _mean_run(runs: list[dict[str, Any]], key: str) -> float:
    values = [float(run[key]) for run in runs if run.get(key) is not None]
    return mean(values) if values else 0.0


def _rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return str(path)


if __name__ == "__main__":
    raise SystemExit(main())
