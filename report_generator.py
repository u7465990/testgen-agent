"""Report generation — JSON, CSV, and console output."""

from __future__ import annotations

import csv
import json
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional

from method_extractor import MethodInfo


@dataclass
class MethodReport:
    """Results for one targeted method."""
    fqn: str
    signature: str
    modifiers: str
    tests_generated: int = 0
    tests_compiled: int = 0
    tests_runnable: int = 0
    targets: List[str] = field(default_factory=list)


@dataclass
class AgentReport:
    """Full report from one agent run."""

    # Input
    project_path: str = ""
    build_tool: str = ""

    # Extraction
    source_files_found: int = 0
    methods_found: int = 0
    methods_targeted: int = 0

    # Generation
    tests_generated: int = 0
    tests_compiled: int = 0
    tests_runnable: int = 0
    compilation_rate: float = 0.0

    # Coverage
    branch_coverage: Optional[float] = None
    line_coverage: Optional[float] = None

    # Quality — how good the tests are, not just whether they compile.
    # `mutation_score` is the headline: fraction of injected faults the
    # generated tests catch. None means the analysis did not run.
    total_test_methods: int = 0
    empty_test_classes: int = 0
    empty_test_class_names: List[str] = field(default_factory=list)
    assertion_density: float = 0.0
    mutation_score: Optional[float] = None
    mutations_killed: int = 0
    mutations_total: int = 0
    mutations_no_coverage: int = 0
    # Test classes excluded from mutation analysis because they failed
    # before mutation — PiTest requires a green suite.
    mutations_excluded_tests: List[str] = field(default_factory=list)
    # Per-class breakdown: {"name", "killed", "total", "score"}
    mutation_by_class: List[Dict[str, Any]] = field(default_factory=list)

    # Per-method details
    method_reports: List[MethodReport] = field(default_factory=list)

    # Errors
    errors: List[str] = field(default_factory=list)

    # Timing
    duration_seconds: float = 0.0

    # Machine-readable test file list
    test_files: List[Dict[str, Any]] = field(default_factory=list)


class ReportGenerator:
    """Generates JSON, CSV, and console output from an AgentReport."""

    # ── Console ───────────────────────────────────────────────

    @staticmethod
    def print_console(report: AgentReport) -> None:
        """Human-readable summary."""
        line = "─" * 55
        print(f"\n{line}")
        print(f"  Test Generation Agent — Summary")
        print(f"{line}")
        print(f"  Project:        {report.project_path}")
        print(f"  Build tool:     {report.build_tool}")
        print(f"  Source files:   {report.source_files_found}")
        print(f"  Methods found:  {report.methods_found}")
        print(f"  Methods targeted: {report.methods_targeted}")
        print(f"  Tests generated:  {report.tests_generated}")
        print(f"  Tests compiled:   {report.tests_compiled}")
        print(f"  Compilation rate: {report.compilation_rate:.1%}")
        if report.branch_coverage is not None:
            print(f"  Branch coverage:  {report.branch_coverage:.1%}")
        if report.line_coverage is not None:
            print(f"  Line coverage:    {report.line_coverage:.1%}")

        # ── Test quality ──────────────────────────────────────
        # Compilation rate alone is not evidence that the tests are
        # meaningful: an empty test class compiles perfectly.
        print(f"  {'-' * 51}")
        print(f"  Test methods:     {report.total_test_methods}")
        print(f"  Assertion density: {report.assertion_density:.2f} per test")
        if report.empty_test_classes:
            print(f"  Empty test classes: {report.empty_test_classes} "
                  f"(compile, but contain no @Test)")
        else:
            print(f"  Empty test classes: 0")
        if report.mutation_score is not None:
            print(f"  Mutation score:   {report.mutation_score:.1%} "
                  f"({report.mutations_killed}/{report.mutations_total} "
                  f"mutants killed)")
            if report.mutations_no_coverage:
                print(f"    ({report.mutations_no_coverage} mutants were "
                      f"never even reached by a test)")
            if report.mutations_excluded_tests:
                print(f"    ({len(report.mutations_excluded_tests)} test "
                      f"class(es) excluded — they fail before mutation)")
        else:
            print(f"  Mutation score:   n/a (analysis skipped or unavailable)")
        print(f"  Duration:       {report.duration_seconds:.1f}s")
        print(f"{line}")

        # Weakest classes by mutation score — where the tests are shallowest.
        if report.mutation_by_class:
            weakest = sorted(
                report.mutation_by_class, key=lambda c: (c["score"], c["name"])
            )[:5]
            if any(c["total"] for c in weakest):
                print(f"\n  Weakest classes (mutation score):")
                for c in weakest:
                    if not c["total"]:
                        continue
                    name = c["name"]
                    if len(name) > 46:
                        name = name[:43] + "..."
                    print(f"  {name:<46} {c['score']:>6.1%}  "
                          f"({c['killed']}/{c['total']})")

        if report.errors:
            print(f"\n  Errors ({len(report.errors)}):")
            for e in report.errors:
                print(f"    - {e}")

        if report.method_reports:
            print(f"\n  Per-method breakdown:")
            print(f"  {'Method':<50} {'Gen':>4} {'Cmp':>4} {'Run':>4}")
            print(f"  {'-'*50} {'-'*4} {'-'*4} {'-'*4}")
            for mr in report.method_reports:
                mname = mr.fqn.split("(")[0]
                if len(mname) > 48:
                    mname = mname[:45] + "..."
                print(
                    f"  {mname:<50} {mr.tests_generated:>4} "
                    f"{mr.tests_compiled:>4} {mr.tests_runnable:>4}"
                )

    # ── Markdown ──────────────────────────────────────────────

    @staticmethod
    def generate_markdown(
        report: AgentReport,
        path: Path,
        reproduce_command: Optional[str] = None,
    ) -> None:
        """Write a human-readable Markdown report.

        This is the report a person reads (or commits, or pastes into a CV).
        Mutation score is the headline: compilation rate alone does not show
        whether the tests assert anything — an empty test class compiles.
        """
        import datetime

        stamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
        project_name = Path(report.project_path).name or report.project_path
        out: List[str] = []

        out.append(f"# TestGen Agent 报告 — {project_name}")
        out.append("")
        out.append(
            f"> 生成于 {stamp} · 耗时 {report.duration_seconds:.1f}s · "
            f"构建工具 `{report.build_tool or 'unknown'}`"
        )
        out.append("")

        # ── Headline metrics ──
        out.append("## 核心指标")
        out.append("")
        out.append("| 指标 | 值 |")
        out.append("|---|---|")
        if report.mutation_score is not None:
            out.append(
                f"| **Mutation score** | **{report.mutation_score:.1%}** "
                f"({report.mutations_killed}/{report.mutations_total} "
                f"mutants killed) |"
            )
        else:
            out.append("| **Mutation score** | _未运行_ |")
        out.append(
            f"| 编译通过率 | {report.compilation_rate:.1%} "
            f"({report.tests_compiled}/{report.tests_generated}) |"
        )
        if report.tests_generated:
            runnable_rate = report.tests_runnable / report.tests_generated
            out.append(
                f"| 可运行率 | {runnable_rate:.1%} "
                f"({report.tests_runnable}/{report.tests_generated}) |"
            )
        out.append(f"| 断言密度 | {report.assertion_density:.2f} / 测试 |")
        out.append(f"| 测试方法总数 | {report.total_test_methods} |")
        out.append(f"| 空测试类 | {report.empty_test_classes} |")
        out.append("")

        verdict = ReportGenerator._mutation_verdict(report.mutation_score)
        if verdict:
            out.append(verdict)
            out.append("")

        # ── Scope ──
        out.append("## 覆盖范围")
        out.append("")
        out.append(f"- 源文件: **{report.source_files_found}**")
        out.append(f"- 提取方法: **{report.methods_found}**")
        out.append(f"- 目标方法: **{report.methods_targeted}**")
        out.append(f"- 生成测试: **{report.tests_generated}**")
        out.append("")

        # ── Weakest classes ──
        scored = [c for c in report.mutation_by_class if c.get("total")]
        if scored:
            out.append("## 最弱的类")
            out.append("")
            out.append("按 mutation score 升序 —— 测试最浅的地方排在最前。")
            out.append("")
            out.append("| 类 | Mutation score | Killed |")
            out.append("|---|---|---|")
            for c in sorted(scored, key=lambda x: (x["score"], x["name"])):
                out.append(
                    f"| `{c['name']}` | {c['score']:.1%} | "
                    f"{c['killed']}/{c['total']} |"
                )
            out.append("")

        # ── Needs human attention ──
        # Each block is emitted separately (blank line between) so a strict
        # Markdown renderer does not fold the next heading into the list.
        blocks: List[List[str]] = []
        if report.mutations_excluded_tests:
            block = [
                f"**{len(report.mutations_excluded_tests)} 个测试运行时失败**"
                f"（已排除出 mutation 分析，PiTest 要求测试全绿）:"
            ]
            block += [f"- `{n}`" for n in report.mutations_excluded_tests]
            blocks.append(block)
        if report.empty_test_class_names:
            block = [
                f"**{len(report.empty_test_class_names)} 个空测试类**"
                f"（编译通过，但不含 `@Test` 方法）:"
            ]
            block += [f"- `{n}`" for n in report.empty_test_class_names]
            blocks.append(block)
        if report.mutations_no_coverage:
            blocks.append([
                f"**{report.mutations_no_coverage} 个 mutant 从未被执行**"
                f" —— 对应代码分支没有任何测试触及。"
            ])
        if report.errors:
            blocks.append(
                [f"**{len(report.errors)} 个错误**:"]
                + [f"- {e}" for e in report.errors]
            )

        if blocks:
            out.append("## 需要人工介入")
            out.append("")
            for i, block in enumerate(blocks):
                if i:
                    out.append("")
                out.extend(block)
            out.append("")

        # ── Per-method detail ──
        if report.method_reports:
            out.append("## 每方法明细")
            out.append("")
            out.append("| 方法 | 生成 | 编译 | 可运行 |")
            out.append("|---|---:|---:|---:|")
            for mr in sorted(report.method_reports, key=lambda m: m.fqn):
                out.append(
                    f"| `{mr.fqn}` | {mr.tests_generated} | "
                    f"{mr.tests_compiled} | {mr.tests_runnable} |"
                )
            out.append("")

        # ── Reproduce ──
        if reproduce_command:
            out.append("## 复现")
            out.append("")
            out.append("```bash")
            out.append(reproduce_command)
            out.append("```")
            out.append("")

        out.append("---")
        out.append("*由 TestGen Agent 自动生成。*")

        path.write_text("\n".join(out) + "\n", encoding="utf-8")

    @staticmethod
    def _mutation_verdict(score: Optional[float]) -> str:
        """One-line, deterministic reading of the mutation score."""
        if score is None:
            return ""
        if score >= 0.80:
            band = "良好 —— 与人工撰写测试的典型水平（约 80–85%）相当"
        elif score >= 0.60:
            band = "一般 —— 有相当比例的行为没有被任何断言校验"
        else:
            band = "偏弱 —— 多数测试可能只执行了代码路径，但没有校验行为"
        return f"**结论：{band}。**"

    # ── JSON ──────────────────────────────────────────────────

    @staticmethod
    def generate_json(report: AgentReport, path: Path) -> None:
        """Write a JSON summary file."""
        data = asdict(report)
        # Convert dataclasses to dicts
        data["method_reports"] = [
            asdict(mr) for mr in report.method_reports
        ]
        path.write_text(
            json.dumps(data, indent=2, default=str), encoding="utf-8"
        )

    # ── CSV ───────────────────────────────────────────────────

    @staticmethod
    def generate_csv(
        report: AgentReport,
        path: Path,
        test_files: Optional[List[Dict[str, Any]]] = None,
    ) -> None:
        """
        Write a CSV file compatible with the existing pipeline format.
        Columns match Test_Data_with_Runnable.csv where possible.
        """
        rows = test_files or report.test_files
        if not rows:
            # Write summary as a single row
            with path.open("w", newline="", encoding="utf-8") as f:
                w = csv.writer(f)
                w.writerow(["Metric", "Value"])
                for key, val in asdict(report).items():
                    if not isinstance(val, (list, dict)):
                        w.writerow([key, val])
            return

        # Column order matching existing pipeline
        fieldnames = [
            "Project", "FQN", "Signature", "SourceCode",
            "BranchConditions", "ClassContext", "AllowedImports",
            "ThrowsExceptions", "Modifiers", "GenerationTarget",
            "GeneratedCode", "CodeAfterFormatting", "SavedPath",
            "Runnable",
        ]
        with path.open("w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
            w.writeheader()
            for row in rows:
                w.writerow(row)

    @staticmethod
    def per_method_row(
        method: MethodInfo, target: str, code: str, saved_path: str,
        runnable: bool,
    ) -> Dict[str, str]:
        """Build a CSV row for one test file."""
        return {
            "Project": method.project_name,
            "FQN": method.fqn,
            "Signature": method.signature,
            "SourceCode": method.source_code,
            "BranchConditions": "; ".join(method.branch_conditions),
            "ClassContext": method.class_context,
            "AllowedImports": "\n".join(method.allowed_imports),
            "ThrowsExceptions": ", ".join(method.throws_exceptions)
                if method.throws_exceptions else "none",
            "Modifiers": " ".join(method.modifiers),
            "GenerationTarget": target,
            "GeneratedCode": code,
            "CodeAfterFormatting": code,
            "SavedPath": saved_path,
            "Runnable": "yes" if runnable else "no",
        }
