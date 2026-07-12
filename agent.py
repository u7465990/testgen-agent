"""TestGeneratorAgent — the main orchestrator that ties everything together."""

from __future__ import annotations

import time
from pathlib import Path
from typing import Dict, List, Optional

from config import AgentConfig
from java_analyzer import JavaProjectAnalyzer, SourceFile
from method_extractor import MethodExtractor, MethodInfo
from target_generator import TargetGenerator
from prompt_manager import PromptManager
from llm_client import LLMClient
from test_writer import TestWriter
from compiler import JavaCompiler
from repair_loop import RepairLoop, TestFile
from report_generator import AgentReport, MethodReport, ReportGenerator


class TestGeneratorAgent:
    """
    Orchestrates the full pipeline:
      1. Analyze project → discover source files
      2. Extract methods → MethodInfo list
      3. Filter methods → targeted method list
      4. Generate targets → (MethodInfo, target_string) pairs
      5. Generate tests via LLM → TestFile list
      6. Repair compilation → compilable TestFile list
      7. Generate report → AgentReport
    """

    def __init__(self, config: AgentConfig):
        self.config = config
        self.project_path = config.project_path
        self.project_name = config.project_path.name

        # Sub-modules
        self.analyzer = JavaProjectAnalyzer(config.project_path)
        self.extractor = MethodExtractor(project_name=self.project_name)
        self.target_gen = TargetGenerator(
            target_types=config.target_types
        )
        self.prompt_mgr = PromptManager(
            Path(__file__).parent / "prompts"
        )
        self.llm = LLMClient(config)
        self.test_dir = (
            Path(config.output_dir)
            if config.output_dir
            else self.analyzer.find_test_directory()
        )
        self.writer = TestWriter(self.test_dir)
        self.compiler = JavaCompiler(config)
        self.repairer = RepairLoop(
            self.llm, self.prompt_mgr, self.compiler,
            self.writer, config
        )

    # ── Main entry point ──────────────────────────────────────

    def run(self) -> AgentReport:
        """Execute the full pipeline and return a report."""
        start = time.time()
        report = AgentReport()
        report.project_path = str(self.project_path)
        report.build_tool = self.analyzer.detect_build_tool()

        # ── Phase 1: Extraction ───────────────────────────────
        print("\n=== Phase 1: Project Analysis ===")
        sources = self.analyzer.find_source_files()
        report.source_files_found = len(sources)
        if not sources:
            report.errors.append(
                "No Java source files found in project"
            )
            report.duration_seconds = time.time() - start
            return report

        print(f"  Found {len(sources)} source files")

        all_methods: List[MethodInfo] = []
        for src in sources:
            methods = self.extractor.extract_methods(src)
            all_methods.extend(methods)
        report.methods_found = len(all_methods)
        print(f"  Extracted {len(all_methods)} methods")

        # ── Phase 2: Filtering ────────────────────────────────
        print("\n=== Phase 2: Method Filtering ===")
        targeted = self._filter_methods(all_methods)
        report.methods_targeted = len(targeted)
        print(f"  Targeting {len(targeted)} methods "
              f"(filtered from {len(all_methods)})")

        if not targeted:
            report.errors.append("No methods matched the filter criteria")
            report.duration_seconds = time.time() - start
            return report

        # ── Phase 3: Target Generation ────────────────────────
        print("\n=== Phase 3: Target Generation ===")
        method_targets: List[tuple[MethodInfo, str]] = []
        for method in targeted:
            targets = self.target_gen.generate_targets(method)
            for t in targets:
                method_targets.append((method, t))
        print(f"  Generated {len(method_targets)} test targets")

        # ── Phase 4: LLM Test Generation ─────────────────────
        print("\n=== Phase 4: Test Generation ===")
        test_files: List[TestFile] = []
        for i, (method, target) in enumerate(method_targets):
            print(
                f"  [{i+1}/{len(method_targets)}] "
                f"{method.fqn} — {target[:50]}..."
            )
            try:
                sys_prompt, user_prompt = \
                    self.prompt_mgr.render_generate_prompt(method, target)
                raw_code = self.llm.generate(sys_prompt, user_prompt)
            except Exception as e:
                report.errors.append(
                    f"LLM call failed for {method.fqn}: {e}"
                )
                print(f"    ERROR: {e}")
                continue

            class_name = self.writer.generate_class_name(
                method, target, i
            )
            package_name = self.writer.get_package(method)
            formatted = self.writer.format_code(
                raw_code, class_name, package_name
            )
            file_path = self.writer.write_test_file(
                formatted, package_name, class_name
            )
            test_file = TestFile(
                path=file_path,
                method=method,
                target=target,
                source_code=formatted,
                class_name=class_name,
                package_name=package_name,
            )
            test_files.append(test_file)
            print(f"    -> Saved: {file_path.name}")

        report.tests_generated = len(test_files)
        print(f"  Generated {len(test_files)} test files")

        if not test_files:
            report.duration_seconds = time.time() - start
            return report

        # ── Phase 5: Compilation Repair ──────────────────────
        print("\n=== Phase 5: Compilation Repair ===")
        compiled: List[TestFile] = []
        for tf in test_files:
            print(f"  [{test_files.index(tf)+1}/{len(test_files)}] "
                  f"{tf.path.name}")
            result = self.repairer.repair_compilation(tf)
            compiled.append(result)
            if result.compiles:
                report.tests_compiled += 1

        print(f"  Compiled: {report.tests_compiled}/{len(test_files)}")

        # ── Phase 6: Coverage Improvement (MVP) ──────────────
        print("\n=== Phase 6: Coverage Improvement ===")
        additional = self.repairer.improve_coverage(compiled)
        compiled.extend(additional)
        report.tests_generated += len(additional)

        # ── Phase 7: Final verification ─────────────────────
        print("\n=== Phase 7: Final Verification ===")
        report.tests_runnable = 0
        classpath = self.compiler.resolve_classpath()
        for tf in compiled:
            success, _ = self.compiler.compile(tf.path, classpath)
            tf.runnable = success
            if success:
                report.tests_runnable += 1

        report.compilation_rate = (
            report.tests_runnable / report.tests_generated
            if report.tests_generated > 0 else 0.0
        )

        # ── Build per-method reports ─────────────────────────
        method_map: Dict[str, MethodReport] = {}
        for tf in compiled:
            key = tf.method.fqn
            if key not in method_map:
                method_map[key] = MethodReport(
                    fqn=key,
                    signature=tf.method.signature,
                    modifiers=" ".join(tf.method.modifiers),
                )
            mr = method_map[key]
            mr.tests_generated += 1
            if tf.compiles:
                mr.tests_compiled += 1
            if tf.runnable:
                mr.tests_runnable += 1

        report.method_reports = list(method_map.values())

        # ── Build test file list for CSV ─────────────────────
        for tf in compiled:
            report.test_files.append(
                ReportGenerator.per_method_row(
                    tf.method, tf.target, tf.source_code,
                    str(tf.path), tf.runnable,
                )
            )

        report.duration_seconds = time.time() - start

        # ── Output ──────────────────────────────────────────
        ReportGenerator.print_console(report)

        # Write report files
        report_dir = self.project_path / "target/testgen-agent"
        report_dir.mkdir(parents=True, exist_ok=True)

        if self.config.report_format in ("json", "both"):
            ReportGenerator.generate_json(
                report, report_dir / "report.json"
            )
            print(f"\n  JSON report: {report_dir / 'report.json'}")

        if self.config.report_format in ("csv", "both"):
            ReportGenerator.generate_csv(
                report, report_dir / "report.csv", report.test_files
            )
            print(f"  CSV report:  {report_dir / 'report.csv'}")

        print(f"\n  Test files are in: {self.test_dir}")
        print("  Done.")

        return report

    # ── Method filtering ──────────────────────────────────────

    def _filter_methods(
        self, methods: List[MethodInfo]
    ) -> List[MethodInfo]:
        """Apply config filters to the method list."""
        filtered: List[MethodInfo] = []
        exclude_names = set(self.config.exclude_methods)

        for m in methods:
            # Package filter
            if self.config.target_packages:
                if m.package_name not in self.config.target_packages:
                    continue

            # Exclude by name
            if m.method_name in exclude_names:
                continue

            # Exclusion filters
            if m.is_constructor and not self.config.include_constructors:
                continue
            if m.is_abstract and not self.config.include_abstract:
                continue
            if m.is_private and not self.config.include_private:
                continue
            # Package-private: no access modifier means default visibility
            if not any(mod in m.modifiers for mod in ["public", "private", "protected"]):
                if not self.config.include_package_private:
                    continue

            # Always exclude synthetic/compiler-generated methods
            if m.method_name.startswith("access$"):
                continue

            filtered.append(m)

        return filtered
