"""Report fields for parse failures and per-module statistics."""

from __future__ import annotations

import json

from report_generator import AgentReport, ReportGenerator


FAILURE = {
    "file": "/p/Money.java",
    "module": "core",
    "stage": "parse",
    "error": "JavaSyntaxError: Expected type declaration",
}

MODULES = {
    "core": {
        "source_files": 6,
        "methods_found": 2,
        "methods_targeted": 2,
        "tests_generated": 3,
        "tests_compiled": 2,
        "tests_runnable": 2,
    }
}


def test_json_records_parse_failures_and_module_stats(tmp_path):
    report = AgentReport(
        project_path="demo",
        source_files_found=9,
        methods_found=7,
        parse_failures=[FAILURE],
        module_stats=MODULES,
    )
    out = tmp_path / "report.json"

    ReportGenerator.generate_json(report, out)

    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["parse_failures"][0]["file"] == "/p/Money.java"
    assert data["module_stats"]["core"]["source_files"] == 6


def test_markdown_names_the_skipped_file_and_module(tmp_path):
    report = AgentReport(
        project_path="demo",
        parse_failures=[FAILURE],
        module_stats=MODULES,
    )
    out = tmp_path / "report.md"

    ReportGenerator.generate_markdown(report, out)

    text = out.read_text(encoding="utf-8")
    assert "Money.java" in text
    assert "`core`" in text
    assert "解析失败" in text


def test_console_shows_skipped_files_and_modules(capsys):
    report = AgentReport(parse_failures=[FAILURE], module_stats=MODULES)

    ReportGenerator.print_console(report)

    captured = capsys.readouterr().out
    assert "Skipped source files (1)" in captured
    assert "Money.java" in captured
    assert "core" in captured
