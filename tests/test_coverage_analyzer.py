"""Tests for coverage_analyzer.py — the JaCoCo half of Phase B.

Everything here is offline: the XML is a fixture and Maven is never invoked.
The module is mostly pure parsing, which is why it is worth pinning — the
decision of *which methods get another test generated* rests entirely on these
ratios, and a wrong denominator silently changes what Phase B chases.

`run_tests_with_coverage` is the exception: it shells out to Maven. Its four
outcomes are still testable by stubbing `subprocess.run`, and they matter
because each one decides whether Phase B proceeds or gives up.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from coverage_analyzer import CoverageAnalyzer, MethodCoverage

parse = CoverageAnalyzer.parse_jacoco_xml
find = CoverageAnalyzer.find_jacoco_xml


JACOCO = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<report name="demo">
  <package name="com/demo">
    <class name="com/demo/Calculator" sourcefilename="Calculator.java">
      <method name="add" desc="(II)I" line="5">
        <counter type="BRANCH" missed="1" covered="1"/>
        <counter type="LINE" missed="0" covered="3"/>
      </method>
      <method name="div" desc="(II)I" line="9">
        <counter type="BRANCH" missed="2" covered="0"/>
        <counter type="LINE" missed="2" covered="1"/>
      </method>
      <method name="plain" desc="()V" line="20">
        <counter type="LINE" missed="0" covered="1"/>
      </method>
    </class>
  </package>
  <package name="com/other">
    <class name="com/other/Unrelated" sourcefilename="Unrelated.java">
      <method name="thing" desc="()V" line="3">
        <counter type="BRANCH" missed="5" covered="0"/>
        <counter type="LINE" missed="5" covered="0"/>
      </method>
    </class>
  </package>
</report>
"""


def _jacoco(tmp_path: Path, text: str = JACOCO, where: str = "") -> Path:
    path = tmp_path / where / "jacoco.xml"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


class TestFindJacocoXml:
    @pytest.mark.parametrize(
        "where",
        [
            "target/site/jacoco",
            "build/reports/jacoco/test",
            "target/site/jacoco-aggregate",
        ],
    )
    def test_finds_each_known_location(self, tmp_path, where):
        expected = _jacoco(tmp_path, where=where)   # create first, then look
        assert find(tmp_path) == expected

    def test_prefers_the_maven_location(self, tmp_path):
        for where in ("target/site/jacoco", "build/reports/jacoco/test"):
            _jacoco(tmp_path, where=where)
        assert find(tmp_path).parent.name == "jacoco"

    def test_absent_report_is_none(self, tmp_path):
        assert find(tmp_path) is None


class TestParseJacocoXml:
    def test_missing_file_yields_nothing(self, tmp_path):
        assert parse(tmp_path / "nope.xml") == {}

    def test_malformed_xml_yields_nothing(self, tmp_path):
        assert parse(_jacoco(tmp_path, "<report><broken")) == {}

    def test_builds_a_readable_fqn(self, tmp_path):
        coverage = parse(_jacoco(tmp_path))
        assert "com.demo.Calculator.add(int,int)" in coverage

    def test_reads_the_counters(self, tmp_path):
        add = parse(_jacoco(tmp_path))["com.demo.Calculator.add(int,int)"]
        assert add.covered_branches == 1 and add.missed_branches == 1
        assert add.total_branches == 2
        assert add.branch_ratio == 0.5
        assert add.covered_lines == 3 and add.missed_lines == 0

    def test_a_method_with_no_branches_is_fully_covered(self, tmp_path):
        # The convention that matters: a straight-line method has no branches to
        # miss, so a 0/0 ratio must read as 1.0 rather than as 0% and drag the
        # method into Phase B's "below threshold" set forever.
        plain = parse(_jacoco(tmp_path))["com.demo.Calculator.plain()"]
        assert plain.total_branches == 0
        assert plain.branch_ratio == 1.0

    def test_target_classes_filter_keeps_only_those_classes(self, tmp_path):
        coverage = parse(
            _jacoco(tmp_path), target_classes=["com/demo/Calculator"]
        )
        assert all(fqn.startswith("com.demo.Calculator") for fqn in coverage)
        assert not any("Unrelated" in fqn for fqn in coverage)

    def test_without_a_filter_every_class_is_included(self, tmp_path):
        coverage = parse(_jacoco(tmp_path))
        assert any("Unrelated" in fqn for fqn in coverage)

    def test_a_filter_that_matches_nothing_returns_nothing(self, tmp_path):
        assert parse(_jacoco(tmp_path), target_classes=["com/nope/Missing"]) == {}


class TestParseJvmDesc:
    @pytest.mark.parametrize(
        "desc,expected",
        [
            ("(II)I", "(int, int) → int"),
            ("()V", "() → void"),
            # Object types stay fully qualified at this layer; the reduction to
            # simple names happens in _method_fen.
            ("(Ljava/lang/String;I)Z", "(java.lang.String, int) → boolean"),
            ("(Lcom/demo/Foo;)V", "(com.demo.Foo) → void"),
            ("()[I", "() → int[]"),
            ("([[Ljava/lang/String;)V", "(java.lang.String[][]) → void"),
            ("(D)Ljava/util/List;", "(double) → java.util.List"),
        ],
    )
    def test_reads_descriptors(self, desc, expected):
        assert CoverageAnalyzer._parse_jvm_desc(desc) == expected

    def test_an_unrecognised_descriptor_is_returned_unchanged(self):
        # Better a raw string in the prompt than a crash or a wrong signature.
        assert CoverageAnalyzer._parse_jvm_desc("garbage") == "garbage"


class TestMethodFen:
    @pytest.mark.parametrize(
        "class_name,method,desc,expected",
        [
            ("com/demo/Calculator", "add", "(II)I", "com.demo.Calculator.add(int,int)"),
            ("com/demo/Foo", "run", "()V", "com.demo.Foo.run()"),
            # Return type is not a parameter: `()Ljava/lang/String;` takes none.
            ("com/demo/Foo", "get", "()Ljava/lang/String;", "com.demo.Foo.get()"),
            ("com/demo/Foo", "m", "(Ljava/lang/String;I)Z", "com.demo.Foo.m(String,int)"),
        ],
    )
    def test_builds_the_expected_fen(self, class_name, method, desc, expected):
        assert CoverageAnalyzer._method_fen(class_name, method, desc) == expected

    def test_object_parameters_are_reduced_to_simple_names(self):
        # This is where java.lang.String becomes String — not in _parse_jvm_desc.
        fen = CoverageAnalyzer._method_fen(
            "com/demo/Foo", "m", "(Ljava/lang/String;)V"
        )
        assert fen == "com.demo.Foo.m(String)"

    def test_inner_classes_keep_jacocos_dollar_form(self):
        # Pinned as observed rather than as ideal: JaCoCo names inner classes
        # Outer$Inner and that is what reaches the prompt.
        fen = CoverageAnalyzer._method_fen("com/demo/Outer$Inner", "go", "()V")
        assert fen == "com.demo.Outer$Inner.go()"

    def test_array_parameters_keep_their_brackets(self):
        fen = CoverageAnalyzer._method_fen("com/demo/Foo", "sum", "([I)I")
        assert fen == "com.demo.Foo.sum(int[])"


class TestRunTestsWithCoverage:
    """Stubbed `subprocess.run`: the point is which outcome means what."""

    def test_a_clean_run_succeeds(self, tmp_path, monkeypatch):
        monkeypatch.setattr(subprocess, "run",
                            lambda *a, **k: subprocess.CompletedProcess(a, 0))
        assert CoverageAnalyzer.run_tests_with_coverage(tmp_path) is True

    def test_failing_tests_still_count_as_a_completed_run(self, tmp_path, monkeypatch):
        # The command passes -Dmaven.test.failure.ignore=true precisely so that
        # failing generated tests still produce a JaCoCo report to reason about.
        monkeypatch.setattr(subprocess, "run",
                            lambda *a, **k: subprocess.CompletedProcess(a, 1))
        assert CoverageAnalyzer.run_tests_with_coverage(tmp_path) is True

    def test_a_timeout_is_a_failure(self, tmp_path, monkeypatch):
        def timeout(*a, **k):
            raise subprocess.TimeoutExpired(cmd="mvn", timeout=300)

        monkeypatch.setattr(subprocess, "run", timeout)
        assert CoverageAnalyzer.run_tests_with_coverage(tmp_path) is False

    def test_missing_maven_is_a_failure_not_a_crash(self, tmp_path, monkeypatch):
        def no_mvn(*a, **k):
            raise FileNotFoundError("mvn")

        monkeypatch.setattr(subprocess, "run", no_mvn)
        assert CoverageAnalyzer.run_tests_with_coverage(tmp_path) is False


class TestMethodCoverage:
    def test_defaults_describe_an_uncovered_method(self):
        mc = MethodCoverage(method_name="m", method_desc="()V", fqn="A.m()")
        assert mc.missed_branches == 0 and mc.covered_branches == 0
        assert mc.total_branches == 0 and mc.branch_ratio == 0.0
