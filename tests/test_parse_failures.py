"""Parse failures must be recorded, not just printed.

This is the other half of the M0 credibility baseline. On modern Java the
javalang backend cannot parse records, switch expressions, pattern matching or
text blocks. Before this change those files vanished behind one console warning
and every reported method count was silently incomplete.
"""

from __future__ import annotations

from java_analyzer import SourceFile
from extractor.javalang_backend import JavalangBackend
from method_extractor import MethodExtractor


def _source(tmp_path, name, code, module="core"):
    path = tmp_path / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(code, encoding="utf-8")
    return SourceFile(path, "com.example", module)


def test_modern_syntax_is_recorded_as_a_parse_failure(tmp_path):
    src = _source(
        tmp_path, "Money.java",
        "package com.example;\npublic record Money(long cents) {}\n",
    )

    backend = JavalangBackend()

    assert backend.extract(src) == []
    (failure,) = backend.parse_failures
    assert failure["file"] == str(src.path)
    assert failure["module"] == "core"
    assert failure["stage"] == "parse"
    assert "JavaSyntaxError" in failure["error"]


def test_a_plain_file_produces_methods_and_no_failure(tmp_path):
    src = _source(
        tmp_path, "Plain.java",
        "package com.example;\npublic class Plain {"
        " public int add(int a, int b) { return a + b; } }\n",
    )

    backend = JavalangBackend()

    assert len(backend.extract(src)) == 1
    assert backend.parse_failures == []


def test_missing_file_is_recorded_as_a_read_failure(tmp_path):
    src = SourceFile(tmp_path / "Missing.java", "com.example", "core")

    backend = JavalangBackend()

    assert backend.extract(src) == []
    (failure,) = backend.parse_failures
    assert failure["stage"] == "read"


def test_facade_exposes_and_clears_failures(tmp_path):
    src = _source(
        tmp_path, "Money.java",
        "package com.example;\npublic record Money(long cents) {}\n",
    )
    extractor = MethodExtractor(project_name="fixture")

    assert extractor.extract_methods(src) == []
    assert len(extractor.parse_failures) == 1

    extractor.clear_parse_failures()
    assert extractor.parse_failures == []
