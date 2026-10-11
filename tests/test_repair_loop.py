"""Tests for repair_loop.py — the compile-repair loop and Phase B's gatekeeping.

No LLM and no javac: `LLMClient` is replaced by a scripted stub and the compiler
by a fake that returns a queued sequence of (success, error). That is enough to
drive every branch of `repair_compilation` deterministically, which is the point
— the loop's behaviour is "what does it do with the Nth failure", and that is
exactly what a queued reply makes reproducible.

`improve_coverage` is tested through its early exits, because those are the ones
that decide whether Phase B runs at all. Its inner rounds need a real JaCoCo
report and are exercised by the e2e test against a real Maven project.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from config import AgentConfig
from coverage_analyzer import MethodCoverage
from method_extractor import MethodInfo

# Aliased: `TestFile` and `TestWriter` match pytest's Test* collection pattern
# and have __init__ constructors, so importing them under their own names makes
# pytest try to collect them as test classes.
from repair_loop import RepairLoop
from repair_loop import TestFile as GeneratedFile
from test_writer import TestWriter as Writer

# repair_compilation discards any reply shorter than 50 characters as truncated,
# so the stub has to clear that floor or every repair round is skipped.
LONG_REPLY = (
    "```java\n"
    "public class RepairedTest {\n"
    "    // padded past the 50-character floor the loop enforces\n"
    "}\n"
    "```"
)

# ── Fakes ─────────────────────────────────────────────────────

class FakeLLM:
    """Replies from a queue. An Exception instance is raised instead."""

    def __init__(self, replies):
        self.replies = list(replies)
        self.calls = 0

    def generate(self, system_prompt, user_prompt):
        self.calls += 1
        if not self.replies:
            raise AssertionError("LLM called more times than the test scripted")
        reply = self.replies.pop(0)
        if isinstance(reply, Exception):
            raise reply
        return reply


class FakeCompiler:
    """Returns queued (success, error) pairs; records what it was asked."""

    def __init__(self, results):
        self.results = list(results)
        self.compiles = []
        self.package_fixes = []

    def resolve_classpath(self):
        return ""

    def force_fix_package(self, path, package):
        self.package_fixes.append(package)

    def compile(self, path, classpath):
        self.compiles.append(path.read_text(encoding="utf-8"))
        return self.results.pop(0)


class FakePrompts:
    def __init__(self):
        self.repair_calls = []

    def render_repair_prompt(self, code, error, allowed_imports, profile):
        self.repair_calls.append({
            "code": code, "error": error, "imports": allowed_imports,
        })
        return "system", "user"


# ── Fixtures ──────────────────────────────────────────────────

def _method(make_method, **overrides):
    return make_method(**overrides)


def _test_file(tmp_path, method, code="public class T {}"):
    return GeneratedFile(
        path=tmp_path / "src/test/java/com/demo/T_Test.java",
        method=method,
        target="[Normal]",
        source_code=code,
        class_name="T_Test",
        package_name="com.demo",
    )


def _loop(tmp_path, compiler, llm=None, prompts=None, max_attempts=3,
          run_coverage=False):
    config = AgentConfig(
        project_path=tmp_path,
        max_compile_attempts=max_attempts,
        run_coverage_improvement=run_coverage,
    )
    return RepairLoop(
        llm_client=llm or FakeLLM([]),
        prompt_manager=prompts or FakePrompts(),
        compiler=compiler,
        test_writer=Writer(tmp_path / "src/test/java"),
        config=config,
    )


# ── TestFile ──────────────────────────────────────────────────

class TestTestFile:
    def test_starts_uncompiled_and_unrun(self, tmp_path, make_method):
        tf = _test_file(tmp_path, _method(make_method))
        assert tf.compiles is False
        assert tf.compile_attempts == 0
        assert tf.runnable is False


# ── Pure helpers ──────────────────────────────────────────────

class TestExtractJavaBlock:
    @pytest.mark.parametrize("fence", ["```java", "```"])
    def test_extracts_the_fenced_block(self, fence):
        text = f"Here you go:\n{fence}\nclass T {{}}\n```\nDone."
        assert RepairLoop._extract_java_block(text) == "class T {}"

    def test_no_block_is_none(self):
        assert RepairLoop._extract_java_block("just prose") is None

    def test_takes_the_first_block(self):
        text = "```java\nfirst\n```\n```java\nsecond\n```"
        assert RepairLoop._extract_java_block(text) == "first"


class TestFormatAllowedImports:
    def test_one_import_per_line(self, tmp_path, make_method):
        method = _method(make_method, allowed_imports=["a.B", "c.D"])
        tf = _test_file(tmp_path, method)
        assert RepairLoop._format_allowed_imports(
            _loop(tmp_path, FakeCompiler([])), tf
        ) == "import a.B;\nimport c.D;"

    def test_no_imports_is_an_empty_string(self, tmp_path, make_method):
        method = _method(make_method, allowed_imports=[])
        tf = _test_file(tmp_path, method)
        assert RepairLoop._format_allowed_imports(
            _loop(tmp_path, FakeCompiler([])), tf
        ) == ""


class TestGetCorrectPackageFromPath:
    """Dead code, pinned as observed rather than as intended.

    Nothing calls this helper — it is defined at repair_loop.py:408 and
    referenced nowhere — and its arithmetic is off by one: it drops the last
    *two* path segments, so `src/main/java/com/demo/Foo.java` yields "com"
    instead of "com.demo". Recorded here, with the discrepancy named, so that
    keeping, correcting or deleting it stays a visible decision rather than a
    silent one.
    """

    @pytest.mark.parametrize(
        "relative,observed",
        [
            ("src/main/java/com/demo/Foo.java", "com"),          # should be com.demo
            ("src/test/java/a/b/Foo.java", "a"),                 # should be a.b
            ("src/main/java/com/demo/deep/Foo.java", "com.demo"),
            ("src\\main\\java\\com\\demo\\Foo.java", "com"),     # Windows separator
            ("src/main/java/Foo.java", None),                    # nothing between
            ("com/demo/Foo.java", None),                         # no "java" segment
        ],
    )
    def test_observed_behaviour(self, relative, observed):
        assert RepairLoop.get_correct_package_from_path(relative) == observed


# ── Phase A: repair_compilation ───────────────────────────────

class TestRepairCompilation:
    def test_first_compile_succeeds_without_calling_the_llm(
        self, tmp_path, make_method
    ):
        compiler = FakeCompiler([(True, "")])
        llm = FakeLLM([])
        loop = _loop(tmp_path, compiler, llm)
        tf = _test_file(tmp_path, _method(make_method))

        result = loop.repair_compilation(tf)

        assert result.compiles is True
        assert result.compile_attempts == 0      # nothing to repair
        assert llm.calls == 0

    def test_a_failure_then_a_success_costs_one_attempt(self, tmp_path, make_method):
        compiler = FakeCompiler([(False, "error: nope"), (True, "")])
        llm = FakeLLM([LONG_REPLY])
        loop = _loop(tmp_path, compiler, llm)
        tf = _test_file(tmp_path, _method(make_method))

        result = loop.repair_compilation(tf)

        assert result.compiles is True
        assert result.compile_attempts == 1
        assert llm.calls == 1

    def test_it_gives_up_after_max_attempts(self, tmp_path, make_method):
        compiler = FakeCompiler([(False, "e")] * 4)
        llm = FakeLLM(["```java\n" + "x" * 80 + "\n```"] * 3)
        loop = _loop(tmp_path, compiler, llm, max_attempts=3)
        tf = _test_file(tmp_path, _method(make_method))

        result = loop.repair_compilation(tf)

        assert result.compiles is False
        assert result.compile_attempts == 3
        assert llm.calls == 3

    def test_the_latest_code_is_written_to_disk(self, tmp_path, make_method):
        compiler = FakeCompiler([(False, "e"), (True, "")])
        llm = FakeLLM([LONG_REPLY])
        loop = _loop(tmp_path, compiler, llm)
        tf = _test_file(tmp_path, _method(make_method))

        loop.repair_compilation(tf)

        assert "class RepairedTest" in tf.path.read_text(encoding="utf-8")
        assert "class RepairedTest" in tf.source_code

    def test_a_private_method_is_told_to_use_reflection(self, tmp_path, make_method):
        compiler = FakeCompiler([(False, "cannot access private"), (True, "")])
        prompts = FakePrompts()
        loop = _loop(tmp_path, compiler, FakeLLM([LONG_REPLY]),
                     prompts)
        tf = _test_file(
            tmp_path, _method(make_method, is_private=True)
        )

        loop.repair_compilation(tf)

        assert "java.lang.reflect.*" in prompts.repair_calls[0]["imports"]

    def test_a_private_error_gets_the_reflection_hint(self, tmp_path, make_method):
        compiler = FakeCompiler([(False, "error: private access"), (True, "")])
        prompts = FakePrompts()
        loop = _loop(tmp_path, compiler, FakeLLM([LONG_REPLY]),
                     prompts)
        tf = _test_file(tmp_path, _method(make_method))

        loop.repair_compilation(tf)

        assert "[CRITICAL]" in prompts.repair_calls[0]["error"]
        assert "setAccessible" in prompts.repair_calls[0]["error"]

    def test_an_unrelated_error_gets_no_hint(self, tmp_path, make_method):
        compiler = FakeCompiler([(False, "error: cannot find symbol"), (True, "")])
        prompts = FakePrompts()
        loop = _loop(tmp_path, compiler, FakeLLM([LONG_REPLY]),
                     prompts)
        tf = _test_file(tmp_path, _method(make_method))

        loop.repair_compilation(tf)

        assert "[CRITICAL]" not in prompts.repair_calls[0]["error"]

    def test_a_too_short_reply_is_skipped(self, tmp_path, make_method):
        # A truncated or empty response must not be written over good code.
        compiler = FakeCompiler([(False, "e"), (True, "")])
        llm = FakeLLM(["tiny"])                       # under the 50-char floor
        loop = _loop(tmp_path, compiler, llm, max_attempts=2)
        tf = _test_file(tmp_path, _method(make_method))

        result = loop.repair_compilation(tf)

        assert result.compiles is False
        assert llm.calls == 2                          # it kept trying

    def test_an_llm_exception_does_not_abort_the_loop(self, tmp_path, make_method):
        compiler = FakeCompiler([(False, "e"), (True, "")])
        llm = FakeLLM([RuntimeError("api down"), LONG_REPLY])
        loop = _loop(tmp_path, compiler, llm, max_attempts=2)
        tf = _test_file(tmp_path, _method(make_method))

        result = loop.repair_compilation(tf)

        assert result.compiles is True
        assert llm.calls == 2

    def test_a_long_error_is_truncated_from_the_second_round_on(self, tmp_path, make_method):
        # Truncation happens at the end of a round, so the first repair prompt
        # still carries the raw javac output and only later rounds see it capped
        # at 2000 characters.
        compiler = FakeCompiler(
            [(False, "e" * 5000), (False, "e" * 5000), (True, "")]
        )
        prompts = FakePrompts()
        loop = _loop(tmp_path, compiler, FakeLLM([LONG_REPLY, LONG_REPLY]),
                     prompts)
        tf = _test_file(tmp_path, _method(make_method))

        loop.repair_compilation(tf)

        assert len(prompts.repair_calls) == 2
        assert len(prompts.repair_calls[0]["error"]) == 5000
        assert len(prompts.repair_calls[1]["error"]) == 2000

    def test_the_package_is_forced_around_every_compile(self, tmp_path, make_method):
        # Three times for one repair round: once before the first compile, once
        # before the prompt is rendered, and again after the LLM's code is
        # written. The LLM is free to rewrite the package line, so it is
        # re-fixed at both points in the round.
        compiler = FakeCompiler([(False, "e"), (True, "")])
        loop = _loop(tmp_path, compiler, FakeLLM([LONG_REPLY]))
        tf = _test_file(tmp_path, _method(make_method))

        loop.repair_compilation(tf)

        assert compiler.package_fixes == ["com.demo"] * 3


# ── Phase B: improve_coverage ─────────────────────────────────

class TestImproveCoverageSkips:
    """Each early exit is a reason Phase B declines to do anything."""

    def test_disabled_by_config(self, tmp_path, make_method):
        loop = _loop(tmp_path, FakeCompiler([]), run_coverage=False)
        assert loop.improve_coverage([_test_file(tmp_path, _method(make_method))]) == []

    def test_no_target_classes(self, tmp_path):
        loop = _loop(tmp_path, FakeCompiler([]), run_coverage=True)
        assert loop.improve_coverage([]) == []

    def test_when_the_test_run_fails(self, tmp_path, make_method, monkeypatch):
        import repair_loop
        monkeypatch.setattr(repair_loop.CoverageAnalyzer, "run_tests_with_coverage",
                            staticmethod(lambda p: False))
        loop = _loop(tmp_path, FakeCompiler([]), run_coverage=True)
        tf = _test_file(tmp_path, _method(make_method))
        assert loop.improve_coverage([tf]) == []

    def test_when_there_is_no_jacoco_report(self, tmp_path, make_method, monkeypatch):
        import repair_loop
        monkeypatch.setattr(repair_loop.CoverageAnalyzer, "run_tests_with_coverage",
                            staticmethod(lambda p: True))
        monkeypatch.setattr(repair_loop.CoverageAnalyzer, "find_jacoco_xml",
                            staticmethod(lambda p: None))
        loop = _loop(tmp_path, FakeCompiler([]), run_coverage=True)
        tf = _test_file(tmp_path, _method(make_method))
        assert loop.improve_coverage([tf]) == []

    def test_when_no_coverage_data_matches(self, tmp_path, make_method, monkeypatch):
        import repair_loop
        monkeypatch.setattr(repair_loop.CoverageAnalyzer, "run_tests_with_coverage",
                            staticmethod(lambda p: True))
        monkeypatch.setattr(repair_loop.CoverageAnalyzer, "find_jacoco_xml",
                            staticmethod(lambda p: Path("jacoco.xml")))
        monkeypatch.setattr(repair_loop.CoverageAnalyzer, "parse_jacoco_xml",
                            staticmethod(lambda p, target_classes=None: {}))
        loop = _loop(tmp_path, FakeCompiler([]), run_coverage=True)
        tf = _test_file(tmp_path, _method(make_method))
        assert loop.improve_coverage([tf]) == []

    def test_when_every_method_is_already_above_the_threshold(
        self, tmp_path, make_method, monkeypatch
    ):
        import repair_loop
        fully = MethodCoverage(
            method_name="add", method_desc="(II)I", fqn="com.demo.Calculator.add(int,int)",
            covered_branches=2, total_branches=2, branch_ratio=1.0,
        )
        monkeypatch.setattr(repair_loop.CoverageAnalyzer, "run_tests_with_coverage",
                            staticmethod(lambda p: True))
        monkeypatch.setattr(repair_loop.CoverageAnalyzer, "find_jacoco_xml",
                            staticmethod(lambda p: Path("jacoco.xml")))
        monkeypatch.setattr(repair_loop.CoverageAnalyzer, "parse_jacoco_xml",
                            staticmethod(lambda p, target_classes=None: {
                                fully.fqn: fully}))
        loop = _loop(tmp_path, FakeCompiler([]), run_coverage=True)
        tf = _test_file(tmp_path, _method(make_method,
                                          fqn="com.demo.Calculator.add(int, int)"))
        assert loop.improve_coverage([tf]) == []
