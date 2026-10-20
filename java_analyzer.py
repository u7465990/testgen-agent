"""Java project analysis — discover source files, build tool, classpath."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from runlog import get_logger

logger = get_logger(__name__)


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
        self._modules: Optional[List[Path]] = None

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
        """Walk every module's standard source directories for .java files.

        A multi-module Maven project has no sources at the root: each module
        keeps its own `src/main/java`. Walking only the root used to yield zero
        files (or, worse, the whole-project fallback occasionally found them),
        so module roots and the root project are both walked here. Each source
        file carries the module it belongs to, which is what lets the report
        say *where* a file was lost or a test was written.

        Order is the root project first, then modules sorted by name. Within a
        module the rglob order is preserved: generated class names are derived
        from a counter, and re-sorting existing single-module projects would
        rename every committed test.
        """
        module_roots = self.find_module_roots()
        roots: List[Tuple[str, Path]] = [("", self.project_path)]
        roots.extend(module_roots)

        found: List[SourceFile] = []
        seen: set = set()
        for module_name, root in roots:
            for src_root in self._source_roots_for(root):
                if not src_root.is_dir():
                    continue
                for jfile in src_root.rglob("*.java"):
                    key = os.path.normcase(str(jfile.resolve()))
                    if key in seen:
                        continue
                    seen.add(key)
                    pkg = self._package_from_path(jfile, src_root)
                    found.append(SourceFile(jfile, pkg, module_name))

        # Fallback: walk entire project for .java files if nothing found
        if not found:
            for jfile in self.project_path.rglob("*.java"):
                # ignore test directories and hidden dirs
                if "/test/" in jfile.as_posix() or "/." in jfile.as_posix():
                    continue
                if "test" in jfile.parts:
                    continue
                pkg = self._package_from_fallback(jfile)
                found.append(SourceFile(
                    jfile, pkg, self.module_name_for_path(jfile)
                ))

        return found

    def _source_root_candidates(self) -> List[Path]:
        """Return likely source root directories for the root project."""
        return self._source_roots_for(self.project_path)

    def _source_roots_for(self, root: Path) -> List[Path]:
        """Standard source roots below one project/module directory."""
        standard = ["src/main/java"]
        build_tool = self.detect_build_tool()
        if build_tool == "ant":
            standard = ["src/main/java", "src/java", "java"]
        return [root / d for d in standard]

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

        # Dedupe, preserving order. The Maven resolver both returns the
        # entries and caches them to target/classpath.txt, which the
        # pre-cached block above then reads — so deps arrive twice.
        resolved: List[str] = []
        seen: set = set()
        for entry in (str(p) for p in cp_entries if p):
            key = os.path.normcase(os.path.normpath(entry))
            if key not in seen:
                seen.add(key)
                resolved.append(entry)

        # A classpath with no project classes directory is the failure mode
        # that makes every generated test fail with "cannot find symbol", so
        # say so explicitly rather than leaving it to be inferred.
        logger.debug("classpath resolved (build tool=%s, %d entries):",
                     build_tool, len(resolved))
        for entry in resolved:
            logger.debug("  %s", entry)
        if not any(Path(e).is_dir() and Path(e).name in
                   ("classes", "main", "bin") for e in resolved):
            logger.debug("  NOTE: no compiled project classes on the classpath")

        return separator.join(resolved)

    def _pom_is_newer_than(self, cp_file: Path) -> bool:
        """True when a build file has been touched since the cache was written.

        Module poms count too: in a multi-module build a dependency usually
        lands in a module's pom, which does not change the root pom's mtime.
        """
        try:
            cache_mtime = cp_file.stat().st_mtime
        except OSError:
            return True
        candidates = [self.project_path / "pom.xml"]
        if self.project_path.is_dir():
            try:
                candidates.extend(
                    d / "pom.xml" for d in self.project_path.iterdir()
                    if d.is_dir()
                )
            except OSError:
                pass
        for pom in candidates:
            try:
                if pom.is_file() and pom.stat().st_mtime > cache_mtime:
                    return True
            except OSError:
                continue
        return False

    def invalidate_classpath_cache(self) -> None:
        """Drop the on-disk classpath cache so the next resolve re-runs Maven.

        Used after the agent modifies a pom: relying on mtime alone is fragile
        (coarse timestamp resolution, same-second writes).
        """
        try:
            (self.project_path / "target/classpath.txt").unlink(missing_ok=True)
        except OSError:
            pass

    def _resolve_maven_classpath(self) -> List[str]:
        """Run `mvn dependency:build-classpath` and return entries."""
        cp_file = self.project_path / "target/classpath.txt"
        if not cp_file.parent.is_dir():
            cp_file.parent.mkdir(parents=True, exist_ok=True)

        # Re-resolve when the build file is newer than the cache. Without this
        # the cached file is read forever, so a dependency added to the pom
        # never reaches `javac` — while `mvn test` and PiTest, which read the
        # pom directly, do see it. That asymmetry makes a fixed project look
        # like a broken heuristic.
        cache_is_fresh = cp_file.is_file() and not self._pom_is_newer_than(cp_file)

        if not cache_is_fresh:
            mvn = self._find_mvn()
            if not mvn:
                return []
            cmd = [
                mvn, "dependency:build-classpath",
                f"-Dmdep.outputFile={cp_file}",
                "-Dmdep.includeScope=test",  # include test-scope deps (JUnit)
                "-q",
            ]
            # On Windows `mvn` is mvn.cmd and must run through cmd.exe
            if sys.platform == "win32" and mvn.lower().endswith((".cmd", ".bat")):
                cmd = ["cmd", "/c"] + cmd
            try:
                subprocess.run(
                    cmd,
                    cwd=str(self.project_path),
                    capture_output=True,
                    text=True,
                    timeout=180,
                )
            except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
                return []

        if cp_file.is_file():
            content = cp_file.read_text().strip()
            if content:
                return content.split(os.pathsep)
        return []

    @staticmethod
    def _find_mvn() -> Optional[str]:
        """Locate the mvn executable (mvn.cmd / mvn.bat on Windows)."""
        for name in ("mvn", "mvn.cmd", "mvn.bat"):
            found = shutil.which(name)
            if found:
                return found
        return None

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
        """Sub-module directories declared by the root pom's <modules>.

        Maven's semantics are used, not a directory heuristic: a directory
        that merely contains a pom.xml is not a module unless the root pom
        declares it. The old heuristic treated example/fixture directories as
        modules, which made a single-module project look multi-module.
        """
        if self._modules is not None:
            return list(self._modules)

        pom = self.project_path / "pom.xml"
        modules: List[Path] = []
        if pom.is_file():
            try:
                root = ET.parse(str(pom)).getroot()
            except (ET.ParseError, OSError):
                root = None
            if root is not None:
                for element in root.iter():
                    if self._local_name(element.tag) != "module":
                        continue
                    rel = (element.text or "").strip()
                    if not rel:
                        continue
                    candidate = (self.project_path / rel).resolve()
                    try:
                        candidate.relative_to(self.project_path)
                    except ValueError:
                        continue  # a module path escaping the project root
                    if candidate.is_dir() and (candidate / "pom.xml").is_file():
                        if candidate not in modules:
                            modules.append(candidate)

        self._modules = modules
        return list(modules)

    @staticmethod
    def _local_name(tag: str) -> str:
        """Element name without the POM XML namespace."""
        return tag.rsplit("}", 1)[-1] if "}" in tag else tag

    def find_module_roots(self) -> List[Tuple[str, Path]]:
        """(display name, path) for each declared module, sorted by name.

        The display name is the module path relative to the project root,
        e.g. "core" or "services/billing" — the same value Maven writes inside
        <module>, so it can be matched against build output and reports.
        """
        roots: List[Tuple[str, Path]] = []
        for module in self.find_maven_modules():
            try:
                name = module.relative_to(self.project_path).as_posix()
            except ValueError:
                name = module.name
            roots.append((name, module))
        return sorted(roots, key=lambda item: item[0])

    def module_name_for_path(self, path: Path) -> str:
        """The declared module a path belongs to, or "" for the root project."""
        try:
            resolved = path.resolve()
        except OSError:
            resolved = path
        best = ""
        best_len = -1
        for name, root in self.find_module_roots():
            try:
                resolved.relative_to(root)
            except ValueError:
                continue
            if len(str(root)) > best_len:
                best, best_len = name, len(str(root))
        return best
