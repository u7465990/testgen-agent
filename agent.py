"""TestGeneratorAgent — the main orchestrator that ties everything together."""

from __future__ import annotations

import shutil
import time
from pathlib import Path
from typing import Dict, List, Optional

from checkpoint import load_checkpoint, append_checkpoint, make_record
from config import AgentConfig
from java_analyzer import JavaProjectAnalyzer, SourceFile
from method_extractor import MethodExtractor, MethodInfo
from target_generator import TargetGenerator
from prompt_manager import PromptManager
from llm_client import LLMClient
from test_writer import TestWriter
from compiler import JavaCompiler
from repair_loop import RepairLoop, TestFile
from quality_analyzer import TestQualityAnalyzer, MutationAnalyzer
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
        self.extractor = MethodExtractor(
            project_name=self.project_name,
            mode=config.extraction_mode,
            java_home=config.java_home,
        )
        self.target_gen = TargetGenerator(
            target_types=config.target_types,
            max_tests_per_method=config.max_tests_per_method,
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

        # Checkpoint for resume: records tests already completed so an
        # interrupted run does not have to re-call the LLM for them.
        # All agent output lives in .testgen-agent/ at the project root —
        # OUTSIDE target/, which `mvn clean` (run by the coverage phase)
        # deletes. Keeping it in target/ would silently destroy resume state.
        state_dir = self.project_path / ".testgen-agent"
        checkpoint_path = state_dir / "checkpoint.jsonl"

        if self.config.resume:
            self._migrate_legacy_checkpoint(checkpoint_path)
            done = load_checkpoint(checkpoint_path)
            if done:
                print(f"  [Resume] {len(done)} tests already in checkpoint "
                      f"— will skip them")
        else:
            done = {}
            if checkpoint_path.is_file():  # fresh start: clear stale state
                checkpoint_path.unlink()

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

        # Build the project before generating anything. Generated tests
        # import the project's own types, and javac can only see them via
        # the compiled output on the classpath. Doing this up front also
        # surfaces an unbuildable project before any LLM spend.
        built, build_message = self.compiler.ensure_project_built()
        if built:
            print(f"  [Build] {build_message}")
        else:
            print(f"  [Build] WARNING: {build_message}")
            print("  [Build] Generated tests will likely fail to compile — "
                  "build the project and re-run.")
            report.errors.append(f"Project build failed: {build_message}")

        # ── Phases 2-4: streaming filter → target → generate ─
        # One source file is processed at a time. The global counter stays
        # monotonic (it advances even for skipped targets) so class names
        # match a full run exactly — this is what makes resume safe.
        print("\n=== Phases 2-4: Filtering, Targets & Generation (streaming) ===")
        test_files: List[TestFile] = []
        methods_found = 0
        methods_targeted = 0
        counter = 0
        skipped = 0
        for src in sources:
            methods = self.extractor.extract_methods(src)
            methods_found += len(methods)
            targeted = self._filter_methods(methods)
            methods_targeted += len(targeted)

            for method in targeted:
                for target in self.target_gen.generate_targets(method):
                    class_name = self.writer.generate_class_name(
                        method, target, counter
                    )
                    counter += 1
                    if self.config.resume and class_name in done:
                        skipped += 1
                        print(f"  [#{counter}] {method.fqn} — "
                              f"{target[:40]}... [skip: already in checkpoint]")
                        continue

                    print(f"  [#{counter}] {method.fqn} — {target[:50]}...")
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

                    package_name = self.writer.get_package(method)
                    formatted = self.writer.format_code(
                        raw_code, class_name, package_name
                    )
                    file_path = self.writer.write_test_file(
                        formatted, package_name, class_name
                    )
                    test_files.append(TestFile(
                        path=file_path,
                        method=method,
                        target=target,
                        source_code=formatted,
                        class_name=class_name,
                        package_name=package_name,
                    ))
                    print(f"    -> Saved: {file_path.name}")

        report.methods_found = methods_found
        report.methods_targeted = methods_targeted
        report.tests_generated = counter
        print(f"  {methods_found} methods extracted, {methods_targeted} "
              f"targeted, {counter} test targets ({skipped} skipped)")

        if methods_targeted == 0:
            report.errors.append("No methods matched the filter criteria")
            report.duration_seconds = time.time() - start
            return report

        if not test_files and not done:
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
                if self.config.resume:
                    record = make_record(
                        result.method, result.class_name, result.path,
                        result.target
                    )
                    append_checkpoint(checkpoint_path, record)

        print(f"  Compiled: {report.tests_compiled}/{len(test_files)} "
              f"(new this run)")

        # ── Phase 6: Coverage Improvement (MVP) ──────────────
        print("\n=== Phase 6: Coverage Improvement ===")
        additional = self.repairer.improve_coverage(compiled)
        compiled.extend(additional)
        report.tests_generated += len(additional)

        # ── Rebuild resumed tests so the report stays complete ─
        resumed = self._resumed_test_files(done)
        report.tests_compiled += len(resumed)
        if resumed:
            print(f"  Resumed from checkpoint: {len(resumed)} tests")

        all_tests = compiled + resumed

        # ── Phase 7: Final verification ─────────────────────
        print("\n=== Phase 7: Final Verification ===")
        report.tests_runnable = 0
        classpath = self.compiler.resolve_classpath()
        for tf in all_tests:
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
        for tf in all_tests:
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
        for tf in all_tests:
            report.test_files.append(
                ReportGenerator.per_method_row(
                    tf.method, tf.target, tf.source_code,
                    str(tf.path), tf.runnable,
                )
            )

        # ── Phase 8: Test quality analysis ──────────────────
        # Compilation only proves the files parse. This measures whether the
        # tests are meaningful: empty classes, assertion density, and (via
        # PiTest) how many injected faults the tests actually catch.
        print("\n=== Phase 8: Test Quality Analysis ===")
        quality = TestQualityAnalyzer.analyze(
            [(tf.class_name, tf.source_code) for tf in all_tests]
        )
        report.total_test_methods = quality.total_test_methods
        report.empty_test_classes = len(quality.empty_test_classes)
        report.empty_test_class_names = quality.empty_test_classes
        report.assertion_density = quality.assertion_density

        print(f"  {quality.total_test_methods} @Test methods across "
              f"{quality.total_files} files")
        print(f"  Assertion density:  {quality.assertion_density:.2f} per test")
        if quality.empty_test_classes:
            print(f"  Empty test classes: {len(quality.empty_test_classes)} "
                  f"(compile, but contain no @Test)")
            for name in quality.empty_test_classes:
                print(f"    - {name}")
        else:
            print("  Empty test classes: none")

        if self.config.run_mutation_analysis:
            self._run_mutation_analysis(report, all_tests)
        else:
            print("  Mutation analysis: skipped (--no-mutation)")

        report.duration_seconds = time.time() - start

        # ── Output ──────────────────────────────────────────
        ReportGenerator.print_console(report)

        # Write report files into the same state dir (survives mvn clean)
        state_dir.mkdir(parents=True, exist_ok=True)

        if self.config.report_format in ("md", "all"):
            ReportGenerator.generate_markdown(
                report, state_dir / "report.md",
                reproduce_command=self._reproduce_command(),
            )
            print(f"\n  Markdown:    {state_dir / 'report.md'}")

        if self.config.report_format in ("json", "both", "all"):
            ReportGenerator.generate_json(
                report, state_dir / "report.json"
            )
            print(f"  JSON report: {state_dir / 'report.json'}")

        if self.config.report_format in ("csv", "both", "all"):
            ReportGenerator.generate_csv(
                report, state_dir / "report.csv", report.test_files
            )
            print(f"  CSV report:  {state_dir / 'report.csv'}")

        print(f"\n  Test files are in: {self.test_dir}")
        print("  Done.")

        return report

    def _resumed_test_files(self, done: Dict[str, dict]) -> List[TestFile]:
        """Rebuild TestFile objects from checkpoint records for the report.

        Only records whose test file still exists on disk are kept. These
        were compiled successfully before (that is why they are recorded),
        so they are treated as already-compiled.
        """
        resumed: List[TestFile] = []
        for record in done.values():
            try:
                method = MethodInfo(**record["method"])
                path = Path(record["file_path"])
                source_code = path.read_text(encoding="utf-8")
            except Exception:
                continue  # file missing or malformed record — skip it
            tf = TestFile(
                path=path,
                method=method,
                target=record.get("target", ""),
                source_code=source_code,
                class_name=record["class_name"],
                package_name=method.package_name,
            )
            tf.compiles = True
            resumed.append(tf)
        return resumed

    # ── State helpers ─────────────────────────────────────────

    def _migrate_legacy_checkpoint(self, checkpoint_path: Path) -> None:
        """Move a checkpoint written by an older version out of target/.

        Earlier versions stored it at target/testgen-agent/checkpoint.jsonl,
        where the coverage phase's `mvn clean` would delete it mid-run. Copy
        it forward so an in-flight run is not silently restarted.
        """
        legacy = self.project_path / "target/testgen-agent/checkpoint.jsonl"
        if checkpoint_path.is_file() or not legacy.is_file():
            return
        checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(legacy, checkpoint_path)
        print("  [Resume] Migrated checkpoint out of target/ "
              "(mvn clean would delete it)")

    # ── Report helpers ────────────────────────────────────────

    def _reproduce_command(self) -> str:
        """Best-effort CLI line that reproduces this run (for the report)."""
        parts = [
            "python main.py generate <project-path>",
            f"--provider {self.config.llm_provider}",
            f"--model {self.config.llm_model}",
            f"--max-per-method {self.config.max_tests_per_method}",
        ]
        for pkg in self.config.target_packages:
            parts.append(f"--package {pkg}")
        if not self.config.include_private:
            parts.append("--skip-private")
        if not self.config.run_coverage_improvement:
            parts.append("--no-coverage")
        if not self.config.run_mutation_analysis:
            parts.append("--no-mutation")
        return " ".join(parts)

    # ── Mutation analysis ─────────────────────────────────────

    def _run_mutation_analysis(
        self, report: AgentReport, all_tests: List[TestFile]
    ) -> None:
        """Run PiTest and fill the mutation fields of the report.

        Degrades gracefully: mutation testing needs Maven plus a resolvable
        pitest-maven plugin, and is skipped with a warning if either is
        missing — the rest of the report is still produced.
        """
        packages = sorted({
            tf.method.package_name
            for tf in all_tests
            if tf.method.package_name
        })
        if not packages:
            print("  [Mutation] No package information available, skipping.")
            return

        # PiTest takes a comma-separated glob of the classes to mutate.
        target_glob = ",".join(f"{p}.*" for p in packages)
        print(f"  [Mutation] Target classes: {target_glob}")

        # PiTest refuses to run unless the suite is green. Generated tests can
        # legitimately fail at runtime (e.g. a misunderstood class invariant),
        # so on that specific failure, exclude the offenders and retry — the
        # remaining green tests still yield a meaningful mutation score.
        excluded: List[str] = []
        ran, output = MutationAnalyzer.run(
            self.project_path,
            target_glob,
            version=self.config.pitest_version,
            timeout=self.config.mutation_timeout_seconds,
        )
        if not ran:
            failing = MutationAnalyzer.parse_failing_tests(output)
            if not failing:
                report.errors.append(
                    "Mutation analysis did not run (Maven or pitest-maven "
                    "unavailable) — see warnings above"
                )
                return
            print(f"  [Mutation] {len(failing)} test class(es) fail before "
                  f"mutation — retrying with them excluded:")
            for name in failing:
                print(f"    - {name}")
            excluded = failing
            ran, output = MutationAnalyzer.run(
                self.project_path,
                target_glob,
                version=self.config.pitest_version,
                timeout=self.config.mutation_timeout_seconds,
                exclude_tests=excluded,
            )
            if not ran:
                report.errors.append(
                    f"Mutation analysis did not run: {len(failing)} test "
                    f"class(es) fail without mutation (PiTest needs a green "
                    f"suite)"
                )
                return

        report.mutations_excluded_tests = excluded

        xml = MutationAnalyzer.find_pitest_xml(self.project_path)
        if not xml:
            print("  [Mutation] No PiTest report generated, skipping.")
            report.errors.append("PiTest produced no mutations.xml")
            return

        result = MutationAnalyzer.parse_pitest_xml(xml)
        report.mutations_killed = result.killed
        report.mutations_total = result.total
        report.mutations_no_coverage = result.no_coverage
        report.mutation_score = result.score
        report.mutation_by_class = [
            {
                "name": c.name,
                "killed": c.killed,
                "total": c.total,
                "score": c.score,
            }
            for c in result.by_class
        ]

        print(f"  Mutation score: {result.score:.1%} "
              f"({result.killed}/{result.total} mutants killed)")

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
