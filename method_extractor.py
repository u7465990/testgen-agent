"""Method extraction — uses javalang to parse Java files and extract MethodInfo."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

from javalang import parse
from javalang.tree import (
    CompilationUnit,
    MethodDeclaration,
    ConstructorDeclaration,
    FieldDeclaration,
    ClassDeclaration,
    InterfaceDeclaration,
)

from java_analyzer import SourceFile


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

    def __repr__(self) -> str:
        return f"MethodInfo({self.fqn})"


# ── Strings that are always allowed in generated tests ───────

ALWAYS_ALLOWED: Set[str] = {
    "org.junit.Test",
    "org.junit.Assert",
    "org.junit.Assert.*",
    "org.junit.Before",
    "org.junit.After",
    "org.junit.Ignore",
    "java.lang.reflect.Method",
    "java.lang.reflect.InvocationTargetException",
    "java.lang.reflect.*",
    "java.io.ByteArrayInputStream",
    "java.io.ByteArrayOutputStream",
    "java.io.ObjectInputStream",
    "java.io.ObjectOutputStream",
    "java.io.IOException",
}

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


# ── Extractor ─────────────────────────────────────────────────

class MethodExtractor:
    """Parses Java source files and extracts structured method information."""

    def __init__(self, project_name: str = ""):
        self.project_name = project_name

    # ── Public API ────────────────────────────────────────────

    def extract_methods(self, source_file: SourceFile) -> List[MethodInfo]:
        """Parse one source file and return all extractable methods."""
        try:
            source_text = source_file.path.read_text(encoding="utf-8")
        except Exception as e:
            print(f"  [WARN] Cannot read {source_file.path}: {e}")
            return []

        try:
            tree = parse.parse(source_text)
        except Exception as e:
            print(f"  [WARN] Failed to parse {source_file.path}: {e}")
            return []

        file_imports = self._collect_imports(tree)
        class_context = self._build_class_context(tree, source_text)

        methods: List[MethodInfo] = []
        for path, node in tree:
            if isinstance(node, (MethodDeclaration, ConstructorDeclaration)):
                mi = self._extract_one(
                    node, source_file, source_text, file_imports, class_context
                )
                if mi:
                    methods.append(mi)
        return methods

    # ── Single method extraction ──────────────────────────────

    def _extract_one(
        self,
        node: MethodDeclaration | ConstructorDeclaration,
        src_file: SourceFile,
        source_text: str,
        file_imports: List[str],
        class_context: str,
    ) -> Optional[MethodInfo]:
        is_constr = isinstance(node, ConstructorDeclaration)
        method_name = (
            node.name
            if not is_constr
            else src_file.path.stem
        )

        # Determine modifiers
        mods: List[str] = list(getattr(node, "modifiers", set()) or [])
        is_private = "private" in mods
        is_static = "static" in mods
        is_abstract = "abstract" in mods

        # Parameter info
        params = list(getattr(node, "parameters", []) or [])
        param_types: List[str] = []
        param_names: List[str] = []
        for p in params:
            pt = self._type_name(p.type)
            param_types.append(pt)
            param_names.append(p.name)

        # Return type
        if is_constr:
            return_type = ""
        else:
            rt = getattr(node, "return_type", None)
            return_type = self._type_name(rt) if rt else "void"

        # Throws
        throws: List[str] = []
        for t in getattr(node, "throws", []) or []:
            throws.append(self._type_name(t))

        # Source code (method body)
        source_code, body = self._extract_source_code(source_text, node)
        if not source_code:
            return None

        # FQN and signature
        pkg = src_file.package_name
        cls = src_file.path.stem
        fqn = f"{pkg}.{cls}.{method_name}({','.join(param_types)})" if pkg \
              else f"{cls}.{method_name}({','.join(param_types)})"
        sig = f"{return_type} {method_name}({', '.join(param_types)})"

        # Allowed imports
        allowed = self._compute_allowed_imports(file_imports, pkg, cls,
                                                 param_types, throws)

        # Branch conditions
        branches = self._extract_branch_conditions(body or source_code)

        return MethodInfo(
            project_name=self.project_name,
            source_file=str(src_file.path),
            class_name=cls,
            package_name=pkg,
            method_name=method_name,
            fqn=fqn,
            signature=sig,
            return_type=return_type,
            parameter_types=param_types,
            parameter_names=param_names,
            modifiers=mods,
            is_private=is_private,
            is_static=is_static,
            is_abstract=is_abstract,
            is_constructor=is_constr,
            throws_exceptions=throws,
            source_code=source_code,
            method_body=body or "",
            class_context=class_context,
            imports=file_imports,
            allowed_imports=allowed,
            branch_conditions=branches,
        )

    # ── Helpers ───────────────────────────────────────────────

    @staticmethod
    def _type_name(t) -> str:
        """Convert a javalang Type node to a readable Java type string."""
        from javalang.tree import BasicType, ReferenceType, TypeArgument

        if t is None:
            return "void"
        if isinstance(t, BasicType):
            name = t.name
            dims = getattr(t, "dimensions", None) or []
            name += "[]" * len(dims)
            return name
        if isinstance(t, ReferenceType):
            name = t.name
            if t.arguments:
                args = []
                for a in t.arguments:
                    if isinstance(a, TypeArgument):
                        if a.pattern_type == "?":
                            args.append("?")
                        elif a.type:
                            args.append(MethodExtractor._type_name(a.type))
                    elif a:
                        args.append(str(a))
                name += "<" + ", ".join(args) + ">"
            # Handle array dimensions stored at the type level
            dims = getattr(t, "dimensions", None) or []
            name += "[]" * len(dims)
            return name
        return str(t)

    @staticmethod
    def _collect_imports(tree: CompilationUnit) -> List[str]:
        """Extract all import statements from the AST."""
        imports = []
        for imp in tree.imports or []:
            imports.append(str(imp))
        return imports

    @staticmethod
    def _extract_source_code(text: str, node) -> Tuple[str, str]:
        """
        Extract the full method source and body from raw text.
        Tries javalang positions first; falls back to finding the method
        by scanning for its name and balancing braces.
        """
        start_pos = getattr(node, "start_position", None)
        end_pos = getattr(node, "end_position", None)

        if start_pos and end_pos:
            lines = text.splitlines(keepends=True)
            start_line = start_pos[0] - 1
            end_line = min(end_pos[0], len(lines))
            code = "".join(lines[start_line:end_line]).rstrip("\n")
            body_start = code.find("{")
            body = code[body_start:] if body_start >= 0 else ""
            return code, body

        # Fallback: find method by name in source and balance braces
        is_constr = isinstance(node, ConstructorDeclaration)
        search_name = node.name
        if not is_constr:
            # Try to find "methodName(" in text
            idx = text.find(search_name + "(")
            if idx < 0:
                idx = text.find(search_name)
        else:
            idx = text.find(search_name)

        if idx < 0:
            return "", ""

        # Scan backwards from idx to find the actual start of the method
        # (modifiers, annotations, return type, etc.)
        start = idx
        while start > 0:
            start -= 1
            ch = text[start]
            if ch == "\n" or ch == ";":
                # Previous line or statement → this is the start
                start = start + 1 if ch == "\n" else start + 1
                break
            if ch == "}":
                # We went too far back (inside previous block)
                start = idx
                break

        # Find opening brace
        brace = text.find("{", idx)
        if brace < 0:
            return "", ""

        # Balance braces
        depth = 0
        i = brace
        while i < len(text):
            if text[i] == "{":
                depth += 1
            elif text[i] == "}":
                depth -= 1
                if depth == 0:
                    code = text[start:i + 1].strip()
                    body = text[brace:i + 1]
                    return code, body
            i += 1

        return "", ""

    @staticmethod
    def _extract_branch_conditions(body: str) -> List[str]:
        """
        Extract control-flow conditions from method source.
        Returns a list of condition strings like:
          "if (var == null)"
          "while (i < len)"
        """
        if not body:
            return []
        conditions: List[str] = []
        # Ensure we're not inside a string literal (simplified)
        patterns = [
            r'if\s*\(([^)]*)\)',
            r'else\s+if\s*\(([^)]*)\)',
            r'while\s*\(([^)]*)\)',
            r'for\s*\(([^;]*);\s*([^;]+);',
            r'catch\s*\(([^)]*)\)',
        ]
        for pattern in patterns:
            for m in re.finditer(pattern, body, re.MULTILINE):
                cond = m.group(0).strip()
                if cond not in conditions:
                    conditions.append(cond)
        return conditions

    @staticmethod
    def _build_class_context(tree: CompilationUnit, source_text: str) -> str:
        """
        Build a summary of the class: fields, constructors, and their types.
        Mirrors the classContext logic from Task1Extractor.
        """
        parts: List[str] = []

        for path, node in tree:
            if isinstance(node, FieldDeclaration):
                for decl in node.declarators:
                    type_name = MethodExtractor._type_name(node.type)
                    parts.append(f"  {type_name} {decl.name};")
            elif isinstance(node, ConstructorDeclaration):
                params = ", ".join(
                    MethodExtractor._type_name(p.type) + " " + p.name
                    for p in (node.parameters or [])
                )
                parts.append(f"  {node.name}({params});")

        if not parts:
            return ""
        return "class context:\n" + "\n".join(parts)

    @staticmethod
    def _compute_allowed_imports(
        file_imports: List[str],
        package_name: str,
        class_name: str,
        param_types: List[str],
        throws: List[str],
    ) -> List[str]:
        """
        Compute the allowed-import whitelist for generated tests.
        Replicates the logic from Task1Extractor/java.
        """
        allowed: List[str] = []

        # Always allowed
        for imp in sorted(ALWAYS_ALLOWED):
            allowed.append(imp)

        # The class under test itself (always allowed)
        if package_name:
            allowed.append(f"{package_name}.{class_name}")
            allowed.append(f"{package_name}.{class_name}.*")

        # Types used in parameters and throws
        used_types: Set[str] = set()
        for pt in param_types:
            used_types.add(pt)
        for ex in throws:
            used_types.add(ex)

        for ut in used_types:
            # Fully-qualified types already contain a dot
            if "." in ut and not ut.startswith("java.lang."):
                allowed.append(ut)

        # Also allow imports from the file that are java/javax based
        for imp in file_imports:
            imp_clean = imp.replace("import ", "").replace(";", "").strip()
            if imp_clean.startswith(("java.", "javax.", "org.junit.")):
                if imp_clean not in allowed:
                    allowed.append(imp_clean)

        return sorted(set(allowed))
