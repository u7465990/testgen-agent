"""Tests for test_writer.py — class naming, package derivation, formatting.

The class names are a load-bearing contract: the resume checkpoint keys on
them, and CLAUDE.md warns that adding a source file to a demo renames every
generated test in it. So the naming rules are pinned here.
"""

from __future__ import annotations

import pytest

# Aliased: pytest would otherwise try to collect the imported `TestWriter`
# class as a test class of its own (it matches the Test* pattern and has an
# __init__), producing a PytestCollectionWarning.
from test_writer import TestWriter as Writer


class TestShortType:
    @pytest.mark.parametrize(
        "raw,expected",
        [
            ("String", "Str"),
            ("int", "int"),
            ("java.lang.String", "Str"),  # package is stripped
            ("String[]", "StrArr"),
            ("int[]", "intArr"),
            ("Object", "Obj"),
            ("Unknown", "Unknown"),  # no abbreviation: passed through
        ],
    )
    def test_abbreviations(self, raw, expected):
        assert Writer._short_type(raw) == expected


class TestGenerateClassName:
    def test_shape(self, make_method):
        name = Writer.generate_class_name(make_method(), "[Normal] t", 10)
        assert name == "Calculator_add_int_int_Test_Normal_10"

    def test_overloads_get_distinct_names(self, make_method):
        # Same method name, different parameter lists must not collide.
        first = Writer.generate_class_name(
            make_method(
                fqn="com.demo.Calculator.add(int)", parameter_types=("int",)
            ),
            "t",
            0,
        )
        second = Writer.generate_class_name(
            make_method(
                fqn="com.demo.Calculator.add(String)", parameter_types=("String",)
            ),
            "t",
            0,
        )
        assert first != second

    def test_index_disambiguates_repeated_targets(self, make_method):
        m = make_method()
        assert Writer.generate_class_name(m, "[Normal] t", 0) != \
            Writer.generate_class_name(m, "[Normal] t", 1)


class TestTargetLabel:
    def test_explicit_tag_wins(self):
        assert Writer._target_label("[Normal] whatever") == "Normal"

    def test_mock_is_not_mislabelled_as_exception(self):
        # The observed bug: the mock target's prose says "assert on the thrown
        # exception", and scanning for keywords matched "exception" before
        # "mock" — naming every Mockito test _Test_Exception_. The [Tag] prefix
        # is what fixes it.
        target = "[Mock] ... assert on the thrown exception, or verify(...)"
        assert Writer._target_label(target) == "Mock"

    def test_substring_fallback_when_untagged(self):
        assert Writer._target_label("write a boundary test") == "Boundary"

    def test_unknown_target(self):
        assert Writer._target_label("") == "General"


class TestGetPackage:
    def test_uses_package_name_when_present(self, make_method):
        assert Writer.get_package(make_method(package_name="com.demo")) == "com.demo"

    def test_falls_back_to_fqn(self, make_method):
        # Note the fallback keeps the class name in the result — only the last
        # FQN segment (the method) is dropped. Asserted loosely on purpose, so
        # that tightening the fallback later does not break this test.
        assert Writer.get_package(make_method(package_name="")).startswith("com.demo")

    def test_no_package_anywhere(self, make_method):
        assert Writer.get_package(
            make_method(package_name="", fqn="add(int)")
        ) == ""


class TestFormatCode:
    RAW = """```java
package com.orig;
import org.junit.Test;
import org.junit.Test;
import static org.junit.Assert.assertEquals;

public class OldName {
    @Test
    public void t() {
        assertEquals(1, 1);
    }
}
```"""

    def test_extracts_and_renames(self):
        out = Writer.format_code(self.RAW, "NewName", "com.demo")
        assert out.startswith("package com.demo;")
        assert "public class NewName {" in out
        assert "com.orig" not in out
        assert "OldName" not in out

    def test_imports_are_deduplicated_but_order_preserved(self):
        out = Writer.format_code(self.RAW, "NewName", "com.demo")
        assert out.count("import org.junit.Test;") == 1
        assert out.count("import static org.junit.Assert.assertEquals;") == 1
        assert out.index("import org.junit.Test;") < out.index(
            "import static org.junit.Assert.assertEquals;"
        )

    def test_body_is_kept(self):
        out = Writer.format_code(self.RAW, "NewName", "com.demo")
        assert "assertEquals(1, 1);" in out

    def test_without_a_fence_still_works(self):
        out = Writer.format_code("public class X { }", "NewName", "com.demo")
        assert "public class NewName {" in out

    def test_empty_package_omits_the_header(self):
        out = Writer.format_code(self.RAW, "NewName", "")
        assert not out.startswith("package")


class TestWriteTestFile:
    def test_writes_into_the_package_path(self, tmp_path):
        writer = Writer(tmp_path)
        path = writer.write_test_file("class body", "com.demo.x", "Foo")
        assert path == tmp_path / "com" / "demo" / "x" / "Foo.java"
        assert path.read_text(encoding="utf-8") == "class body"

    def test_no_package_writes_at_the_root(self, tmp_path):
        writer = Writer(tmp_path)
        assert writer.write_test_file("body", "", "Foo") == tmp_path / "Foo.java"
