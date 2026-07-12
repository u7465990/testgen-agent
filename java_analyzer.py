"""Java project analysis — discover source files, build tool, classpath."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple


class SourceFile:
    """A discovered Java source file within the project."""

    def __init__(self, path: Path, package_name: str, module_name: str = ""):
        self.path = path
        self.package_name = package_name
        self.module_name = module_name  # multi-module Maven projects

    @property
    def qualified_name(self) -> str:
        """Fully qualified class name, e.g. org.apache.commons.codec.binary.StringUtils."""
        stem = self.path.stem
        if self.package_name:
            return f"{self.package_name}.{stem}"
        return stem

    def __repr__(self) -> str:
        return f"SourceFile({self.qualified_name})"


class JavaProjectAnalyzer:
    """Discovers project structure, build tool, source files, and classpath."""

    def __init__(self, project_path: Path):
        self.project_path = project_path.resolve()
        self._build_tool: Optional[str] = None

    # ── Build tool detection ──────────────────────────────────

    def detect_build_tool(self) -> str:
        """Detect the project build system."""
        if self._build_tool:
            return self._build_tool
        has_pom = (self.project_path / "pom.xml").is_file()
        has_build_gradle = (self.project_path / "build.gradle").is_file()
        has_build_xml = (self.project_path / "build.xml").is_file()

        if has_pom:
            self._build_tool = "maven"
        elif has_build_gradle:
            self._build_tool = "gradle"
        elif has_build_xml:
            self._build_tool = "ant"
        else:
            self._build_tool = "manual"
        return self._build_tool

    # ── Source file discovery ─────────────────────────────────

    def find_source_files(self) -> List[SourceFile]:
        """Walk standard source directories and return all .java files."""
        candidates = self._source_root_candidates()
        found: List[SourceFile] = []

        for src_root in candidates:
            if not src_root.is_dir():
                continue
            for jfile in src_root.rglob("*.java"):
                pkg = self._package_from_path(jfile, src_root)
                found.append(SourceFile(jfile, pkg))

        # Fallback: walk entire project for .java files if nothing found
        if not found:
            for jfile in self.project_path.rglob("*.java"):
                # ignore test directories and hidden dirs
                if "/test/" in jfile.as_posix() or "/." in jfile.as_posix():
                    continue
                if "test" in jfile.parts:
                    continue
                pkg = self._package_from_fallback(jfile)
                found.append(SourceFile(jfile, pkg))

        return found

    def _source_root_candidates(self) -> List[Path]:
        """Return likely source root directories."""
        standard = ["src/main/java"]
        build_tool = self.detect_build_tool()
        if build_tool == "maven":
            standard = ["src/main/java"]
        elif build_tool == "ant":
            standard = ["src/main/java", "src/java", "java"]
        elif build_tool == "gradle":
            standard = ["src/main/java"]
        return [self.project_path / d for d in standard]

    def _package_from_path(self, jfile: Path, src_root: Path) -> str:
        """Derive package name from file's path relative to source root."""
        try:
            rel = jfile.relative_to(src_root)
        except ValueError:
            return ""
        parts = rel.parent.parts
        return ".".join(p for p in parts if p and p != ".") if parts else ""

    def _package_from_fallback(self, jfile: Path) -> str:
        """Guess package by reading the source file's package declaration."""
        try:
            for line in jfile.open(errors="replace"):
                line = line.strip()
                if line.startswith("package "):
                    return line[len("package "):].rstrip(";").strip()
                if line.startswith("import ") or line.startswith("public class"):
                    break
        except Exception:
            pass
        return ""

    # ── Test directory ────────────────────────────────────────

    def find_test_directory(self) -> Path:
        """Return the path to the project's test source directory, creating if needed."""
        candidates = [
            self.project_path / "src/test/java",
            self.project_path / "test",
            self.project_path / "tests",
        ]
        for d in candidates:
            if d.is_dir():
                return d
        # default
        test_dir = candidates[0]
        test_dir.mkdir(parents=True, exist_ok=True)
        return test_dir

    # ── Classpath resolution ──────────────────────────────────

    def resolve_classpath(self) -> str:
        """Resolve the project classpath as a string suitable for javac -cp."""
        build_tool = self.detect_build_tool()
        cp_entries: List[str] = []

        # Compiled project classes
        classes_dirs = [
            self.project_path / "target/classes",
            self.project_path / "build/classes",
            self.project_path / "bin",
        ]
        for d in classes_dirs:
            if d.is_dir():
                cp_entries.append(str(d))
                break

        # Test classes (for dependencies when compiling tests)
        test_classes_dirs = [
            self.project_path / "target/test-classes",
            self.project_path / "build/test-classes",
        ]
        for d in test_classes_dirs:
            if d.is_dir():
                cp_entries.append(str(d))
                break

        if build_tool == "maven":
            deps = self._resolve_maven_classpath()
            cp_entries.extend(deps)
        elif build_tool == "gradle":
            deps = self._resolve_gradle_classpath()
            cp_entries.extend(deps)
        elif build_tool == "ant":
            deps = self._resolve_ant_classpath()
            cp_entries.extend(deps)

        # Check for a pre-cached classpath.txt
        for cp_file in [
            self.project_path / "classpath.txt",
            self.project_path / "target/classpath.txt",
        ]:
            if cp_file.is_file():
                content = cp_file.read_text().strip()
                if content:
                    cp_entries.extend(content.split(os.pathsep))

        separator = ";" if sys.platform == "win32" else ":"
        return separator.join(str(p) for p in cp_entries if p)

    def _resolve_maven_classpath(self) -> List[str]:
        """Run `mvn dependency:build-classpath` and return entries."""
        cp_file = self.project_path / "target/classpath.txt"
        if not cp_file.parent.is_dir():
            cp_file.parent.mkdir(parents=True, exist_ok=True)

        if not cp_file.is_file():
            try:
                subprocess.run(
                    ["mvn", "dependency:build-classpath",
                     f"-Dmdep.outputFile={cp_file}", "-q"],
                    cwd=str(self.project_path),
                    capture_output=True,
                    text=True,
                    timeout=120,
                )
            except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
                return []

        if cp_file.is_file():
            content = cp_file.read_text().strip()
            if content:
                return content.split(os.pathsep)
        return []

    def _resolve_gradle_classpath(self) -> List[str]:
        """Attempt to get Gradle classpath. Returns empty on failure."""
        try:
            result = subprocess.run(
                ["gradle", "printClasspath"],
                cwd=str(self.project_path),
                capture_output=True,
                text=True,
                timeout=120,
            )
            if result.returncode == 0:
                return [line.strip()
                        for line in result.stdout.splitlines()
                        if line.strip()]
        except (FileNotFoundError, OSError):
            pass
        return []

    def _resolve_ant_classpath(self) -> List[str]:
        """Ant projects: look for lib/ directory with jars."""
        lib_dirs = [
            self.project_path / "lib",
            self.project_path / "libs",
        ]
        jars = []
        for d in lib_dirs:
            if d.is_dir():
                jars.extend(str(p) for p in d.glob("*.jar"))
        return jars

    def find_compiled_classes(self) -> List[Path]:
        """Locate compiled .class files for the project."""
        candidates = [
            self.project_path / "target/classes",
            self.project_path / "build/classes",
            self.project_path / "bin",
        ]
        return [d for d in candidates if d.is_dir()]

    # ── Multi-module Maven support ────────────────────────────

    def find_maven_modules(self) -> List[Path]:
        """Discover Maven sub-modules via the parent pom.xml."""
        modules: List[Path] = []
        pom = self.project_path / "pom.xml"
        if not pom.is_file():
            return modules
        # Simple heuristic: look for sub-module directories with their own pom.xml
        for candidate in self.project_path.iterdir():
            if candidate.is_dir() and (candidate / "pom.xml").is_file():
                modules.append(candidate)
        return modules
