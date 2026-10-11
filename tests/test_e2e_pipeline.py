"""End-to-end pipeline test: Phase 0-8 against a real project, stubbed LLM.

The rest of the suite is deliberately offline — no LLM, no JDK, no Maven — and
covers the deterministic core one module at a time. What it cannot cover is the
*wiring between* the phases, and both bugs recorded in CLAUDE.md were exactly
wiring bugs:

* the generate prompt was rendered without the detected profile, so a JUnit 5
  project was told "Do NOT use assertThrows() (not available in JUnit 4)" while
  the target text — built from the correctly-shared profile — asked for JUnit 5.
  Nothing short of looking at what the model was actually *sent* sees that.
* every Mockito test used the ``@Mock`` annotation idiom, which fails silently
  when the runner annotation is dropped.

So this test drives ``TestGeneratorAgent.run()`` for real — detect → extract →
target → prompt → write → javac → repair → quality → report — with the LLM
replaced by a recording stub. It needs a JDK and Maven and builds a real Maven
project, which is why it carries the ``e2e`` marker: ``pytest.ini`` deselects
that by default so ``pytest -q`` stays fast and offline, and CI runs it in a
job of its own.

What it proves: framework detection reaches the prompt and the target text, the
generated files land under the deterministic names, they compile against the
project's *own* classes, and Phase 8 counts what was produced.
What it does not prove: that a real model writes *useful* tests. The stub emits
a fixed body for every target, so mutation score remains the measure of that.
"""

from __future__ import annotations

import os
import re
import shutil
import sys
from pathlib import Path

import pytest

# Aliased: pytest would otherwise try to collect the imported
# `TestGeneratorAgent` as a test class of its own (it matches the Test* pattern
# and has an __init__), producing a PytestCollectionWarning.
from agent import TestGeneratorAgent as Agent
from config import AgentConfig
from llm_client import LLMClient

pytestmark = pytest.mark.e2e

REPO_ROOT = Path(__file__).resolve().parent.parent
DEMOS = {
    "junit4": (REPO_ROOT / "examples/demo-project", 4),
    "junit5": (REPO_ROOT / "examples/demo-project-junit5", 5),
}


# ── Toolchain detection (for the skip) ────────────────────────

def _find_javac():
    """Mirror JavaCompiler.find_javac(): JAVA_HOME first, then PATH."""
    java_home = os.environ.get("JAVA_HOME")
    names = ["javac.exe", "javac"] if sys.platform == "win32" else ["javac"]
    if java_home:
        for name in names:
            candidate = Path(java_home) / "bin" / name
            if candidate.is_file():
                return candidate
    for name in names:
        found = shutil.which(name)
        if found:
            return found
    return None


def _find_maven():
    for name in ("mvn", "mvn.cmd", "mvn.bat"):
        found = shutil.which(name)
        if found:
            return found
    return None


_NEEDS_TOOLCHAIN = pytest.mark.skipif(
    not (_find_javac() and _find_maven()),
    reason="needs a JDK (javac) and Maven to build and compile a real project",
)


# ── The stub LLM ──────────────────────────────────────────────

# The body is fixed; only the class it points at varies. Referring to
# <class>.class is what forces javac to resolve the project's own compiled
# types, so a classpath that is missing target/classes fails this test — the
# exact failure that made a clean checkout score an 18/40 compile rate.
_BODY = """
```java
package placeholder;

import __TEST_IMPORT__;
import __ASSERT_IMPORT__;

public class GeneratedStub {
    @Test
    public void stub() {
        __ASSERT__.assertNotNull(__OWNER__.class);
    }
}
```"""

_JUNIT4 = (_BODY
           .replace("__TEST_IMPORT__", "org.junit.Test")
           .replace("__ASSERT_IMPORT__", "org.junit.Assert")
           .replace("__ASSERT__", "Assert"))

_JUNIT5 = (_BODY
           .replace("__TEST_IMPORT__", "org.junit.jupiter.api.Test")
           .replace("__ASSERT_IMPORT__", "org.junit.jupiter.api.Assertions")
           .replace("__ASSERT__", "Assertions"))


def _field(prompt: str, name: str) -> str:
    """Read one `###name`-labelled line out of a rendered prompt."""
    match = re.search(rf"^###{re.escape(name)}\n(.+)$", prompt, re.MULTILINE)
    return match.group(1).strip() if match else ""


def _owner_class(method_fqn: str) -> str:
    """`com.demo.Calculator.add(int, int)` → `com.demo.Calculator`."""
    match = re.match(r"([\w.$]+)\.(\w+)\(", method_fqn)
    return match.group(1) if match else method_fqn.rsplit(".", 1)[0]


class StubLLM:
    """Records every prompt it is sent and answers with compilable code."""

    def __init__(self):
        self.calls: list = []  # (system_prompt, user_prompt)

    def generate(self, system_prompt: str, user_prompt: str) -> str:
        self.calls.append((system_prompt, user_prompt))
        owner = _owner_class(_field(user_prompt, "focal_method_FQN"))
        # The stub reads the framework out of the prompt rather than being told
        # it, so the Java it emits is only compilable if the prompt was right.
        return (_JUNIT5 if "org.junit.jupiter" in system_prompt else _JUNIT4)\
            .replace("__OWNER__", owner)

    # ── Assertions helpers over what was sent ─────────────────

    def generate_calls(self):
        """Only the generation calls — not any repair round."""
        return [(s, u) for s, u in self.calls if "focal_method_FQN" in s]

    @staticmethod
    def system_framework(system_prompt: str) -> int:
        """4 or 5, read off the version-specific rule text."""
        return 5 if "-> { ... })" in system_prompt else 4

    @staticmethod
    def target_framework(user_prompt: str) -> int:
        """4 or 5, read off the generation_target line."""
        target = _field(user_prompt, "generation_target")
        return 5 if "JUnit 5" in target else 4


# ── Fixtures ──────────────────────────────────────────────────

@pytest.fixture
def project_copy(tmp_path):
    """A buildable copy of a demo: pom + main sources only.

    Deliberately does NOT copy `target/` or the committed generated tests.
    Copying target/ would let `ensure_project_built()` short-circuit on a warm
    local checkout and force a real Maven build on a cold CI one — the two runs
    would take different paths. Same for the tests: Phase 8 must count only the
    files this run produced.
    """
    def _copy(demo_dir: Path) -> Path:
        root = tmp_path / demo_dir.name
        shutil.copytree(demo_dir / "src/main/java", root / "src/main/java")
        shutil.copy2(demo_dir / "pom.xml", root / "pom.xml")
        return root

    return _copy


@pytest.fixture
def stub(monkeypatch):
    """Replace the LLM for the duration of the test.

    Only `generate` needs replacing: conftest's autouse guard already makes the
    real provider-SDK client impossible to build, so no API key is involved and
    nothing here can reach the network.
    """
    stub = StubLLM()
    monkeypatch.setattr(LLMClient, "generate", stub.generate)
    return stub


def _config(project_path: Path) -> AgentConfig:
    return AgentConfig(
        project_path=project_path,
        junit_version="auto",
        java_version="auto",
        target_types=["normal", "boundary", "exception", "path",
                      "reflection", "mock"],
        max_tests_per_method=1,     # keeps the file count (and javac calls) small
        max_compile_attempts=1,
        run_coverage_improvement=False,   # Phase B runs `mvn clean test` + JaCoCo
        run_mutation_analysis=False,      # PiTest is minutes, not seconds
        report_format="all",
    )


# ── Checks over a finished run ────────────────────────────────
# Split out so one assertion failing names the phase it belongs to.

def _check_build(report):
    """Phase 1 built the project, so the run did real work."""
    assert not [e for e in report.errors if "build failed" in e.lower()], \
        report.errors
    assert report.source_files_found == 4
    assert report.tests_generated > 0


def _check_detection(report, expected_junit):
    """Phase 0 followed the project, not a hard-coded default."""
    assert report.target_profile["junit_version"] == expected_junit


def _check_compilation(report):
    """Phase 5/7 — every generated file compiled against the project's classes."""
    assert report.compilation_rate == 1.0
    assert report.tests_runnable == report.tests_generated


def _check_quality(report):
    """Phase 8 — the stub's one @Test with one assertion, per file."""
    assert report.empty_test_classes == 0
    assert report.total_test_methods == report.tests_generated
    assert report.assertion_density == 1.0


def _check_prompts(stub, expected_junit):
    """The regression test for the bug in CLAUDE.md.

    The generate prompt was once rendered without the profile, so it told a
    JUnit 5 project not to use assertThrows — while the target text, built from
    the correctly-shared profile, asked for JUnit 5. Asserting the system prompt
    and the target agree is what catches that whole class of mistake.
    """
    calls = stub.generate_calls()
    assert calls, "no generation calls were made"

    for system_prompt, user_prompt in calls:
        assert StubLLM.system_framework(system_prompt) == expected_junit, \
            system_prompt
        assert StubLLM.target_framework(user_prompt) == expected_junit, \
            _field(user_prompt, "generation_target")


def _check_artifacts(root, report):
    """The deterministic naming contract, and where the state dir lives."""
    written = sorted((root / "src/test/java/com/demo").glob("*.java"))
    assert len(written) == report.tests_generated
    for path in written:
        assert re.fullmatch(r"\w+_Test_\w+_\d+\.java", path.name), path.name

    # Reports go to .testgen-agent/ at the project root, NOT target/, which the
    # coverage phase's `mvn clean` deletes.
    state = root / ".testgen-agent"
    for name in ("report.md", "report.json", "report.csv",
                 "checkpoint.jsonl", "run.log"):
        assert (state / name).is_file(), name


# ── Tests ─────────────────────────────────────────────────────

@_NEEDS_TOOLCHAIN
@pytest.mark.parametrize("demo", sorted(DEMOS))
def test_pipeline_end_to_end(demo, project_copy, stub):
    """One real run per demo, then checked from every angle.

    Deliberately one test rather than one per concern: a run costs ~30s of
    Maven and javac, and every assertion here reads the same report.
    """
    expected_junit = DEMOS[demo][1]
    root = project_copy(DEMOS[demo][0])

    report = Agent(_config(root)).run()

    _check_build(report)
    _check_detection(report, expected_junit)
    # Before the compile check: a wrong framework in the prompt is the root
    # cause of a compile failure here, and the prompt is the actionable thing.
    _check_prompts(stub, expected_junit)
    _check_compilation(report)
    _check_quality(report)
    _check_artifacts(root, report)
