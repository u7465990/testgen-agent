"""Repair loop — compiles generated tests and fixes failures via LLM."""

from __future__ import annotations

import os
import re
import subprocess
import time
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

from config import AgentConfig
from compiler import JavaCompiler
from coverage_analyzer import CoverageAnalyzer, MethodCoverage
from llm_client import LLMClient
from prompt_manager import PromptManager
from test_writer import TestWriter
from method_extractor import MethodInfo


class TestFile:
    """Represents a generated test file with metadata."""

    def __init__(
        self,
        path: Path,
        method: MethodInfo,
        target: str,
        source_code: str,
        class_name: str,
        package_name: str,
    ):
        self.path = path
        self.method = method
        self.target = target
        self.source_code = source_code
        self.class_name = class_name
        self.package_name = package_name
        self.compiles: bool = False
        self.compile_attempts: int = 0
        self.runnable: bool = False


class RepairLoop:
    """
    Two-phase test repair:
      Phase A — compilation repair via LLM feedback
      Phase B — coverage-guided improvement (run tests, find gaps, fill them)
    """

    def __init__(
        self,
        llm_client: LLMClient,
        prompt_manager: PromptManager,
        compiler: JavaCompiler,
        test_writer: TestWriter,
        config: AgentConfig,
    ):
        self.llm = llm_client
        self.prompts = prompt_manager
        self.compiler = compiler
        self.writer = test_writer
        self.config = config
        self.project_path = config.project_path

    # ── Phase A: Compilation repair ───────────────────────────

    def repair_compilation(self, test_file: TestFile) -> TestFile:
        """
        Phase A: Up to max_compile_attempts rounds.
        Each round: compile → if failed, send error to LLM → apply fix.
        """
        classpath = self.compiler.resolve_classpath()
        allowed_imports = self._format_allowed_imports(test_file)

        # Ensure java.lang.reflect is available for private methods
        if test_file.method.is_private:
            if "java.lang.reflect.*" not in allowed_imports:
                allowed_imports += "\nimport java.lang.reflect.*;"

        current_code = test_file.source_code
        file_abs = test_file.path
        file_abs.parent.mkdir(parents=True, exist_ok=True)

        # Always write initial code to disk
        file_abs.write_text(current_code, encoding="utf-8")

        # Auto-fix package before first compile
        correct_pkg = self.writer.get_package(test_file.method)
        self.compiler.force_fix_package(file_abs, correct_pkg)
        current_code = file_abs.read_text(encoding="utf-8")

        # Compile
        success, error = self.compiler.compile(file_abs, classpath)
        test_file.compile_attempts = 0

        if success:
            test_file.compiles = True
            test_file.source_code = current_code
            return test_file

        # Repair loop
        max_attempts = self.config.max_compile_attempts
        for attempt in range(1, max_attempts + 1):
            test_file.compile_attempts = attempt
            print(f"      Repair attempt {attempt}/{max_attempts}...")

            # Auto-fix package again (LLM may have changed it)
            self.compiler.force_fix_package(file_abs, correct_pkg)

            # Enhance error message for common patterns
            enhanced_error = error
            if "IllegalAccessException" in error or "private" in error:
                enhanced_error += (
                    "\n[CRITICAL] The test is accessing a private method. "
                    "You MUST use reflection: getDeclaredMethod, "
                    "setAccessible(true), invoke, and catch "
                    "InvocationTargetException."
                )

            # Call LLM for repair
            sys_prompt, user_prompt = self.prompts.render_repair_prompt(
                current_code, enhanced_error, allowed_imports
            )
            try:
                new_code = self.llm.generate(sys_prompt, user_prompt)
            except Exception as e:
                print(f"      LLM repair call failed: {e}")
                continue

            if not new_code or len(new_code) < 50:
                print("      LLM returned too-short response, skipping.")
                continue

            # Extract Java from markdown if needed
            java_block = self._extract_java_block(new_code)
            if java_block:
                new_code = java_block

            # Write, auto-fix, and compile
            file_abs.write_text(new_code, encoding="utf-8")
            self.compiler.force_fix_package(file_abs, correct_pkg)
            current_code = file_abs.read_text(encoding="utf-8")

            success, error = self.compiler.compile(file_abs, classpath)
            if success:
                test_file.compiles = True
                test_file.source_code = current_code
                print("      -> COMPILABLE")
                return test_file
            else:
                # Truncate long errors for the next prompt
                error = error[:2000] if len(error) > 2000 else error

        test_file.compiles = False
        print("      -> STILL FAILING after all attempts")
        return test_file

    # ── Phase B: Coverage improvement ─────────────────────────

    def improve_coverage(
        self, project_tests: List[TestFile]
    ) -> List[TestFile]:
        """
        Phase B: Run Maven tests + JaCoCo → detect uncovered branches
        → generate [MissingBranch] tests → repair → verify.

        Returns a list of newly generated TestFile objects.
        """
        if not self.config.run_coverage_improvement:
            return []

        print("\n  [Phase B] Starting coverage-guided improvement...")

        # 1. Determine which target classes are covered by existing tests
        target_class_set: Set[str] = set()
        for tf in project_tests:
            # Derive slash-separated class name from method FQN
            fqn_no_method = tf.method.fqn.rsplit(".", 1)[0]
            slash_class = fqn_no_method.replace(".", "/")
            target_class_set.add(slash_class)

        if not target_class_set:
            print("  [Phase B] No target classes found, skipping.")
            return []

        print(f"  [Phase B] Target classes: {target_class_set}")

        # 2. Run tests with coverage
        if not CoverageAnalyzer.run_tests_with_coverage(self.project_path):
            print("  [Phase B] Failed to run tests, skipping coverage improvement.")
            return []

        # 3. Parse JaCoCo XML
        jacoco_xml = CoverageAnalyzer.find_jacoco_xml(self.project_path)
        if not jacoco_xml:
            print("  [Phase B] No JaCoCo report generated, skipping.")
            return []

        coverage = CoverageAnalyzer.parse_jacoco_xml(
            jacoco_xml, target_classes=list(target_class_set)
        )
        if not coverage:
            print("  [Phase B] No coverage data for target classes.")
            return []

        # 4. Find methods below branch threshold
        threshold = self.config.branch_coverage_target
        low_coverage_methods = {
            fen: mc
            for fen, mc in coverage.items()
            if mc.total_branches > 0 and mc.branch_ratio < threshold
        }

        if not low_coverage_methods:
            print(f"  [Phase B] All methods meet {threshold:.0%} branch coverage!")
            return []

        print(f"  [Phase B] Found {len(low_coverage_methods)} methods "
              f"below {threshold:.0%} branch coverage")

        # 5. For each low-coverage method, generate a [MissingBranch] test
        additional: List[TestFile] = []
        round_count = 0

        for _round in range(1, self.config.max_runtime_rounds + 1):
            round_count = _round
            print(f"\n  [Phase B] Round {_round}/{self.config.max_runtime_rounds}")

            new_this_round = self._generate_missing_branch_tests(
                project_tests, low_coverage_methods, coverage
            )
            if not new_this_round:
                print("  [Phase B] No new tests generated this round.")
                break

            # Compile-and-repair each new test
            for tf in new_this_round:
                self.repair_compilation(tf)

            additional.extend(new_this_round)
            print(f"  [Phase B] Round {_round}: +{len(new_this_round)} tests "
                  f"(compilable: {sum(1 for t in new_this_round if t.compiles)})")

            # Re-run coverage to check improvement
            if not CoverageAnalyzer.run_tests_with_coverage(self.project_path):
                break

            jacoco_xml = CoverageAnalyzer.find_jacoco_xml(self.project_path)
            if not jacoco_xml:
                break

            coverage = CoverageAnalyzer.parse_jacoco_xml(
                jacoco_xml, target_classes=list(target_class_set)
            )
            still_low = {
                fen: mc
                for fen, mc in coverage.items()
                if mc.total_branches > 0 and mc.branch_ratio < threshold
            }
            if not still_low:
                print(f"  [Phase B] All methods now meet {threshold:.0%} coverage!")
                break

            low_coverage_methods = still_low
            print(f"  [Phase B] {len(still_low)} methods still below threshold")

        print(f"  [Phase B] Done. Generated {len(additional)} additional tests "
              f"in {round_count} round(s).")
        return additional

    def _generate_missing_branch_tests(
        self,
        project_tests: List[TestFile],
        low_coverage: Dict[str, MethodCoverage],
        full_coverage: Dict[str, MethodCoverage],
    ) -> List[TestFile]:
        """Generate new test files targeting uncovered branches.

        For each low-coverage method, finds the corresponding TestFile
        as a template, creates a [MissingBranch] target, calls the LLM,
        and saves the result.
        """
        # Build a quick lookup: method FEN → TestFile
        fen_to_tf: Dict[str, TestFile] = {}
        for tf in project_tests:
            fen_to_tf[tf.method.fqn] = tf

        generated: List[TestFile] = []
        idx_counter = len(project_tests) + 1

        for fen, mc in low_coverage.items():
            # Find the template TestFile for this method
            tf = fen_to_tf.get(fen)
            if not tf:
                # Try matching by simpler FQN (params stripped)
                base_fen = fen.split("(")[0]
                for k, v in fen_to_tf.items():
                    if k.startswith(base_fen):
                        tf = v
                        break
            if not tf:
                print(f"    [SKIP] No matching method info for {fen}")
                continue

            missed = mc.missed_branches
            covered = mc.covered_branches
            total = mc.total_branches
            print(f"    {fen}: {covered}/{total} branches covered "
                  f"({mc.branch_ratio:.1%})")

            # Extract branch hints from the method's branch conditions
            conditions = tf.method.branch_conditions
            hint = ""
            if conditions:
                hint = (" The uncovered branches likely correspond "
                        "to these conditions: " + "; ".join(conditions[:5]))
            else:
                hint = (" Analyze the method logic and provide inputs "
                        "that trigger each missing branch.")

            target_text = (
                f"[MissingBranch] Generate ONE JUnit 4 test method "
                f"that covers {missed} uncovered branch(es). "
                f"{hint} "
                "IMPORTANT: Use safe, realistic inputs only. "
                "DO NOT use Integer.MIN_VALUE, Integer.MAX_VALUE, etc., "
                "as length/offset parameters. "
                "For length/offset, prefer -1, 0, 1, 2. "
                "For arrays/byte[], use non-null and small size. "
                "For strings, use typical values like \"test\". "
                "Assert the expected return value or exception "
                "using JUnit 4 assertions. "
                "If the method is private, use reflection "
                "with setAccessible(true)."
            )

            # Call LLM to generate the new test
            try:
                sys_prompt, user_prompt = self.prompts.render_generate_prompt(
                    tf.method, target_text
                )
                raw_code = self.llm.generate(sys_prompt, user_prompt)
            except Exception as e:
                print(f"      LLM generation failed: {e}")
                continue

            if not raw_code or len(raw_code) < 50:
                print("      LLM returned too-short response, skipping.")
                continue

            # Format, name, and save
            class_name = self.writer.generate_class_name(
                tf.method, target_text, idx_counter
            )
            package_name = self.writer.get_package(tf.method)
            formatted = self.writer.format_code(
                raw_code, class_name, package_name
            )
            file_path = self.writer.write_test_file(
                formatted, package_name, class_name
            )

            new_tf = TestFile(
                path=file_path,
                method=tf.method,
                target=target_text,
                source_code=formatted,
                class_name=class_name,
                package_name=package_name,
            )
            generated.append(new_tf)
            idx_counter += 1
            print(f"      -> Saved: {file_path.name}")

        return generated

    # ── Helpers ───────────────────────────────────────────────

    @staticmethod
    def _extract_java_block(text: str) -> Optional[str]:
        """Extract Java code from a ```java ... ``` markdown block."""
        match = re.search(
            r"```(?:java)?\s*\n(.*?)\n```", text, re.DOTALL
        )
        return match.group(1) if match else None

    def _format_allowed_imports(self, tf: TestFile) -> str:
        """Format allowed imports as a string for the repair prompt."""
        imports = list(tf.method.allowed_imports)
        return "\n".join(f"import {i};" for i in imports)

    @staticmethod
    def get_correct_package_from_path(relative_path: str) -> Optional[str]:
        """Infer package name from the file's relative path."""
        parts = relative_path.replace("\\", "/").split("/")
        try:
            idx = parts.index("java") + 1
            pkg_parts = (
                parts[idx:-2] if len(parts) > idx + 1 else parts[idx:-1]
            )
            return ".".join(pkg_parts) if pkg_parts else None
        except (ValueError, IndexError):
            return None
