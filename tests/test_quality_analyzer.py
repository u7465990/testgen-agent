"""Tests for quality_analyzer.py — the module that computes the headline metric.

Compilation success only proves a file parses; the numbers this module produces
are what the report leads with, so they are worth pinning. It is also the
easiest module in the repo to test: ``analyze()`` is a pure function over
(class_name, source) string pairs — no I/O, no JVM, no LLM.

The @ParameterizedTest case is a regression test for a false negative the
source documents: ``@Test\\b`` does not match ``@ParameterizedTest`` (the \\b
fails between 'd' and 'T', both word characters), so a JUnit 5 class using only
that annotation was reported as an empty test class — the exact false negative
this metric exists to catch.
"""

from __future__ import annotations

import pytest

from quality_analyzer import (
    ClassMutation,
    MutationAnalyzer,
    MutationResult,
    TestQualityAnalyzer,
)

analyze = TestQualityAnalyzer.analyze


def _junit4(body: str, name: str = "Foo") -> tuple:
    return (name, f"package com.demo;\npublic class {name} {{\n{body}\n}}\n")


class TestAnalyzeCounts:
    def test_plain_test_is_counted(self):
        q = analyze([_junit4("    @Test public void a() { assertEquals(1, 1); }")])
        assert q.total_files == 1
        assert q.total_test_methods == 1
        assert q.total_assertions == 1
        assert q.empty_test_classes == []

    def test_test_with_parameters_is_counted(self):
        # @Test(expected = ArithmeticException.class) — the \b holds before '('.
        q = analyze([_junit4(
            "    @Test(expected = ArithmeticException.class)\n"
            "    public void a() { assertEquals(1, 1); }"
        )])
        assert q.total_test_methods == 1

    def test_no_test_methods_is_an_empty_class(self):
        q = analyze([_junit4("    public void helper() { }", name="Empty")])
        assert q.total_test_methods == 0
        assert q.empty_test_classes == ["Empty"]

    def test_aggregates_across_files(self):
        q = analyze([
            _junit4("    @Test public void a() { assertEquals(1, 1); }"),
            _junit4("    public void helper() { }", name="Empty"),
        ])
        assert q.total_files == 2
        assert q.total_test_methods == 1
        assert q.empty_test_classes == ["Empty"]

    def test_no_sources_is_not_an_error(self):
        q = analyze([])
        assert q.total_files == 0
        assert q.assertion_density == 0.0  # no ZeroDivisionError

    @pytest.mark.parametrize(
        "annotation",
        ["@ParameterizedTest", "@RepeatedTest(3)", "@TestFactory",
         "@TestTemplate"],
    )
    def test_junit5_test_annotations_are_not_empty_classes(self, annotation):
        # The regression this module's own comment warns about: if only @Test
        # were matched, each of these classes would be reported as empty.
        q = analyze([_junit4(
            f"    {annotation}\n    public void a() {{ assertEquals(1, 1); }}"
        )])
        assert q.total_test_methods == 1
        assert q.empty_test_classes == []


class TestAssertionDensity:
    def test_density_is_assertions_per_test(self):
        q = analyze([_junit4(
            "    @Test public void a() { assertEquals(1, 1); }\n"
            "    @Test public void b() { assertEquals(1, 1); assertEquals(2, 2); }"
        )])
        assert q.total_test_methods == 2
        assert q.total_assertions == 3
        assert q.assertion_density == 1.5

    @pytest.mark.parametrize(
        "statement",
        ["assertEquals(1, 1);", "assertTrue(x);", "Assert.assertNotNull(o);",
         "assertThat(v, is(1));", "fail(\"boom\");"],
    )
    def test_assertion_idioms_are_recognised(self, statement):
        q = analyze([_junit4(f"    @Test public void a() {{ {statement} }}")])
        assert q.total_assertions == 1, statement


class TestCommentStripping:
    def test_commented_out_test_does_not_count(self):
        q = analyze([_junit4(
            "    // @Test\n    /* @Test */\n    public void a() { }",
            name="Commented",
        )])
        assert q.total_test_methods == 0
        assert q.empty_test_classes == ["Commented"]

    def test_commented_out_assertion_does_not_inflate(self):
        q = analyze([_junit4(
            "    @Test public void a() {\n"
            "        // assertEquals(1, 1);\n"
            "        fail(\"boom\");\n"
            "    }"
        )])
        assert q.total_test_methods == 1
        assert q.total_assertions == 1  # only the fail(), not the comment

    def test_strip_comments_keeps_line_structure(self):
        stripped = TestQualityAnalyzer._strip_comments("a // gone\nb\n")
        assert stripped.startswith("a ")
        assert "\nb" in stripped  # the newline survives


class TestMutationScores:
    def test_class_score(self):
        assert ClassMutation(name="X", killed=3, total=4).score == 0.75

    def test_class_score_without_mutants_is_zero(self):
        assert ClassMutation(name="X").score == 0.0  # no ZeroDivisionError

    def test_result_score(self):
        assert MutationResult(killed=6, total=8).score == 0.75

    def test_result_score_without_mutants_is_zero(self):
        assert MutationResult().score == 0.0


def _write_xml(tmp_path, body: str):
    path = tmp_path / "mutations.xml"
    path.write_text(f"<mutations>{body}</mutations>", encoding="utf-8")
    return path


def _mutation(status: str, cls: str = "com.demo.Foo") -> str:
    return (f'<mutation status="{status}">'
            f"<mutatedClass>{cls}</mutatedClass></mutation>")


class TestParsePitestXml:
    def test_killed_survived_counted(self, tmp_path):
        path = _write_xml(tmp_path, _mutation("KILLED") + _mutation("SURVIVED"))
        result = MutationAnalyzer.parse_pitest_xml(path)
        assert result.total == 2
        assert result.killed == 1
        assert result.score == 0.5

    def test_timed_out_counts_as_killed(self, tmp_path):
        # The test did catch the mutant, it just caught it by hanging.
        result = MutationAnalyzer.parse_pitest_xml(
            _write_xml(tmp_path, _mutation("TIMED_OUT"))
        )
        assert result.killed == 1 and result.total == 1

    def test_non_viable_is_dropped_entirely(self, tmp_path):
        # Broken by construction — it says nothing about the tests, so it must
        # not sit in the denominator and drag the score down.
        result = MutationAnalyzer.parse_pitest_xml(
            _write_xml(tmp_path, _mutation("KILLED") + _mutation("NON_VIABLE"))
        )
        assert result.total == 1 and result.killed == 1

    def test_no_coverage_is_counted_but_not_killed(self, tmp_path):
        result = MutationAnalyzer.parse_pitest_xml(
            _write_xml(tmp_path, _mutation("NO_COVERAGE"))
        )
        assert result.total == 1
        assert result.killed == 0
        assert result.no_coverage == 1

    def test_status_is_case_insensitive(self, tmp_path):
        result = MutationAnalyzer.parse_pitest_xml(
            _write_xml(tmp_path, _mutation("killed"))
        )
        assert result.killed == 1

    def test_by_class_is_grouped_and_sorted(self, tmp_path):
        result = MutationAnalyzer.parse_pitest_xml(_write_xml(
            tmp_path,
            _mutation("KILLED", "com.demo.Zed")
            + _mutation("SURVIVED", "com.demo.Abc")
            + _mutation("KILLED", "com.demo.Abc"),
        ))
        assert [c.name for c in result.by_class] == ["com.demo.Abc", "com.demo.Zed"]
        assert result.by_class[0].killed == 1 and result.by_class[0].total == 2

    def test_missing_file_returns_empty_result(self, tmp_path):
        result = MutationAnalyzer.parse_pitest_xml(tmp_path / "nope.xml")
        assert result.total == 0 and result.by_class == []

    def test_malformed_xml_returns_empty_result(self, tmp_path):
        path = tmp_path / "mutations.xml"
        path.write_text("<mutations><mutation", encoding="utf-8")
        result = MutationAnalyzer.parse_pitest_xml(path)
        assert result.total == 0


class TestFindPitestXml:
    def test_finds_the_maven_location(self, tmp_path):
        target = tmp_path / "target/pit-reports"
        target.mkdir(parents=True)
        xml = target / "mutations.xml"
        xml.write_text("<mutations/>", encoding="utf-8")
        assert MutationAnalyzer.find_pitest_xml(tmp_path) == xml

    def test_absent_report_returns_none(self, tmp_path):
        assert MutationAnalyzer.find_pitest_xml(tmp_path) is None


class TestParseFailingTests:
    def test_extracts_the_offending_class(self):
        output = (
            "Line 1\n"
            "testClass=com.demo.Calculator_add_int_int_Test_Normal_5 did not "
            "pass without mutation\n"
            "more noise\n"
        )
        assert MutationAnalyzer.parse_failing_tests(output) == [
            "com.demo.Calculator_add_int_int_Test_Normal_5"
        ]

    def test_deduplicates_repeats(self):
        line = "testClass=com.demo.Foo did not pass without mutation"
        assert MutationAnalyzer.parse_failing_tests(f"{line}\n{line}") == [
            "com.demo.Foo"
        ]

    def test_unrelated_output_yields_nothing(self):
        # A compile failure must NOT be mistaken for a failing test class —
        # that is the distinction describe_failure() exists to make.
        assert MutationAnalyzer.parse_failing_tests("BUILD FAILURE") == []


class TestDescribeFailure:
    def test_compile_error_is_named_as_such(self):
        # Without this, the run says "Maven unavailable" and sends the reader
        # to the wrong place — the real cause was one truncated response.
        text = MutationAnalyzer.describe_failure(
            "[ERROR] /x/Foo.java:[3,5] compilation error"
        )
        assert "does not compile" in text

    def test_no_tests_points_at_surefire_includes(self):
        text = MutationAnalyzer.describe_failure("No tests found for target")
        assert "surefire" in text

    def test_falls_back_to_unavailable(self):
        text = MutationAnalyzer.describe_failure("some unrelated output")
        assert "unavailable" in text
