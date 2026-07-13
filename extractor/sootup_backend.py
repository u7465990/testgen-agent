"""SootUp-based extraction backend — produces full Jimple IR from bytecode.

Requires Java 11+ and SootUp dependencies (auto-resolved via Maven).

How it works:
  1. Resolves SootUp JARs from ~/.m2/repository or via Maven
  2. Compiles SootUpExtractor.java (one-time)
  3. For each target class, runs the extractor as a subprocess
  4. Parses JSON output → merges Jimple into MethodInfo
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Optional, Set

from extractor.base import ExtractorBackend
from java_analyzer import SourceFile
from method_extractor import MethodInfo


class SootUpBackend(ExtractorBackend):
    """Backend that uses SootUp (via subprocess) for Jimple IR extraction."""

    def __init__(self, project_name: str = "",
                 java_home: Optional[str] = None,
                 sootup_jars: Optional[List[Path]] = None):
        self._project_name = project_name
        self._java_home = java_home or os.environ.get("JAVA_HOME", "")
        self._sootup_jars = sootup_jars or []
        self._compiled = False

    @property
    def name(self) -> str:
        return "sootup"

    @property
    def provides_jimple(self) -> bool:
        return True

    # ── Public API ────────────────────────────────────────────

    def extract(self, source_file: SourceFile) -> List[MethodInfo]:
        """Extract methods with Jimple from a compiled class file.

        NOTE: This backend requires the project to be compiled first.
        It looks for .class files in target/classes/ corresponding
        to the source file's qualified name.
        """
        # This backend works per-class, not per-file.
        # We return empty here — the facade calls extract_class() instead.
        return []

    def extract_class(self, class_name: str,
                      classpath: str,
                      source_context: Optional[SourceFile] = None,
                      existing_methods: Optional[List[MethodInfo]] = None
                      ) -> Dict[str, str]:
        """Extract Jimple code for all methods in a class.

        Args:
            class_name: Fully qualified class name (e.g., org.example.MyClass)
            classpath: Java classpath string (; separated on Windows)
            source_context: Optional SourceFile for metadata
            existing_methods: Optional list of MethodInfo to merge Jimple into

        Returns:
            Dict mapping method FQN → Jimple code string
        """
        if not self._ensure_compiled():
            print("  [WARN] SootUp extractor not available, "
                  "returning empty Jimple.")
            return {}

        # Run the Java extractor
        jimple_data = self._run_extractor(class_name, classpath)
        if not jimple_data:
            return {}

        # Build FQN → Jimple map
        result: Dict[str, str] = {}
        for entry in jimple_data:
            method_name = entry.get("method", "")
            jimple_body = entry.get("jimple", "")
            if not method_name:
                continue
            fqn = f"{class_name}.{method_name}"
            result[fqn] = jimple_body

        # If existing_methods provided, merge Jimple into them
        if existing_methods:
            for mi in existing_methods:
                if mi.fqn in result:
                    mi.jimple_code = result[mi.fqn]

        return result

    # ── Java tool management ──────────────────────────────────

    def _ensure_compiled(self) -> bool:
        """Compile SootUpExtractor.java if not already done.

        Returns True if the tool is available.
        """
        tool_source = Path(__file__).parent / "SootUpExtractor.java"
        if not tool_source.is_file():
            print("  [ERROR] SootUpExtractor.java not found.")
            return False

        # Check if Java is available
        javac = self._find_javac()
        if not javac:
            print("  [WARN] javac not found — cannot compile SootUp extractor.")
            return False

        # Resolve SootUp dependencies
        jars = self._resolve_sootup_jars()
        if not jars:
            print("  [WARN] SootUp JARs not found. Try running: "
                  "mvn dependency:copy-dependencies "
                  "in LLM_Test_Gen/Script/")
            return False

        # Compile if needed
        class_file = tool_source.with_suffix("")
        class_dir = Path(__file__).parent
        if (class_dir / "SootUpExtractor.class").is_file():
            self._compiled = True
            self._sootup_jars = jars
            return True

        separator = ";" if sys.platform == "win32" else ":"
        cp = separator.join(str(j) for j in jars)
        out_dir = str(class_dir)

        try:
            result = subprocess.run(
                [str(javac), "-cp", cp, "-d", out_dir, str(tool_source)],
                capture_output=True, text=True, timeout=60,
            )
            if result.returncode != 0:
                print(f"  [WARN] Failed to compile SootUpExtractor:\n"
                      f"{result.stderr[:500]}")
                return False
            self._compiled = True
            self._sootup_jars = jars
            print("  [OK] SootUpExtractor compiled successfully.")
            return True
        except (subprocess.TimeoutExpired, OSError) as e:
            print(f"  [WARN] Compilation failed: {e}")
            return False

    def _run_extractor(self, class_name: str,
                       classpath: str) -> List[dict]:
        """Run the Java Jimple extractor as a subprocess."""
        java = self._find_java()
        if not java:
            return []

        separator = ";" if sys.platform == "win32" else ":"
        class_dir = str(Path(__file__).parent)
        cp = f"{class_dir}{separator}{classpath}"
        if self._sootup_jars:
            cp += f"{separator}{separator.join(str(j) for j in self._sootup_jars)}"

        try:
            result = subprocess.run(
                [str(java), "-cp", cp,
                 "SootUpExtractor", classpath, class_name],
                capture_output=True, text=True, timeout=120,
            )
            if result.returncode != 0:
                print(f"  [WARN] SootUpExtractor returned "
                      f"{result.returncode}: {result.stderr[:300]}")
                return []
            if not result.stdout.strip():
                return []
            return json.loads(result.stdout)
        except (subprocess.TimeoutExpired, OSError, json.JSONDecodeError) as e:
            print(f"  [WARN] SootUpExtractor execution failed: {e}")
            return []

    # ── Dependency resolution ─────────────────────────────────

    def _resolve_sootup_jars(self) -> List[Path]:
        """Find SootUp JARs from local Maven repository.

        Looks in: ~/.m2/repository/org/soot-oss/
        Also checks the existing assignment's Maven target directory.
        """
        jars: List[Path] = []

        # 1. Check Maven local repository
        m2 = Path.home() / ".m2" / "repository" / "org" / "soot-oss"
        if m2.is_dir():
            for root, dirs, files in os.walk(str(m2)):
                for f in files:
                    if f.endswith(".jar"):
                        jars.append(Path(root) / f)

        # 2. Check existing assignment build
        assignment_dir = (Path(__file__).resolve().parent.parent.parent
                          / "LLM_Test_Gen" / "Script" / "target")
        if assignment_dir.is_dir():
            for root, dirs, files in os.walk(str(assignment_dir)):
                for f in files:
                    if f.endswith(".jar"):
                        jars.append(Path(root) / f)

        # 3. Check for Maven dependency:copy-dependencies output
        dep_dir = (Path(__file__).resolve().parent.parent.parent
                   / "LLM_Test_Gen" / "Script" / "target" / "dependency")
        if dep_dir.is_dir():
            for f in dep_dir.iterdir():
                if f.suffix == ".jar":
                    jars.append(f)

        return jars

    # ── Java toolchain detection ──────────────────────────────

    def _find_javac(self) -> Optional[Path]:
        java_home = self._java_home
        if java_home:
            candidate = Path(java_home) / "bin" / "javac"
            if sys.platform == "win32":
                candidate = candidate.with_suffix(".exe")
            if candidate.is_file():
                return candidate
        for path_dir in os.environ.get("PATH", "").split(os.pathsep):
            candidate = Path(path_dir) / "javac"
            if sys.platform == "win32":
                candidate = candidate.with_suffix(".exe")
            if candidate.is_file():
                return candidate
        return None

    def _find_java(self) -> Optional[Path]:
        java_home = self._java_home
        if java_home:
            candidate = Path(java_home) / "bin" / "java"
            if sys.platform == "win32":
                candidate = candidate.with_suffix(".exe")
            if candidate.is_file():
                return candidate
        for path_dir in os.environ.get("PATH", "").split(os.pathsep):
            candidate = Path(path_dir) / "java"
            if sys.platform == "win32":
                candidate = candidate.with_suffix(".exe")
            if candidate.is_file():
                return candidate
        return None
