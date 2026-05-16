from __future__ import annotations

from datetime import date
from html import escape
from typing import Any

from .diff import diff_packages
from .package import SkillPackage
from .validate import CheckResult, run_golden_schema_tests, validate_package


def build_report(
    package: SkillPackage,
    *,
    compare: SkillPackage | None = None,
    package_spec: str | None = None,
    diff_command: str | None = None,
    package_source: str | None = None,
    compare_source: str | None = None,
) -> str:
    data = build_report_payload(
        package,
        compare=compare,
        package_spec=package_spec,
        diff_command=diff_command,
        package_source=package_source,
        compare_source=compare_source,
    )
    return render_report_markdown(data)


def build_report_payload(
    package: SkillPackage,
    *,
    compare: SkillPackage | None = None,
    package_spec: str | None = None,
    diff_command: str | None = None,
    package_source: str | None = None,
    compare_source: str | None = None,
) -> dict[str, Any]:
    validation = validate_package(package)
    test_result = run_golden_schema_tests(package) if validation.ok else None
    diff = diff_packages(compare, package) if compare is not None else None
    validate_command = f"python3 -m sit.cli validate {package_spec or package.root}"
    test_command = f"python3 -m sit.cli test {package_spec or package.root}"
    payload = {
        "schema_version": "sit.report.v1",
        "date": date.today().isoformat(),
        "package": _package_ref(package, source=package_source),
        "validation": validation.to_dict(),
        "golden_tests": _test_result_dict(test_result),
        "diff": diff.to_dict(compare, package, old_source=compare_source, new_source=package_source)
        if diff is not None and compare is not None
        else None,
        "reproducibility": {
            "validate": validate_command,
            "test": test_command,
            "diff": diff_command or (f"python3 -m sit.cli diff {compare.root} {package.root}" if compare is not None else None),
        },
    }
    return payload


def render_report_markdown(data: dict[str, Any]) -> str:
    package = data["package"]
    validation = data["validation"]
    test_result = data["golden_tests"]

    lines: list[str] = [
        f"# {package['name'] or 'Skill Package'} {package['version'] or '<unknown>'} SIT Report",
        "",
        f"Date: {data['date']}",
        "",
        "## Package",
        "",
        f"- Name: `{package['name']}`",
        f"- Version: `{package['version']}`",
    ]
    if package.get("source"):
        lines.append(f"- Source: `{package['source']}`")
    else:
        lines.extend([f"- Root: `{package['root']}`", f"- Manifest: `{package['manifest']}`"])

    if package.get("description"):
        lines.append(f"- Description: {package['description']}")

    lines.extend(
        [
            "",
            "## Validation",
            "",
            f"- Result: {validation['status']}",
        ]
    )
    lines.extend(f"- `{_display_text(message, data)}`" for message in validation["messages"])

    lines.extend(["", "## Golden Tests", ""])
    if test_result["status"] == "skipped":
        lines.append("- Skipped because validation failed.")
    else:
        lines.append(f"- Result: {test_result['status']}")
        lines.extend(f"- `{_display_text(message, data)}`" for message in test_result["messages"])

    if data["diff"] is not None:
        diff = data["diff"]
        lines.extend(
            [
                "",
                "## Diff",
                "",
                f"- Baseline: `{diff['old']['name']}@{diff['old']['version']}`",
                f"- Current: `{diff['new']['name']}@{diff['new']['version']}`",
            ]
        )
        lines.extend(f"- `{_display_text(message, data)}`" for message in diff["messages"])

    lines.extend(
        [
            "",
            "## Reproducibility",
            "",
            "- Re-run validation with:",
            f"  `{data['reproducibility']['validate']}`",
            "- Re-run golden schema tests with:",
            f"  `{data['reproducibility']['test']}`",
        ]
    )

    if data["reproducibility"]["diff"] is not None:
        lines.extend(
            [
                "- Re-run package diff with:",
                f"  `{data['reproducibility']['diff']}`",
            ]
        )

    return "\n".join(lines) + "\n"


def render_report_html(data: dict[str, Any]) -> str:
    package = data["package"]
    validation = data["validation"]
    tests = data["golden_tests"]
    diff = data.get("diff")
    risk = diff["risk"] if diff is not None else "no-compare"
    suggested_bump = diff["suggested_bump"] if diff is not None else "none"
    test_percent = _percent(tests.get("passed"), tests.get("total"))
    title = f"{package['name']} {package['version']} SitHub Report"

    html = [
        "<!doctype html>",
        '<html lang="en">',
        "<head>",
        '<meta charset="utf-8">',
        '<meta name="viewport" content="width=device-width, initial-scale=1">',
        f"<title>{escape(title)}</title>",
        "<style>",
        _html_css(),
        "</style>",
        "</head>",
        "<body>",
        '<main class="page">',
        '<section class="hero">',
        '<div class="hero-copy">',
        '<p class="eyebrow">SitHub semantic control report</p>',
        f"<h1>{escape(str(package['name']))}</h1>",
        f"<p class=\"subtitle\">Version {escape(str(package['version']))} - {escape(str(data['date']))}</p>",
        "</div>",
        '<div class="risk-panel">',
        '<span class="panel-label">Diff risk</span>',
        f'<strong class="risk {escape(_token_class(risk))}">{escape(risk)}</strong>',
        f"<span>Suggested bump: <b>{escape(suggested_bump)}</b></span>",
        "</div>",
        "</section>",
        '<section class="metrics" aria-label="Status metrics">',
        _metric("Validation", validation["status"], validation["ok"]),
        _metric("Golden Tests", tests["status"], tests.get("ok")),
        _metric("Cases Passed", _count_label(tests.get("passed"), tests.get("total")), tests.get("ok")),
        _metric("Version Bump", suggested_bump, None),
        "</section>",
        '<section class="band">',
        '<div class="section-head">',
        "<h2>Golden Test Progress</h2>",
        f"<span>{escape(_count_label(tests.get('passed'), tests.get('total')))}</span>",
        "</div>",
        '<div class="progress" aria-label="Golden test pass rate">',
        f'<div class="progress-fill" style="width: {test_percent}%"></div>',
        "</div>",
        "</section>",
        '<section class="columns">',
        _message_section("Validation", _display_messages(validation["messages"], data), "validation"),
        _message_section("Golden Tests", _display_messages(tests["messages"], data), "tests"),
        "</section>",
    ]

    if diff is not None:
        counts = _diff_counts(diff["events"])
        html.extend(
            [
                '<section class="band">',
                '<div class="section-head">',
                "<h2>Semantic Diff</h2>",
                f'<span class="risk {escape(_token_class(risk))}">{escape(risk)}</span>',
                "</div>",
                '<div class="diff-toolbar" aria-label="Semantic diff filters">',
                '<button type="button" class="filter active" data-filter="all">All '
                f'<span>{counts["all"]}</span></button>',
                '<button type="button" class="filter" data-filter="breaking">Breaking '
                f'<span>{counts["breaking"]}</span></button>',
                '<button type="button" class="filter" data-filter="changed">Changed '
                f'<span>{counts["changed"]}</span></button>',
                '<button type="button" class="filter" data-filter="info">Info '
                f'<span>{counts["info"]}</span></button>',
                '<button type="button" class="toggle-long" data-toggle-long>Expand long diff</button>',
                "</div>",
                '<div class="timeline">',
                *_diff_items(diff["events"], data),
                "</div>",
                "</section>",
            ]
        )

    html.extend(
        [
            '<section class="band">',
            '<div class="section-head">',
            "<h2>Reproduce</h2>",
            "<span>local commands</span>",
            "</div>",
            "<pre><code>",
            escape("\n".join(_repro_commands(data))),
            "</code></pre>",
            "</section>",
            "<script>",
            _html_script(),
            "</script>",
            "</main>",
            "</body>",
            "</html>",
        ]
    )
    return "\n".join(html) + "\n"


def _test_result_dict(result: CheckResult | None) -> dict[str, Any]:
    if result is None:
        return {
            "status": "skipped",
            "ok": None,
            "passed": None,
            "total": None,
            "summary": None,
            "messages": [],
        }
    passed, total, summary = _parse_summary(result.messages)
    return {
        "status": "pass" if result.ok else "fail",
        "ok": result.ok,
        "passed": passed,
        "total": total,
        "summary": summary,
        "messages": result.messages,
    }


def _parse_summary(messages: list[str]) -> tuple[int | None, int | None, str | None]:
    prefix = "SUMMARY "
    suffix = " golden cases passed"
    for message in reversed(messages):
        if not message.startswith(prefix) or not message.endswith(suffix):
            continue
        counts = message[len(prefix) : -len(suffix)]
        left, separator, right = counts.partition("/")
        if not separator:
            continue
        try:
            return int(left), int(right), message
        except ValueError:
            continue
    return None, None, None


def _package_ref(package: SkillPackage, *, source: str | None = None) -> dict[str, str | None]:
    data = {
        "name": package.name or "<unknown>",
        "version": package.version or "<unknown>",
        "description": package.description,
        "root": str(package.root),
        "manifest": str(package.manifest_path),
    }
    if source is not None:
        data["source"] = source
    return data


def _metric(title: str, value: str, ok: bool | None) -> str:
    state = "neutral" if ok is None else ("pass" if ok else "fail")
    return "\n".join(
        [
            '<div class="metric">',
            f"<span>{escape(title)}</span>",
            f'<strong class="{state}">{escape(str(value))}</strong>',
            "</div>",
        ]
    )


def _message_section(title: str, messages: list[str], section_class: str) -> str:
    lines = [f'<section class="band compact {section_class}">', f"<h2>{escape(title)}</h2>", '<ul class="message-list">']
    if messages:
        lines.extend(f"<li>{escape(message)}</li>" for message in messages)
    else:
        lines.append("<li>&lt;none&gt;</li>")
    lines.extend(["</ul>", "</section>"])
    return "\n".join(lines)


def _diff_items(events: list[dict[str, Any]], data: dict[str, Any]) -> list[str]:
    items: list[str] = []
    for index, event in enumerate(events, start=1):
        severity = _token_class(str(event.get("severity", "info")))
        category = str(event.get("category", "event"))
        message = _display_text(str(event.get("message", "")), data)
        schema_path = _schema_path_from_message(message)
        long_class = " long" if len(message) > 120 else ""
        items.append(
            "\n".join(
                [
                    f'<article class="diff-item {escape(severity)}{long_class}" data-severity="{escape(severity)}">',
                    '<div class="diff-meta">',
                    f"<span>{escape(category)}</span>",
                    f"<span>#{index}</span>",
                    "</div>",
                    f"{_path_badge(schema_path)}",
                    f"<p>{escape(message)}</p>",
                    "</article>",
                ]
            )
        )
    return items


def _diff_counts(events: list[dict[str, Any]]) -> dict[str, int]:
    counts = {"all": len(events), "breaking": 0, "changed": 0, "info": 0}
    for event in events:
        severity = _token_class(str(event.get("severity", "info")))
        if severity in counts:
            counts[severity] += 1
        else:
            counts["info"] += 1
    return counts


def _path_badge(path: str | None) -> str:
    if path is None:
        return ""
    return f'<code class="schema-path">{escape(path)}</code>'


def _schema_path_from_message(message: str) -> str | None:
    if not message.startswith("SCHEMA "):
        return None
    markers = (
        " property added ",
        " property removed ",
        " property became required ",
        " property became optional ",
        " property type changed ",
        " enum removed values ",
        " enum added values ",
        " enum added ",
        " enum removed ",
        " additionalProperties restricted ",
        " additionalProperties relaxed ",
        " additionalProperties changed ",
        " constraint changed ",
        " items added ",
        " items removed ",
        " items changed ",
        " oneOf branch changed ",
        " oneOf branch added ",
        " oneOf branch removed ",
        " oneOf branches reordered ",
        " anyOf branch changed ",
        " anyOf branch added ",
        " anyOf branch removed ",
        " anyOf branches reordered ",
        " allOf branch changed ",
        " allOf branch added ",
        " allOf branch removed ",
        " allOf branches reordered ",
        " $ref target changed ",
        " $ref added ",
        " $ref removed ",
        " unresolved $ref ",
    )
    for marker in markers:
        if marker not in message:
            continue
        tail = message.split(marker, 1)[1]
        for separator in (" (", ":"):
            tail = tail.split(separator, 1)[0]
        tail = tail.strip()
        return tail if tail and tail != "<root>" else "<root>"
    return None


def _repro_commands(data: dict[str, Any]) -> list[str]:
    repro = data.get("reproducibility", {})
    return [command for command in (repro.get("validate"), repro.get("test"), repro.get("diff")) if command]


def _display_messages(messages: list[str], data: dict[str, Any]) -> list[str]:
    return [_display_text(message, data) for message in messages]


def _display_text(text: str, data: dict[str, Any]) -> str:
    for root, source in _source_replacements(data):
        text = text.replace(root, source)
    return text


def _source_replacements(data: dict[str, Any]) -> list[tuple[str, str]]:
    refs = [data.get("package")]
    diff = data.get("diff")
    if isinstance(diff, dict):
        refs.extend([diff.get("old"), diff.get("new")])

    replacements: list[tuple[str, str]] = []
    for ref in refs:
        if not isinstance(ref, dict):
            continue
        root = ref.get("root")
        source = ref.get("source")
        if isinstance(root, str) and isinstance(source, str):
            replacements.append((root.rstrip("/"), source.rstrip("/")))
    return sorted(set(replacements), key=lambda item: len(item[0]), reverse=True)


def _percent(passed: int | None, total: int | None) -> int:
    if not passed or not total:
        return 0
    return max(0, min(100, round((passed / total) * 100)))


def _count_label(passed: int | None, total: int | None) -> str:
    if passed is None or total is None:
        return "n/a"
    return f"{passed}/{total}"


def _token_class(value: str) -> str:
    return "".join(char if char.isalnum() else "-" for char in value.lower()).strip("-") or "neutral"


def _html_css() -> str:
    return """
:root {
  color-scheme: light;
  --ink: #17202a;
  --muted: #5b6472;
  --line: #d9dee7;
  --paper: #f7f8fb;
  --panel: #ffffff;
  --blue: #2457d6;
  --green: #147d64;
  --red: #b42318;
  --amber: #a05a00;
  --violet: #7047a8;
}
* { box-sizing: border-box; }
body {
  margin: 0;
  font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
  color: var(--ink);
  background: var(--paper);
  letter-spacing: 0;
}
.page {
  width: min(1180px, calc(100% - 32px));
  margin: 0 auto;
  padding: 28px 0 48px;
}
.hero {
  min-height: 240px;
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(280px, 380px);
  gap: 24px;
  align-items: stretch;
  padding: 32px;
  color: #fff;
  background:
    linear-gradient(120deg, rgba(23, 32, 42, .88), rgba(36, 87, 214, .74)),
    url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='960' height='360' viewBox='0 0 960 360'%3E%3Crect width='960' height='360' fill='%23222f3e'/%3E%3Cg fill='none' stroke='%23ffffff' stroke-opacity='.18'%3E%3Cpath d='M80 270 C180 170 260 210 350 110 S560 80 660 160 790 280 900 110' stroke-width='5'/%3E%3Cpath d='M60 100 H900 M60 180 H900 M60 260 H900'/%3E%3Cpath d='M160 40 V320 M360 40 V320 M560 40 V320 M760 40 V320'/%3E%3C/g%3E%3Cg fill='%23ffffff' fill-opacity='.92'%3E%3Ccircle cx='350' cy='110' r='9'/%3E%3Ccircle cx='660' cy='160' r='9'/%3E%3Ccircle cx='900' cy='110' r='9'/%3E%3C/g%3E%3C/svg%3E");
  background-size: cover;
  background-position: center;
  border-radius: 8px;
}
.hero h1 {
  margin: 0;
  font-size: 42px;
  line-height: 1.05;
  overflow-wrap: anywhere;
}
.eyebrow, .subtitle {
  margin: 0 0 12px;
  color: rgba(255,255,255,.78);
}
.subtitle { margin-top: 14px; }
.risk-panel {
  align-self: end;
  display: grid;
  gap: 10px;
  min-height: 150px;
  padding: 20px;
  background: rgba(255,255,255,.12);
  border: 1px solid rgba(255,255,255,.24);
  border-radius: 8px;
}
.panel-label { color: rgba(255,255,255,.76); }
.risk-panel strong { font-size: 28px; line-height: 1.1; }
.metrics {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 14px;
  margin: 18px 0;
}
.metric, .band {
  background: var(--panel);
  border: 1px solid var(--line);
  border-radius: 8px;
}
.metric {
  min-height: 112px;
  padding: 18px;
  display: grid;
  align-content: space-between;
}
.metric span, .section-head span, .diff-item span {
  color: var(--muted);
  font-size: 13px;
}
.metric strong {
  font-size: 25px;
  overflow-wrap: anywhere;
}
.pass { color: var(--green); }
.fail, .breaking, .breaking-change { color: var(--red); }
.changed, .review-required { color: var(--amber); }
.neutral, .info, .no-change, .no-compare { color: var(--blue); }
.band {
  padding: 22px;
  margin-top: 18px;
}
.compact { margin-top: 0; }
.section-head {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  align-items: center;
  margin-bottom: 16px;
}
h2 {
  margin: 0;
  font-size: 20px;
}
.progress {
  height: 14px;
  overflow: hidden;
  background: #e9edf3;
  border-radius: 999px;
}
.progress-fill {
  height: 100%;
  background: linear-gradient(90deg, var(--green), var(--blue));
}
.columns {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 18px;
  margin-top: 18px;
}
.message-list {
  margin: 14px 0 0;
  padding-left: 18px;
}
.message-list li {
  margin: 8px 0;
  line-height: 1.45;
  overflow-wrap: anywhere;
}
.timeline {
  display: grid;
  gap: 10px;
}
.diff-toolbar {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 16px;
}
.filter, .toggle-long {
  min-height: 36px;
  border: 1px solid var(--line);
  border-radius: 6px;
  background: #fff;
  color: var(--ink);
  padding: 0 12px;
  font: inherit;
  cursor: pointer;
}
.filter span {
  color: var(--muted);
  margin-left: 4px;
}
.filter.active {
  color: #fff;
  background: var(--blue);
  border-color: var(--blue);
}
.filter.active span {
  color: rgba(255,255,255,.82);
}
.diff-item {
  border-left: 4px solid var(--blue);
  padding: 12px 14px;
  background: #fbfcff;
  border-radius: 6px;
}
.diff-item.hidden { display: none; }
.diff-item.long:not(.expanded) p {
  max-height: 44px;
  overflow: hidden;
}
.diff-item.breaking { border-color: var(--red); }
.diff-item.changed { border-color: var(--amber); }
.diff-meta {
  display: flex;
  justify-content: space-between;
  gap: 12px;
}
.schema-path {
  display: inline-block;
  margin-top: 8px;
  max-width: 100%;
  padding: 4px 7px;
  color: #24364b;
  background: #eef3fb;
  border: 1px solid #d7e1ef;
  border-radius: 5px;
  overflow-wrap: anywhere;
}
.diff-item p {
  margin: 5px 0 0;
  overflow-wrap: anywhere;
}
pre {
  margin: 0;
  padding: 16px;
  overflow: auto;
  background: #15202b;
  color: #edf3f8;
  border-radius: 8px;
}
code {
  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
  font-size: 13px;
}
@media (max-width: 820px) {
  .hero, .metrics, .columns {
    grid-template-columns: 1fr;
  }
  .hero {
    padding: 24px;
  }
  .hero h1 {
    font-size: 32px;
  }
}
""".strip()


def _html_script() -> str:
    return """
document.querySelectorAll('[data-filter]').forEach((button) => {
  button.addEventListener('click', () => {
    const filter = button.dataset.filter;
    document.querySelectorAll('[data-filter]').forEach((item) => item.classList.remove('active'));
    button.classList.add('active');
    document.querySelectorAll('.diff-item').forEach((item) => {
      item.classList.toggle('hidden', filter !== 'all' && item.dataset.severity !== filter);
    });
  });
});
document.querySelectorAll('[data-toggle-long]').forEach((button) => {
  button.addEventListener('click', () => {
    const expand = button.dataset.expanded !== 'true';
    button.dataset.expanded = String(expand);
    button.textContent = expand ? 'Collapse long diff' : 'Expand long diff';
    document.querySelectorAll('.diff-item.long').forEach((item) => item.classList.toggle('expanded', expand));
  });
});
""".strip()
