"""JaCoCo coverage analysis — parse jacoco.xml for per-method branch/line data."""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional


@dataclass
class MethodCoverage:
    """Coverage data for a single method."""
    method_name: str
    method_desc: str                   # JVM descriptor, e.g. (Ljava/lang/String;)I
    fqn: str                           # human-readable, e.g. org.example.Cls.meth(int)
    missed_branches: int = 0
    covered_branches: int = 0
    missed_lines: int = 0
    covered_lines: int = 0
    total_branches: int = 0
    branch_ratio: float = 0.0
    line_ratio: float = 0.0


_JVM_TYPE_MAP: dict = {
    "V": "void", "Z": "boolean", "B": "byte", "C": "char",
    "S": "short", "I": "int", "J": "long", "F": "float", "D": "double",
}


class CoverageAnalyzer:
    """Parse JaCoCo XML reports and extract per-method coverage information."""

    @staticmethod
    def find_jacoco_xml(project_path: Path) -> Optional[Path]:
        """Locate the JaCoCo XML report in a project."""
        candidates = [
            project_path / "target/site/jacoco/jacoco.xml",
            project_path / "build/reports/jacoco/test/jacoco.xml",
            project_path / "target/site/jacoco-aggregate/jacoco.xml",
        ]
        for c in candidates:
            if c.is_file():
                return c
        return None

    @staticmethod
    def run_tests_with_coverage(project_path: Path) -> bool:
        """Run 'mvn clean test jacoco:report' for the project.

        Returns True if the process completed (even if some tests fail).
        """
        import subprocess
        import sys

        cmd = "mvn clean test jacoco:report -Dmaven.test.failure.ignore=true -B -q"
        print(f"    [CMD] cd {project_path} && {cmd}")
        try:
            result = subprocess.run(
                cmd, cwd=str(project_path),
                capture_output=True, text=True,
                timeout=300, shell=True,
            )
            if result.returncode != 0:
                print(f"    [WARN] Maven returned exit code {result.returncode}")
            else:
                print("    [OK] Tests executed successfully")
            return True
        except subprocess.TimeoutExpired:
            print("    [FAIL] Maven test execution timed out")
            return False
        except FileNotFoundError:
            print("    [FAIL] Maven (mvn) not found in PATH")
            return False

    @staticmethod
    def parse_jacoco_xml(
        jacoco_xml: Path,
        target_classes: Optional[List[str]] = None,
    ) -> Dict[str, MethodCoverage]:
        """Parse jacoco.xml and return per-method coverage keyed by FQN.

        Args:
            jacoco_xml: Path to jacoco.xml
            target_classes: Optional list of class names (slash-separated,
                           e.g. 'org/apache/commons/codec/binary/StringUtils')
                           to filter. If None, returns all methods.

        Returns:
            Dict mapping human-readable method FEN → MethodCoverage
        """
        if not jacoco_xml.is_file():
            print(f"    [WARN] JaCoCo XML not found: {jacoco_xml}")
            return {}

        try:
            tree = ET.parse(str(jacoco_xml))
            root = tree.getroot()
        except ET.ParseError as e:
            print(f"    [ERROR] Failed to parse jacoco.xml: {e}")
            return {}

        results: Dict[str, MethodCoverage] = {}

        for pkg in root.findall(".//package"):
            for cls in pkg.findall("class"):
                class_name = cls.get("name", "")
                if target_classes:
                    if class_name not in target_classes:
                        continue

                for method in cls.findall("method"):
                    m_name = method.get("name", "")
                    m_desc = method.get("desc", "")

                    counters = {}
                    for c in method.findall("counter"):
                        ctype = c.get("type", "")
                        counters[ctype] = c

                    missed_b = int(counters.get("BRANCH", {}).get("missed", 0))
                    covered_b = int(counters.get("BRANCH", {}).get("covered", 0))
                    missed_l = int(counters.get("LINE", {}).get("missed", 0))
                    covered_l = int(counters.get("LINE", {}).get("covered", 0))
                    total_b = missed_b + covered_b
                    total_l = missed_l + covered_l

                    fqn = CoverageAnalyzer._method_fen(
                        class_name, m_name, m_desc
                    )

                    results[fqn] = MethodCoverage(
                        method_name=m_name,
                        method_desc=m_desc,
                        fqn=fqn,
                        missed_branches=missed_b,
                        covered_branches=covered_b,
                        missed_lines=missed_l,
                        covered_lines=covered_l,
                        total_branches=total_b,
                        branch_ratio=covered_b / total_b if total_b > 0 else 1.0,
                        line_ratio=covered_l / total_l if total_l > 0 else 1.0,
                    )

        return results

    @staticmethod
    def _method_fen(class_name: str, method_name: str, desc: str) -> str:
        """Build a human-readable method FEN from JaCoCo attributes.

        E.g. org/apache/.../StringUtils.equals(Ljava/lang/CharSequence;)I
             → org.apache.commons.codec.binary.StringUtils.equals(CharSequence)
        """
        dot_class = class_name.replace("/", ".")
        sig = CoverageAnalyzer._parse_jvm_desc(desc)
        param_block = sig.split(" → ")[0] if " → " in sig else sig
        raw_params = param_block.strip("()").split(",")
        simple_params = []
        for p in raw_params:
            p = p.strip()
            if not p:
                continue
            array_suffix = ""
            while p.endswith("[]"):
                array_suffix += "[]"
                p = p[:-2]
            simple_part = p.split(".")[-1]
            if "$" in simple_part:
                simple_part = simple_part.split("$")[-1]
            simple_params.append(simple_part + array_suffix)
        return f"{dot_class}.{method_name}({','.join(simple_params)})"

    @staticmethod
    def _parse_jvm_desc(desc: str) -> str:
        """Convert a JVM type descriptor to a human-readable signature.

        (Ljava/lang/String;I)Z → (String, int) → boolean
        """
        match = re.match(r"\((.*?)\)(.*)", desc)
        if not match:
            return desc
        param_part, return_part = match.groups()

        params = []
        i = 0
        while i < len(param_part):
            array_dim = 0
            while i < len(param_part) and param_part[i] == "[":
                array_dim += 1
                i += 1
            if i >= len(param_part):
                break
            ch = param_part[i]
            if ch in _JVM_TYPE_MAP:
                java_type = _JVM_TYPE_MAP[ch]
                i += 1
            elif ch == "L":
                end = param_part.index(";", i) + 1
                java_type = param_part[i + 1:end - 1].replace("/", ".")
                i = end
            else:
                java_type = ch
                i += 1
            params.append(java_type + "[]" * array_dim)

        # Parse return type
        rt = return_part
        array_dim = 0
        while rt.startswith("["):
            array_dim += 1
            rt = rt[1:]
        if rt in _JVM_TYPE_MAP:
            return_type = _JVM_TYPE_MAP[rt]
        elif rt.startswith("L") and rt.endswith(";"):
            return_type = rt[1:-1].replace("/", ".")
        else:
            return_type = rt
        if array_dim:
            return_type += "[]" * array_dim

        return f"({', '.join(params)}) → {return_type}"
