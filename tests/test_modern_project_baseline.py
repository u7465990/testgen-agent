"""M0 baseline: a fixed modern Java project with a known, recorded gap.

The point is not that the tool handles this project today. It is that the
project's current limits are written down as an executable expectation, so the
M1 parser swap can show the gap closing without letting anything else regress.

At M0 javalang cannot parse five files (a record, two switch expressions,
pattern matching, a text block). They MUST appear in parse_failures. When M1
lands, EXPECTED_SKIPPED becomes an empty set and the parsed method count rises;
that change should be made deliberately, together with the new backend.

Everything here is offline: javalang only, no JDK and no Maven.
"""

from __future__ import annotations

from collections import Counter
from pathlib import Path

from java_analyzer import JavaProjectAnalyzer
from method_extractor import MethodExtractor

FIXTURE = (
    Path(__file__).resolve().parent.parent
    / "examples/demo-project-multimodule"
)

EXPECTED_SOURCE_FILES = {"app": 1, "core": 6, "service": 2}
EXPECTED_METHODS = {"app": 2, "core": 2, "service": 3}
EXPECTED_SKIPPED = {
    "Money.java",
    "OrderStatus.java",
    "TicketFormatter.java",
    "TypeChecks.java",
    "ServiceStatus.java",
}
EXPECTED_PARSED = {
    "Main.java",
    "MathUtil.java",
    # Parses, but yields no methods: interface methods are a separate,
    # pre-existing extraction limitation, not part of the M0 syntax gap.
    "PaymentGateway.java",
    "PaymentService.java",
}


def _analysis():
    analyzer = JavaProjectAnalyzer(FIXTURE)
    sources = analyzer.find_source_files()
    extractor = MethodExtractor(project_name="demo-project-multimodule")
    methods = {src.path: extractor.extract_methods(src) for src in sources}
    return sources, methods, extractor.parse_failures


def test_the_fixture_exists():
    assert (FIXTURE / "pom.xml").is_file()
    assert (FIXTURE / "core/src/main/java").is_dir()


def test_modules_are_discovered_from_the_root_pom():
    analyzer = JavaProjectAnalyzer(FIXTURE)
    assert [name for name, _ in analyzer.find_module_roots()] == [
        "app", "core", "service",
    ]


def test_source_and_method_counts_are_the_known_baseline():
    sources, methods, _ = _analysis()

    assert dict(Counter(src.module_name for src in sources)) == \
        EXPECTED_SOURCE_FILES
    method_counts = Counter()
    for src in sources:
        method_counts[src.module_name] += len(methods[src.path])
    assert dict(method_counts) == EXPECTED_METHODS


def test_every_modern_syntax_file_is_reported_not_silently_lost():
    sources, _, failures = _analysis()

    assert {Path(f["file"]).name for f in failures} == EXPECTED_SKIPPED
    assert {f["module"] for f in failures} == {"core", "service"}

    # Account for every file: it either parsed or is in the failure list.
    failed = {f["file"] for f in failures}
    parsed = {str(src.path) for src in sources} - failed
    assert {Path(p).name for p in parsed} == EXPECTED_PARSED
