"""Java compilation — classpath resolution and javac invocation."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from typing import Optional, Tuple

from config import AgentConfig
from java_analyzer import JavaProjectAnalyzer


class JavaCompiler:
    """Resolves classpath and compiles Java test files with javac."""

    def __init__(self, config: AgentConfig):
        self.config = config
        self.project_path = config.project_path
        self._analyzer = JavaProjectAnalyzer(config.project_path)
        self._classpath: Optional[str] = None

    def resolve_classpath(self) -> str:
        """Get the project classpath, caching the result."""
        if self._classpath is not None:
            return self._classpath
        self._classpath = self._analyzer.resolve_classpath()
        return self._classpath

    def find_javac(self) -> Optional[Path]:
        """Locate the javac binary."""
        java_home = self.config.get_java_home()
        if java_home:
            candidate = Path(java_home) / "bin" / "javac"
            if sys.platform == "win32":
                candidate = candidate.with_suffix(".exe")
            if candidate.is_file():
                return candidate

        # Fallback: search PATH
        for path_dir in os.environ.get("PATH", "").split(os.pathsep):
            candidate = Path(path_dir) / "javac"
            if sys.platform == "win32":
                candidate = candidate.with_suffix(".exe")
            if candidate.is_file():
                return candidate
        return None

    def compile(
        self, java_file: Path, extra_classpath: str = ""
    ) -> Tuple[bool, str]:
        """
        Compile a single .java file against the project classpath.

        Returns:
            (success: bool, error_output: str)
        """
        javac = self.find_javac()
        if not javac:
            return False, "javac not found. Set JAVA_HOME or add javac to PATH."

        classpath = self.resolve_classpath()
        if extra_classpath:
            separator = ";" if sys.platform == "win32" else ":"
            classpath = f"{classpath}{separator}{extra_classpath}"

        # Output directory for .class files
        output_dirs = [
            self.project_path / "target/test-classes",
            self.project_path / "build/test-classes",
        ]
        output_dir = None
        for d in output_dirs:
            if d.is_dir():
                output_dir = d
                break
        if not output_dir:
            output_dir = self.project_path / "target/test-classes"
        output_dir.mkdir(parents=True, exist_ok=True)

        cmd = [
            str(javac),
            "-cp", classpath,
            "-d", str(output_dir),
            "-encoding", "UTF-8",
            "-source", "8",
            "-target", "8",
            "-Xlint:-options",
            str(java_file),
        ]

        try:
            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=60
            )
            if result.returncode == 0:
                return True, ""
            # Extract the actual javac errors (skip lines that are just notes)
            stderr = (result.stderr or "").strip()
            return False, stderr
        except subprocess.TimeoutExpired:
            return False, "javac timed out (60s)"
        except FileNotFoundError:
            return False, f"javac not found at {javac}"
        except OSError as e:
            return False, f"javac error: {e}"

    @staticmethod
    def get_output_dir(project_path: Path) -> Path:
        """Return a writable directory for compiled .class files."""
        candidates = [
            project_path / "target/test-classes",
            project_path / "build/test-classes",
        ]
        for d in candidates:
            if d.is_dir():
                return d
        d = project_path / "target/test-classes"
        d.mkdir(parents=True, exist_ok=True)
        return d

    @staticmethod
    def force_fix_package(java_file: Path, correct_package: str) -> bool:
        """
        Automatically fix the package declaration in a .java file.
        Returns True if the file was modified.
        """
        if not java_file.is_file() or not correct_package:
            return False
        import re
        content = java_file.read_text(encoding="utf-8")
        new_content = re.sub(
            r"^package\s+[\w.]+;",
            f"package {correct_package};",
            content,
            count=1,
            flags=re.MULTILINE,
        )
        if new_content != content:
            java_file.write_text(new_content, encoding="utf-8")
            return True
        return False
