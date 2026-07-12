"""Test code formatting, class naming, and file I/O."""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import List

from method_extractor import MethodInfo


class TestWriter:
    """Formats LLM-generated test code and writes it to disk."""

    def __init__(self, test_directory: Path):
        self.test_directory = test_directory

    # ── Type abbreviation map ─────────────────────────────────

    _TYPE_ABBREV: dict = {
        "String": "Str",
        "int": "int",
        "long": "Lng",
        "double": "Dbl",
        "float": "Flt",
        "boolean": "Bool",
        "byte": "Byte",
        "short": "Short",
        "char": "Char",
        "void": "Void",
        "Object": "Obj",
        "Integer": "Int",
        "CharSequence": "CSq",
        "Charset": "CSet",
        "ZipEncoding": "ZipEnc",
        "ByteBuffer": "BBuf",
        "InputStream": "InStr",
        "OutputStream": "OutStr",
        "ObjectInputStream": "OInStr",
        "ObjectOutputStream": "OOutStr",
    }

    # ── Class naming ──────────────────────────────────────────

    @staticmethod
    def _short_type(t: str) -> str:
        """Shorten a Java type name for inclusion in a class name."""
        base = t.strip()
        is_arr = base.endswith("[]")
        core = base[:-2] if is_arr else base
        # Strip package
        if "." in core:
            core = core.rsplit(".", 1)[-1]
        abbr = TestWriter._TYPE_ABBREV.get(core, core)
        if is_arr:
            abbr += "Arr"
        return abbr

    @staticmethod
    def generate_class_name(
        method: MethodInfo, target: str, index: int
    ) -> str:
        """Generate a unique, deterministic test class name.

        Includes parameter-type abbreviations so overloaded methods
        with different parameter lists produce distinct class names.
        """
        fqn_no_params = method.fqn.split("(")[0]
        parts = fqn_no_params.split(".")
        cls = parts[-2] if len(parts) >= 2 else method.class_name
        mname = parts[-1]

        # Parameter-type suffix (e.g. _Str_int for (String, int))
        param_suffix = ""
        for pt in method.parameter_types:
            param_suffix += "_" + TestWriter._short_type(pt)

        target_label = "General"
        tl = target.lower()
        if "normal" in tl:
            target_label = "Normal"
        elif "boundary" in tl:
            target_label = "Boundary"
        elif "exception" in tl:
            target_label = "Exception"
        elif "path" in tl:
            target_label = "Path"
        elif "reflection" in tl:
            target_label = "Reflection"
        elif "missingbranch" in tl:
            target_label = "MissingBranch"

        safe_m = mname.replace("<", "_").replace(">", "_")
        safe_c = cls.replace("<", "_").replace(">", "_")
        return f"{safe_c}_{safe_m}{param_suffix}_Test_{target_label}_{index}"

    # ── Package from FQN ──────────────────────────────────────

    @staticmethod
    def get_package(method: MethodInfo) -> str:
        """Derive the test package from the method's FQN."""
        if method.package_name:
            return method.package_name
        fqn_no_params = method.fqn.split("(")[0]
        parts = fqn_no_params.split(".")
        if len(parts) >= 2:
            return ".".join(parts[:-1])
        return ""

    # ── Code formatting ───────────────────────────────────────

    @staticmethod
    def format_code(
        raw_response: str, class_name: str, package_name: str
    ) -> str:
        """
        Clean and format LLM output into compilable Java.
        Mirrors the logic in generate_test.py::format_test_code.
        """
        # Extract code from markdown fences
        code_blocks = re.findall(
            r"```(?:\w+)?\s*\n(.*?)\n```", raw_response, re.DOTALL
        )
        java_code = "\n".join(code_blocks) if code_blocks else raw_response

        # Collect and deduplicate imports (order-preserving)
        imports: List[str] = re.findall(
            r"^import\s+(?:static\s+)?[\w.*]+;", java_code, re.MULTILINE
        )
        seen: set = set()
        unique_imports: List[str] = []
        for imp in imports:
            if imp not in seen:
                seen.add(imp)
                unique_imports.append(imp)

        # Strip existing package and imports
        java_code = re.sub(
            r"^package\s+.+;", "", java_code, flags=re.MULTILINE
        )
        java_code = re.sub(
            r"^import\s+.+;", "", java_code, flags=re.MULTILINE
        )

        # Find class body
        class_match = re.search(
            r"(?:public\s+)?class\s+(\w+)\s*\{([\s\S]*)\}", java_code
        )
        if class_match:
            orig_name = class_match.group(1)
            body = class_match.group(2)
        else:
            orig_name = "TemporaryClass"
            body = java_code

        # Rename class if needed
        if orig_name != class_name:
            body = body.replace(orig_name, class_name)

        # Reassemble
        header = f"package {package_name};\n\n" if package_name else ""
        formatted = (
            header
            + "\n".join(unique_imports)
            + f"\n\npublic class {class_name} {{\n"
            + body
            + "\n}\n"
        )
        return formatted

    # ── File I/O ──────────────────────────────────────────────

    def write_test_file(
        self, formatted_code: str, package_name: str, class_name: str
    ) -> Path:
        """Write formatted test code to disk. Returns the relative path."""
        package_path = package_name.replace(".", "/") if package_name else ""
        test_dir = self.test_directory
        if package_path:
            test_dir = test_dir / package_path
        test_dir.mkdir(parents=True, exist_ok=True)

        file_path = test_dir / f"{class_name}.java"
        file_path.write_text(formatted_code, encoding="utf-8")
        return file_path
