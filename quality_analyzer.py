"""Test quality analysis — empty test classes, assertion density, mutation score.

Compilation success only proves a test file is syntactically valid. This module
measures whether the generated tests are actually *meaningful*:

  * empty test classes   — files that compile but contain no @Test method
  * assertion density    — assertions per @Test method
  * mutation score       — PiTest: how many injected faults the tests catch

Mutation score is the headline metric: coverage can be 100% with zero
assertions, but a surviving mutant means the tests do not check that behaviour.
"""

from __future__ import annotations

import re
import subprocess
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Sequence, Tuple

from runlog import get_logger

logger = get_logger(__name__)


# ── Patterns for static source analysis ───────────────────────
# Matches @Test and @Test(expected = ...). Kept loose on purpose: a false
# "not empty" is far less harmful here than a false "empty".
_TEST_ANNOTATION_RE = re.compile(r"@Test\b")
# assertEquals / assertTrue / Assert.assertNotNull / assertThat — and fail().
_ASSERT_RE = re.compile(r"\bassert[A-Za-z0-9_]*\s*\(", re.IGNORECASE)
_FAIL_RE = re.compile(r"\bfail\s*\(")
_BLOCK_COMMENT_RE = re.compile(r"/\*.*?\*/", re.DOTALL)
_LINE_COMMENT_RE = re.compile(r"//[^\n]*")


@dataclass
class TestQuality:
    """Quality metrics computed from the generated test sources."""

    total_files: int = 0
    total_test_methods: int = 0
    total_assertions: int = 0
    empty_test_classes: List[str] = field(default_factory=list)

    @property
    def assertion_density(self) -> float:
        """Assertions per @Test method (0.0 when there are no test methods)."""
        if self.total_test_methods == 0:
            return 0.0
        return self.total_assertions / self.total_test_methods


class TestQualityAnalyzer:
    """Static analysis over generated test sources — needs no build or JVM."""

    @staticmethod
    def analyze(sources: Sequence[Tuple[str, str]]) -> TestQuality:
        """Compute quality metrics from (class_name, source_code) pairs."""
        quality = TestQuality()
        for name, code in sources:
            quality.total_files += 1
            # Strip comments first so a commented-out assertion or a
            # "// TODO add @Test" does not inflate the counts.
            stripped = TestQualityAnalyzer._strip_comments(code)
            n_tests = len(_TEST_ANNOTATION_RE.findall(stripped))
            quality.total_test_methods += n_tests
            quality.total_assertions += len(_ASSERT_RE.findall(stripped))
            quality.total_assertions += len(_FAIL_RE.findall(stripped))
            if n_tests == 0:
                quality.empty_test_classes.append(name)
        return quality

    @staticmethod
    def _strip_comments(code: str) -> str:
        """Remove block and line comments, preserving line structure."""
        code = _BLOCK_COMMENT_RE.sub(" ", code)
        # Keep the newline so line-based reasoning elsewhere stays valid.
        return _LINE_COMMENT_RE.sub(" ", code)


# ── Mutation testing (PiTest) ─────────────────────────────────

@dataclass
class ClassMutation:
    """Mutation results for one mutated class."""

    name: str
    killed: int = 0
    total: int = 0

    @property
    def score(self) -> float:
        return self.killed / self.total if self.total else 0.0


@dataclass
class MutationResult:
    """Aggregate mutation-testing results for a run."""

    killed: int = 0
    total: int = 0
    no_coverage: int = 0          # mutants no test even reached
    by_class: List[ClassMutation] = field(default_factory=list)

    @property
    def score(self) -> float:
        return self.killed / self.total if self.total else 0.0


# PiTest statuses. TIMED_OUT is conventionally counted as killed: the test
# caught the mutant, it just caught it by hanging. NON_VIABLE mutants are
# broken by construction and say nothing about the tests, so they are dropped.
_KILLED_STATUSES = frozenset({"KILLED", "TIMED_OUT"})
_EXCLUDED_STATUSES = frozenset({"NON_VIABLE"})


class MutationAnalyzer:
    """Runs PiTest via Maven and parses its XML report."""

    @staticmethod
    def find_pitest_xml(project_path: Path) -> Optional[Path]:
        """Locate the PiTest mutations.xml report."""
        candidates = [
            project_path / "target/pit-reports/mutations.xml",
            project_path / "build/reports/pitest/mutations.xml",
        ]
        for candidate in candidates:
            if candidate.is_file():
                return candidate
        return None

    @staticmethod
    def run(
        project_path: Path,
        target_classes: str,
        version: str = "1.15.0",
        timeout: int = 1800,
        exclude_tests: Optional[Sequence[str]] = None,
    ) -> Tuple[bool, str]:
        """Run PiTest mutation coverage for the given class glob.

        Args:
            target_classes: comma-separated glob, e.g. "com.demo.*"
            version: pitest-maven plugin version.
            timeout: seconds before the Maven run is abandoned.
            exclude_tests: fully-qualified test classes to exclude. PiTest
                refuses to run unless the suite is green, so failing tests
                must be excluded (see parse_failing_tests).

        Returns (completed, output). `completed` is False when Maven or the
        plugin was unavailable, or PiTest refused to run. Never raises — the
        rest of the pipeline still produces its report.
        """
        # `test-compile` runs the lifecycle up to compiling the tests; invoking
        # the plugin goal directly does NOT do that on its own.
        # -DtimestampedReports=false pins the output to a predictable path.
        cmd = (
            f"mvn test-compile "
            f"org.pitest:pitest-maven:{version}:mutationCoverage "
            f"-DtargetClasses={target_classes} "
            f"-DtargetTests={target_classes} "
            f"-DoutputFormats=XML "
            f"-DtimestampedReports=false "
            f"-Dmaven.test.failure.ignore=true -B -q"
        )
        if exclude_tests:
            cmd += f" -DexcludedTestClasses={','.join(exclude_tests)}"

        print(f"    [CMD] cd {project_path} && {cmd}")
        try:
            result = subprocess.run(
                cmd, cwd=str(project_path),
                capture_output=True, text=True,
                timeout=timeout, shell=True,
            )
        except subprocess.TimeoutExpired:
            print(f"    [FAIL] PiTest timed out after {timeout}s")
            return False, ""
        except FileNotFoundError:
            print("    [FAIL] Maven (mvn) not found in PATH")
            return False, ""

        output = (result.stdout or "") + (result.stderr or "")
        if result.returncode != 0:
            print(f"    [WARN] Maven returned exit code {result.returncode}")
            # Surface the tail — usually the actual plugin failure reason.
            for line in output.strip().splitlines()[-6:]:
                print(f"      {line}")
            # The console only shows the tail; the full Maven output is what
            # says whether this was a build failure, a missing plugin, or
            # failing tests.
            logger.debug("PiTest maven run FAILED (exit %s), full output:\n%s",
                         result.returncode, output)
            return False, output
        print("    [OK] Mutation testing completed")
        logger.debug("PiTest maven run OK")
        return True, output

    @staticmethod
    def parse_failing_tests(output: str) -> List[str]:
        """Extract test classes PiTest rejected for failing before mutation.

        PiTest aborts with "did not pass without mutation" when the suite is
        not green. Those class names can be fed back via exclude_tests so the
        remaining (green) tests still yield a mutation score.
        """
        names: List[str] = []
        for line in output.splitlines():
            if "did not pass without mutation" not in line:
                continue
            match = re.search(r"testClass=([\w.$]+)", line)
            if match and match.group(1) not in names:
                names.append(match.group(1))
        return names

    @staticmethod
    def parse_pitest_xml(path: Path) -> MutationResult:
        """Parse a PiTest mutations.xml into a MutationResult."""
        result = MutationResult()
        if not path.is_file():
            print(f"    [WARN] PiTest XML not found: {path}")
            return result

        try:
            root = ET.parse(str(path)).getroot()
        except ET.ParseError as e:
            print(f"    [ERROR] Failed to parse PiTest XML: {e}")
            return result

        per_class: dict = {}
        for mutation in root.findall(".//mutation"):
            status = (mutation.get("status") or "").upper()
            if status in _EXCLUDED_STATUSES:
                continue

            class_name = (mutation.findtext("mutatedClass") or "?").strip()
            entry = per_class.setdefault(class_name, ClassMutation(name=class_name))

            result.total += 1
            entry.total += 1
            if status in _KILLED_STATUSES:
                result.killed += 1
                entry.killed += 1
            if status == "NO_COVERAGE":
                result.no_coverage += 1

        result.by_class = sorted(per_class.values(), key=lambda c: c.name)
        return result
