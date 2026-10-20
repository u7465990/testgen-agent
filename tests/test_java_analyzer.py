"""Tests for java_analyzer.py — build tool, source discovery, classpath.

Everything here is offline and needs no JDK: the Maven resolver is never given
a chance to run. That is deliberate on two counts — the offline CI job has no
Maven installed, and a real `mvn dependency:build-classpath` inside a unit test
would be slow, network-bound and non-deterministic. Where a test needs a "maven
project", it stubs `_find_mvn` to return None, which is exactly the
no-Maven-installed path.

The classpath tests cover the two behaviours CLAUDE.md calls out as past bugs:
the dedupe (the Maven resolver returns its entries *and* caches them to
target/classpath.txt, which the pre-cached block then re-reads) and the
staleness check (a cached classpath.txt used to be read forever, so a
dependency added to the pom never reached javac while `mvn test` did see it).

Paths are asserted against `analyzer.project_path`, not `tmp_path` — the
analyzer calls `.resolve()` on what it is given, and on Windows that is not
always the identity.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from java_analyzer import JavaProjectAnalyzer, SourceFile


def _write(path: Path, text: str = "") -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def _entries(classpath: str):
    return [Path(e) for e in classpath.split(os.pathsep) if e]


@pytest.fixture
def no_maven(monkeypatch):
    """Make the Maven resolver a no-op, as on a machine without Maven."""
    monkeypatch.setattr(
        JavaProjectAnalyzer, "_find_mvn", staticmethod(lambda: None)
    )


class TestDetectBuildTool:
    @pytest.mark.parametrize(
        "marker,expected",
        [("pom.xml", "maven"), ("build.gradle", "gradle"),
         ("build.xml", "ant")],
    )
    def test_detects_from_the_build_file(self, tmp_path, marker, expected):
        _write(tmp_path / marker, "<project/>")
        assert JavaProjectAnalyzer(tmp_path).detect_build_tool() == expected

    def test_manual_when_there_is_no_build_file(self, tmp_path):
        assert JavaProjectAnalyzer(tmp_path).detect_build_tool() == "manual"

    def test_maven_wins_when_several_markers_are_present(self, tmp_path):
        _write(tmp_path / "pom.xml", "<project/>")
        _write(tmp_path / "build.gradle", "")
        assert JavaProjectAnalyzer(tmp_path).detect_build_tool() == "maven"

    def test_the_result_is_cached(self, tmp_path):
        _write(tmp_path / "pom.xml", "<project/>")
        analyzer = JavaProjectAnalyzer(tmp_path)
        assert analyzer.detect_build_tool() == "maven"
        # Deleting the marker mid-run must not flip the answer: one detection
        # per analyzer is the point of the cache.
        (analyzer.project_path / "pom.xml").unlink()
        assert analyzer.detect_build_tool() == "maven"


class TestSourceFile:
    def test_qualified_name_joins_package_and_stem(self, tmp_path):
        src = SourceFile(tmp_path / "Foo.java", "com.demo")
        assert src.qualified_name == "com.demo.Foo"

    def test_qualified_name_without_a_package(self, tmp_path):
        assert SourceFile(tmp_path / "Foo.java", "").qualified_name == "Foo"

    def test_repr_names_the_class(self, tmp_path):
        src = SourceFile(tmp_path / "Foo.java", "com.demo")
        assert "com.demo.Foo" in repr(src)


class TestFindSourceFiles:
    def test_walks_the_standard_maven_root(self, tmp_path):
        analyzer = JavaProjectAnalyzer(tmp_path)
        root = analyzer.project_path
        _write(root / "pom.xml", "<project/>")
        _write(root / "src/main/java/com/demo/Foo.java", "package com.demo;")
        _write(root / "src/main/java/com/demo/Bar.java", "package com.demo;")

        found = analyzer.find_source_files()

        assert sorted(f.path.stem for f in found) == ["Bar", "Foo"]
        assert {f.package_name for f in found} == {"com.demo"}

    def test_subdirectory_becomes_the_package(self, tmp_path):
        analyzer = JavaProjectAnalyzer(tmp_path)
        _write(analyzer.project_path / "src/main/java/org/example/deep/Foo.java")
        (found,) = analyzer.find_source_files()
        assert found.package_name == "org.example.deep"
        assert found.qualified_name == "org.example.deep.Foo"

    def test_file_at_the_source_root_has_no_package(self, tmp_path):
        analyzer = JavaProjectAnalyzer(tmp_path)
        _write(analyzer.project_path / "src/main/java/Foo.java")
        (found,) = analyzer.find_source_files()
        assert found.package_name == ""

    def test_falls_back_to_a_whole_project_walk(self, tmp_path):
        # No src/main/java — the sources sit wherever the author put them.
        analyzer = JavaProjectAnalyzer(tmp_path)
        _write(analyzer.project_path / "demo/Foo.java", "package com.x;\n")
        (found,) = analyzer.find_source_files()
        assert found.path.stem == "Foo"
        # In this mode the package comes from the file's own declaration.
        assert found.package_name == "com.x"

    def test_fallback_skips_test_directories(self, tmp_path):
        analyzer = JavaProjectAnalyzer(tmp_path)
        _write(analyzer.project_path / "demo/Foo.java", "package com.x;\n")
        _write(analyzer.project_path / "demo/test/Bar.java", "package com.x;\n")
        found = analyzer.find_source_files()
        assert [f.path.stem for f in found] == ["Foo"]

    def test_empty_project_finds_nothing(self, tmp_path):
        assert JavaProjectAnalyzer(tmp_path).find_source_files() == []


class TestPackageFromFallback:
    def test_reads_the_package_declaration(self, tmp_path):
        analyzer = JavaProjectAnalyzer(tmp_path)
        path = _write(analyzer.project_path / "Foo.java",
                      "package a.b;\n\npublic class Foo {}")
        assert analyzer._package_from_fallback(path) == "a.b"

    def test_no_declaration_yields_empty(self, tmp_path):
        analyzer = JavaProjectAnalyzer(tmp_path)
        path = _write(analyzer.project_path / "Foo.java", "public class Foo {}")
        assert analyzer._package_from_fallback(path) == ""

    def test_stops_at_the_first_import(self, tmp_path):
        # A `package` line after an import is not a declaration; stopping early
        # is what keeps a stray later match from being read as one.
        analyzer = JavaProjectAnalyzer(tmp_path)
        path = _write(analyzer.project_path / "Foo.java",
                      "import java.util.List;\npackage late;")
        assert analyzer._package_from_fallback(path) == ""


class TestSourceRootCandidates:
    def test_maven_only_looks_at_src_main_java(self, tmp_path):
        analyzer = JavaProjectAnalyzer(tmp_path)
        _write(analyzer.project_path / "pom.xml", "<project/>")
        assert analyzer._source_root_candidates() == \
            [analyzer.project_path / "src/main/java"]

    def test_ant_also_looks_at_src_java_and_java(self, tmp_path):
        analyzer = JavaProjectAnalyzer(tmp_path)
        _write(analyzer.project_path / "build.xml", "<project/>")
        assert analyzer._source_root_candidates() == [
            analyzer.project_path / d for d in ("src/main/java", "src/java", "java")
        ]

    def test_gradle_uses_the_standard_root(self, tmp_path):
        analyzer = JavaProjectAnalyzer(tmp_path)
        _write(analyzer.project_path / "build.gradle", "")
        assert analyzer._source_root_candidates() == \
            [analyzer.project_path / "src/main/java"]


class TestFindTestDirectory:
    def test_returns_an_existing_candidate(self, tmp_path):
        analyzer = JavaProjectAnalyzer(tmp_path)
        (analyzer.project_path / "test").mkdir()
        assert analyzer.find_test_directory() == analyzer.project_path / "test"

    def test_prefers_src_test_java(self, tmp_path):
        analyzer = JavaProjectAnalyzer(tmp_path)
        (analyzer.project_path / "src/test/java").mkdir(parents=True)
        (analyzer.project_path / "test").mkdir()
        assert analyzer.find_test_directory() == \
            analyzer.project_path / "src/test/java"

    def test_creates_the_default_when_none_exists(self, tmp_path):
        analyzer = JavaProjectAnalyzer(tmp_path)
        result = analyzer.find_test_directory()
        assert result == analyzer.project_path / "src/test/java"
        assert result.is_dir()


class TestResolveClasspath:
    def test_uses_the_compiled_classes_directory(self, tmp_path, no_maven):
        analyzer = JavaProjectAnalyzer(tmp_path)
        (analyzer.project_path / "target/classes").mkdir(parents=True)
        assert analyzer.project_path / "target/classes" in \
            _entries(analyzer.resolve_classpath())

    def test_also_includes_test_classes(self, tmp_path, no_maven):
        analyzer = JavaProjectAnalyzer(tmp_path)
        (analyzer.project_path / "target/classes").mkdir(parents=True)
        (analyzer.project_path / "target/test-classes").mkdir(parents=True)
        entries = _entries(analyzer.resolve_classpath())
        assert analyzer.project_path / "target/test-classes" in entries

    def test_empty_for_an_unbuilt_manual_project(self, tmp_path):
        assert JavaProjectAnalyzer(tmp_path).resolve_classpath() == ""

    def test_precached_classpath_file_is_read(self, tmp_path):
        _write(tmp_path / "classpath.txt", "/jars/a.jar")
        assert Path("/jars/a.jar") in \
            _entries(JavaProjectAnalyzer(tmp_path).resolve_classpath())

    def test_entries_are_joined_with_the_platform_separator(self, tmp_path):
        _write(tmp_path / "classpath.txt", os.pathsep.join(["/a.jar", "/b.jar"]))
        assert JavaProjectAnalyzer(tmp_path).resolve_classpath() == \
            os.pathsep.join(["/a.jar", "/b.jar"])

    def test_duplicate_entries_are_dropped(self, tmp_path, monkeypatch):
        # The documented bug: the Maven resolver *returns* its entries and also
        # caches them to target/classpath.txt, which the pre-cached block then
        # re-reads — so every dependency arrived twice, and again through
        # `compile(extra_classpath=...)`.
        _write(tmp_path / "pom.xml", "<project/>")
        _write(tmp_path / "target/classpath.txt", "/jars/junit.jar")
        analyzer = JavaProjectAnalyzer(tmp_path)
        monkeypatch.setattr(analyzer, "_resolve_maven_classpath",
                            lambda: ["/jars/junit.jar"])

        entries = _entries(analyzer.resolve_classpath())

        assert entries.count(Path("/jars/junit.jar")) == 1

    def test_no_maven_installed_is_not_an_error(self, tmp_path, no_maven):
        analyzer = JavaProjectAnalyzer(tmp_path)
        _write(analyzer.project_path / "pom.xml", "<project/>")
        (analyzer.project_path / "target/classes").mkdir(parents=True)
        assert _entries(analyzer.resolve_classpath()) == \
            [analyzer.project_path / "target/classes"]


class TestPomIsNewerThan:
    """The staleness check: a cached classpath.txt must not outlive the pom."""

    def _analyzer_with_cache(self, tmp_path, cache_mtime, pom_mtime):
        analyzer = JavaProjectAnalyzer(tmp_path)
        _write(analyzer.project_path / "pom.xml", "<project/>")
        cache = _write(analyzer.project_path / "target/classpath.txt", "/jars/a.jar")
        os.utime(cache, (cache_mtime, cache_mtime))
        os.utime(analyzer.project_path / "pom.xml", (pom_mtime, pom_mtime))
        return analyzer, cache

    def test_newer_pom_means_stale(self, tmp_path):
        analyzer, cache = self._analyzer_with_cache(tmp_path, 1000, 2000)
        assert analyzer._pom_is_newer_than(cache) is True

    def test_older_pom_means_fresh(self, tmp_path):
        analyzer, cache = self._analyzer_with_cache(tmp_path, 2000, 1000)
        assert analyzer._pom_is_newer_than(cache) is False

    def test_module_pom_counts_too(self, tmp_path):
        # In a multi-module build the dependency usually lands in a module's
        # pom, which leaves the root pom's mtime untouched.
        analyzer, cache = self._analyzer_with_cache(tmp_path, 2000, 1000)
        module_pom = _write(analyzer.project_path / "module/pom.xml", "<project/>")
        os.utime(module_pom, (3000, 3000))
        assert analyzer._pom_is_newer_than(cache) is True

    def test_missing_cache_counts_as_stale(self, tmp_path):
        analyzer = JavaProjectAnalyzer(tmp_path)
        assert analyzer._pom_is_newer_than(analyzer.project_path / "nope.txt") is True


class TestInvalidateClasspathCache:
    def test_deletes_the_cached_file(self, tmp_path):
        analyzer = JavaProjectAnalyzer(tmp_path)
        cache = _write(analyzer.project_path / "target/classpath.txt", "/jars/a.jar")
        analyzer.invalidate_classpath_cache()
        assert not cache.exists()

    def test_is_a_noop_when_there_is_no_cache(self, tmp_path):
        JavaProjectAnalyzer(tmp_path).invalidate_classpath_cache()  # must not raise


class TestAntClasspath:
    def test_collects_jars_from_lib_and_libs(self, tmp_path):
        analyzer = JavaProjectAnalyzer(tmp_path)
        _write(analyzer.project_path / "lib/a.jar")
        _write(analyzer.project_path / "libs/b.jar")
        _write(analyzer.project_path / "lib/notes.txt", "not a jar")
        jars = analyzer._resolve_ant_classpath()
        assert sorted(Path(j).name for j in jars) == ["a.jar", "b.jar"]

    def test_no_lib_directories_yields_nothing(self, tmp_path):
        assert JavaProjectAnalyzer(tmp_path)._resolve_ant_classpath() == []


class TestFindCompiledClasses:
    def test_returns_existing_output_directories(self, tmp_path):
        analyzer = JavaProjectAnalyzer(tmp_path)
        (analyzer.project_path / "build/classes").mkdir(parents=True)
        assert analyzer.find_compiled_classes() == \
            [analyzer.project_path / "build/classes"]

    def test_nothing_built_yields_nothing(self, tmp_path):
        assert JavaProjectAnalyzer(tmp_path).find_compiled_classes() == []


class TestFindMavenModules:
    def test_declared_submodule_is_a_module(self, tmp_path):
        analyzer = JavaProjectAnalyzer(tmp_path)
        _write(
            analyzer.project_path / "pom.xml",
            "<project><modules><module>core</module></modules></project>",
        )
        _write(analyzer.project_path / "core/pom.xml", "<project/>")
        assert analyzer.find_maven_modules() == [analyzer.project_path / "core"]

    def test_undeclared_subdirectory_with_a_pom_is_not_a_module(self, tmp_path):
        # Maven's semantics, not "any directory that contains a pom.xml".
        # The old heuristic treated an example/fixture directory as a module.
        analyzer = JavaProjectAnalyzer(tmp_path)
        _write(analyzer.project_path / "pom.xml", "<project/>")
        _write(analyzer.project_path / "core/pom.xml", "<project/>")
        (analyzer.project_path / "docs").mkdir()
        assert analyzer.find_maven_modules() == []

    def test_namespaced_pom_modules_are_found(self, tmp_path):
        analyzer = JavaProjectAnalyzer(tmp_path)
        _write(
            analyzer.project_path / "pom.xml",
            '<project xmlns="http://maven.apache.org/POM/4.0.0">'
            "<modules><module>core</module></modules></project>",
        )
        _write(analyzer.project_path / "core/pom.xml", "<project/>")
        assert analyzer.find_maven_modules() == [analyzer.project_path / "core"]

    def test_nested_module_path_is_preserved_as_its_name(self, tmp_path):
        analyzer = JavaProjectAnalyzer(tmp_path)
        _write(
            analyzer.project_path / "pom.xml",
            "<project><modules><module>services/billing</module>"
            "</modules></project>",
        )
        _write(analyzer.project_path / "services/billing/pom.xml", "<project/>")
        assert analyzer.find_module_roots() == [
            ("services/billing", analyzer.project_path / "services/billing")
        ]

    def test_without_a_root_pom_there_are_no_modules(self, tmp_path):
        analyzer = JavaProjectAnalyzer(tmp_path)
        _write(analyzer.project_path / "core/pom.xml", "<project/>")
        assert analyzer.find_maven_modules() == []


class TestFindSourceFilesInModules:
    def _multi_module(self, tmp_path):
        analyzer = JavaProjectAnalyzer(tmp_path)
        root = analyzer.project_path
        _write(
            root / "pom.xml",
            "<project><modules><module>core</module>"
            "<module>service</module></modules></project>",
        )
        _write(root / "core/pom.xml", "<project/>")
        _write(root / "service/pom.xml", "<project/>")
        _write(
            root / "core/src/main/java/com/example/core/A.java",
            "package com.example.core;",
        )
        _write(
            root / "service/src/main/java/com/example/service/B.java",
            "package com.example.service;",
        )
        return analyzer

    def test_each_module_keeps_its_own_sources(self, tmp_path):
        analyzer = self._multi_module(tmp_path)
        found = analyzer.find_source_files()
        assert {(f.module_name, f.path.stem) for f in found} == {
            ("core", "A"), ("service", "B"),
        }
        assert {f.package_name for f in found} == {
            "com.example.core", "com.example.service",
        }

    def test_root_sources_are_kept_alongside_modules(self, tmp_path):
        analyzer = self._multi_module(tmp_path)
        _write(
            analyzer.project_path / "src/main/java/com/example/root/Root.java",
            "package com.example.root;",
        )
        found = analyzer.find_source_files()
        assert {(f.module_name, f.path.stem) for f in found} == {
            ("", "Root"), ("core", "A"), ("service", "B"),
        }

    def test_module_name_for_path_uses_the_deepest_module(self, tmp_path):
        analyzer = self._multi_module(tmp_path)
        module_file = analyzer.project_path / "core/src/main/java/com/example/core/A.java"
        assert analyzer.module_name_for_path(module_file) == "core"
        assert analyzer.module_name_for_path(analyzer.project_path / "pom.xml") == ""

    def test_fallback_attributes_files_to_their_module(self, tmp_path):
        # No standard src/main/java anywhere: the whole-project walk still has
        # to say which module a file came from.
        analyzer = JavaProjectAnalyzer(tmp_path)
        _write(
            analyzer.project_path / "pom.xml",
            "<project><modules><module>core</module></modules></project>",
        )
        _write(analyzer.project_path / "core/pom.xml", "<project/>")
        _write(
            analyzer.project_path / "core/demo/Foo.java",
            "package com.example;\n",
        )
        (found,) = analyzer.find_source_files()
        assert found.module_name == "core"
