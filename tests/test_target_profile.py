"""Regression tests for target_profile.py — Java/JUnit version detection.

These are the pure decision functions: text in, version out. They encode a few
bugs that shipped once, which is why the parameters are asserted rather than
just the happy path — a wrong version guess changes every generated file.
"""

from __future__ import annotations

import pytest

from target_profile import (
    _classpath_junit_signals,
    _java_from_gradle_text,
    _java_from_pom_text,
    _normalize_java_version,
    _strip_xml_comments,
    pom_declares,
)


class TestNormalizeJavaVersion:
    @pytest.mark.parametrize(
        "raw,expected",
        [
            ("8", 8),
            ("11", 11),
            ("17", 17),
            ("21", 21),
            ("1.8", 8),  # Maven <source> style
            ("1_8", 8),  # Gradle JavaVersion.VERSION_1_8
            ("VERSION_17", 17),  # the VERSION_ prefix is stripped
        ],
    )
    def test_recognized_forms(self, raw, expected):
        assert _normalize_java_version(raw) == expected

    @pytest.mark.parametrize("raw", ["", "   ", "garbage", "1.8.0", "java"])
    def test_unrecognized_returns_none(self, raw):
        # "1.8.0" is deliberately rejected: a full JDK build string is not a
        # source level, and guessing would be worse than falling through to the
        # next detection source.
        assert _normalize_java_version(raw) is None


class TestJavaFromPomText:
    def test_release_wins_over_source(self):
        # `release` also pins the platform API, so it is the strictest signal.
        pom = """
        <maven.compiler.source>8</maven.compiler.source>
        <maven.compiler.release>17</maven.compiler.release>
        """
        assert _java_from_pom_text(pom) == 17

    def test_java_version_property(self):
        assert _java_from_pom_text("<java.version>11</java.version>") == 11

    def test_maven_compiler_plugin_source(self):
        pom = (
            "<maven-compiler-plugin><source>1.8</source></maven-compiler-plugin>"
        )
        assert _java_from_pom_text(pom) == 8

    def test_commented_out_value_is_ignored(self):
        # A commented-out release must not win — the whole point of
        # _strip_xml_comments.
        pom = """
        <!-- <maven.compiler.release>21</maven.compiler.release> -->
        <maven.compiler.release>11</maven.compiler.release>
        """
        assert _java_from_pom_text(pom) == 11

    def test_no_version_declared(self):
        assert _java_from_pom_text("<groupId>com.demo</groupId>") is None


class TestJavaFromGradleText:
    @pytest.mark.parametrize(
        "text,expected",
        [
            ("sourceCompatibility = JavaVersion.VERSION_17", 17),
            ("sourceCompatibility = JavaVersion.VERSION_1_8", 8),
            ("sourceCompatibility = '11'", 11),
            ('targetCompatibility = "1.8"', 8),
        ],
    )
    def test_recognized_forms(self, text, expected):
        assert _java_from_gradle_text(text) == expected

    def test_absent_returns_none(self):
        assert _java_from_gradle_text("plugins { id 'java' }") is None


class TestClasspathJunitSignals:
    def test_jupiter(self):
        cp = (
            "C:/Users/x/.m2/repository/org/junit/jupiter/junit-jupiter-api/"
            "5.9.0/junit-jupiter-api-5.9.0.jar"
        )
        assert _classpath_junit_signals(cp) == (True, False)

    def test_junit4(self):
        cp = "C:/Users/x/.m2/repository/junit/junit/4.13.2/junit-4.13.2.jar"
        assert _classpath_junit_signals(cp) == (False, True)

    def test_windows_backslashes_still_match(self):
        # The separator normalisation is what makes this work on Windows.
        cp = r"C:\Users\x\.m2\repository\junit\junit\4.13.2\junit-4.13.2.jar"
        assert _classpath_junit_signals(cp) == (False, True)

    def test_both_present_reports_both(self):
        # A project mid-migration has jupiter + vintage on the classpath.
        # _detect_junit resolves that tie in favour of JUnit 5.
        cp = (
            "/x/junit-jupiter-api-5.9.0.jar"
            ":/y/junit/junit/4.13.2/junit-4.13.2.jar"
        )
        assert _classpath_junit_signals(cp) == (True, True)

    def test_empty(self):
        assert _classpath_junit_signals("") == (False, False)


class TestStripXmlComments:
    def test_comment_is_removed(self):
        assert "hidden" not in _strip_xml_comments("a<!-- hidden -->b")

    def test_multiline_comment_is_removed(self):
        # DOTALL matters: Maven poms wrap comments across lines routinely.
        assert "hidden" not in _strip_xml_comments("a<!--\nhidden\n-->b")

    def test_plain_text_unchanged(self):
        assert _strip_xml_comments("<a>1</a>") == "<a>1</a>"


class TestPomDeclares:
    @staticmethod
    def _write(tmp_path, body: str):
        (tmp_path / "pom.xml").write_text(body, encoding="utf-8")

    def test_declared_dependency(self, tmp_path):
        self._write(
            tmp_path,
            "<dependencies><dependency>"
            "<artifactId>mockito-core</artifactId>"
            "</dependency></dependencies>",
        )
        assert pom_declares(tmp_path, "mockito-core") is True

    def test_mention_is_not_a_declaration(self, tmp_path):
        # The observed false positive: a demo pom whose <description> said it
        # used Mockito was reported as declaring it, while the dependency was
        # absent. Matching the <artifactId> element is what fixes that.
        self._write(
            tmp_path,
            "<description>used to verify mockito-core support</description>",
        )
        assert pom_declares(tmp_path, "mockito-core") is False

    def test_commented_out_declaration(self, tmp_path):
        self._write(
            tmp_path, "<!-- <artifactId>mockito-core</artifactId> -->"
        )
        assert pom_declares(tmp_path, "mockito-core") is False

    def test_no_pom(self, tmp_path):
        assert pom_declares(tmp_path, "mockito-core") is False
