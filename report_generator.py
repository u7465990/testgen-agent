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
        print(f"  Duration:       {report.duration_seconds:.1f}s")
        print(f"{line}")

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
