"""Method extraction facade — selects backend and merges results."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

from java_analyzer import SourceFile
from target_profile import TargetProfile


# ── Data model ────────────────────────────────────────────────

@dataclass
class MethodInfo:
    """All extracted information about one Java method."""

    project_name: str
    source_file: str
    class_name: str
    package_name: str
    method_name: str
    fqn: str                     # e.g. org.example.MyClass.myMethod(int,String)
    signature: str               # e.g. void myMethod(int, String)
    return_type: str
    parameter_types: List[str]
    parameter_names: List[str]
    modifiers: List[str]
    is_private: bool = False
    is_static: bool = False
    is_abstract: bool = False
    is_constructor: bool = False
    throws_exceptions: List[str] = field(default_factory=list)
    source_code: str = ""        # Full method source including signature + body
    method_body: str = ""        # Just the body
    class_context: str = ""      # Fields + constructors summary of enclosing class
    imports: List[str] = field(default_factory=list)
    allowed_imports: List[str] = field(default_factory=list)
    branch_conditions: List[str] = field(default_factory=list)
    jimple_code: str = ""        # SootUp Jimple IR (empty if not available)

    def __repr__(self) -> str:
        return f"MethodInfo({self.fqn})"


# ── Strings always allowed in generated tests ─────────────────

# Version-independent: reflection (required to invoke private methods) and the
# IO types the prompts are permitted to construct.
_ALWAYS_ALLOWED_COMMON: Set[str] = {
    "java.lang.reflect.Method",
    "java.lang.reflect.InvocationTargetException",
    "java.lang.reflect.*",
    "java.io.ByteArrayInputStream",
    "java.io.ByteArrayOutputStream",
    "java.io.ObjectInputStream",
    "java.io.ObjectOutputStream",
    "java.io.IOException",
}

_ALWAYS_ALLOWED_JUNIT4: Set[str] = {
    "org.junit.Test",
    "org.junit.Assert",
    "org.junit.Assert.*",
    "org.junit.Before",
    "org.junit.After",
    "org.junit.Ignore",
}

# JUnit 5 renamed every one of these (Test stays but Assert did not), and
# assertThrows() takes an Executable — so a lambda-based exception test cannot
# compile unless that type is importable.
_ALWAYS_ALLOWED_JUNIT5: Set[str] = {
    "org.junit.jupiter.api.Test",
    "org.junit.jupiter.api.Assertions",
    "org.junit.jupiter.api.Assertions.*",
    "org.junit.jupiter.api.BeforeEach",
    "org.junit.jupiter.api.AfterEach",
    "org.junit.jupiter.api.BeforeAll",
    "org.junit.jupiter.api.AfterAll",
    "org.junit.jupiter.api.Disabled",
    "org.junit.jupiter.api.function.Executable",
}


def always_allowed(junit_version: int = 4) -> Set[str]:
    """The base import whitelist for a JUnit version (4 or 5)."""
    junit = (
        _ALWAYS_ALLOWED_JUNIT5 if junit_version == 5 else _ALWAYS_ALLOWED_JUNIT4
    )
    return _ALWAYS_ALLOWED_COMMON | junit

KEYWORD_SET: Set[str] = {
    "abstract", "assert", "boolean", "break", "byte", "case", "catch",
    "char", "class", "const", "continue", "default", "do", "double",
    "else", "enum", "extends", "final", "finally", "float", "for",
    "goto", "if", "implements", "import", "instanceof", "int",
    "interface", "long", "native", "new", "package", "private",
    "protected", "public", "return", "short", "static", "strictfp",
    "super", "switch", "synchronized", "this", "throw", "throws",
    "transient", "try", "void", "volatile", "while",
}


# ── Facade: backend selection ─────────────────────────────────

class MethodExtractor:
    """Facade that selects the appropriate extraction backend.

    Modes:
      - "python"  : javalang only (default, pure Python, no Jimple)
      - "sootup"  : javalang + SootUp (requires Java + deps, adds Jimple)
    """

    def __init__(self, project_name: str = "",
                 mode: str = "python",
                 java_home: Optional[str] = None,
                 sootup_jars: Optional[List[Path]] = None,
                 profile: Optional[TargetProfile] = None):
        self.project_name = project_name
        self.mode = mode
        self.profile = profile or TargetProfile()

        # Always use javalang for basic extraction
        from extractor.javalang_backend import JavalangBackend
        self._primary = JavalangBackend(
            project_name=project_name, profile=self.profile
        )

        # Conditionally add SootUp
        self._sootup = None
        if mode == "sootup":
            try:
                from extractor.sootup_backend import SootUpBackend
                self._sootup = SootUpBackend(
                    project_name=project_name,
                    java_home=java_home,
                    sootup_jars=sootup_jars or [],
                )
            except Exception as e:
                print(f"  [WARN] Failed to init SootUp backend: {e}")
                print(f"  [WARN] Falling back to javalang only.")

    def extract_methods(self, source_file: SourceFile) -> List[MethodInfo]:
        """Extract methods from a source file.

        Uses the primary backend (javalang) for base extraction,
        then optionally enriches with Jimple from SootUp.
        """
        methods = self._primary.extract(source_file)
        if not methods:
            return methods

        if self._sootup and self._sootup.provides_jimple:
            self._merge_jimple(source_file, methods)

        return methods

    def _merge_jimple(self, source_file: SourceFile,
                      methods: List[MethodInfo]) -> None:
        """Merge Jimple IR from SootUp into extracted methods."""
        class_name = source_file.qualified_name
        if not class_name:
            return

        compiled = self._find_compiled_dir(source_file.path)
        if not compiled:
            return

        try:
            jimple_map = self._sootup.extract_class(
                class_name=class_name,
                classpath=str(compiled),
                existing_methods=methods,
            )
            if jimple_map:
                cnt = sum(1 for v in jimple_map.values() if v)
                print(f"  [SootUp] Merged Jimple for "
                      f"{cnt} methods in {class_name}")
        except Exception as e:
            print(f"  [WARN] SootUp merge failed for {class_name}: {e}")

    @staticmethod
    def _find_compiled_dir(source_path: Path) -> Optional[Path]:
        """Find the compiled classes directory for a source file."""
        for parent in [source_path] + list(source_path.parents):
            for c in [parent / "target" / "classes",
                      parent / "build" / "classes",
                      parent / "bin"]:
                if c.is_dir():
                    return c
            if parent.name == "src":
                for c in [parent.parent / "target" / "classes",
                          parent.parent / "build" / "classes"]:
                    if c.is_dir():
                        return c
        return None
