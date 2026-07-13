"""javalang-based extraction backend — pure Python, fast, no JVM needed."""

from __future__ import annotations

import re
from pathlib import Path
from typing import List, Optional, Set, Tuple

from javalang import parse
from javalang.tree import (
    BasicType,
    ClassDeclaration,
    CompilationUnit,
    ConstructorDeclaration,
    FieldDeclaration,
    InterfaceDeclaration,
    MethodDeclaration,
    ReferenceType,
    TypeArgument,
)

from extractor.base import ExtractorBackend
from java_analyzer import SourceFile
from method_extractor import ALWAYS_ALLOWED, MethodInfo


class JavalangBackend(ExtractorBackend):
    """Pure-Python extraction using javalang AST parser."""

    def __init__(self, project_name: str = ""):
        self._project_name = project_name

    @property
    def name(self) -> str:
        return "javalang"

    @property
    def provides_jimple(self) -> bool:
        return False

    # ── Public API ────────────────────────────────────────────

    def extract(self, source_file: SourceFile) -> List[MethodInfo]:
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

        mods: List[str] = list(getattr(node, "modifiers", set()) or [])
        is_private = "private" in mods
        is_static = "static" in mods
        is_abstract = "abstract" in mods

        params = list(getattr(node, "parameters", []) or [])
        param_types: List[str] = []
        param_names: List[str] = []
        for p in params:
            pt = self._type_name(p.type)
            param_types.append(pt)
            param_names.append(p.name)

        if is_constr:
            return_type = ""
        else:
            rt = getattr(node, "return_type", None)
            return_type = self._type_name(rt) if rt else "void"

        throws: List[str] = []
        for t in getattr(node, "throws", []) or []:
            throws.append(self._type_name(t))

        source_code, body = self._extract_source_code(source_text, node)
        if not source_code:
            return None

        pkg = src_file.package_name
        cls = src_file.path.stem
        fqn = f"{pkg}.{cls}.{method_name}({','.join(param_types)})" if pkg \
              else f"{cls}.{method_name}({','.join(param_types)})"
        sig = f"{return_type} {method_name}({', '.join(param_types)})"

        allowed = self._compute_allowed_imports(
            file_imports, pkg, cls, param_types, throws
        )
        branches = self._extract_branch_conditions(body or source_code)

        return MethodInfo(
            project_name=self._project_name,
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
            jimple_code="",  # javalang doesn't produce Jimple
        )

    # ── Static helpers ────────────────────────────────────────

    @staticmethod
    def _type_name(t) -> str:
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
                            args.append(JavalangBackend._type_name(a.type))
                    elif a:
                        args.append(str(a))
                name += "<" + ", ".join(args) + ">"
            dims = getattr(t, "dimensions", None) or []
            name += "[]" * len(dims)
            return name
        return str(t)

    @staticmethod
    def _collect_imports(tree: CompilationUnit) -> List[str]:
        imports = []
        for imp in tree.imports or []:
            imports.append(str(imp))
        return imports

    @staticmethod
    def _extract_source_code(text: str, node) -> Tuple[str, str]:
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

        # Fallback: find method by name and balance braces
        is_constr = isinstance(node, ConstructorDeclaration)
        search_name = node.name
        if not is_constr:
            idx = text.find(search_name + "(")
            if idx < 0:
                idx = text.find(search_name)
        else:
            idx = text.find(search_name)

        if idx < 0:
            return "", ""

        start = idx
        while start > 0:
            start -= 1
            ch = text[start]
            if ch == "\n" or ch == ";":
                start = start + 1 if ch == "\n" else start + 1
                break
            if ch == "}":
                start = idx
                break

        brace = text.find("{", idx)
        if brace < 0:
            return "", ""

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
        if not body:
            return []
        conditions: List[str] = []
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
        parts: List[str] = []
        for path, node in tree:
            if isinstance(node, FieldDeclaration):
                for decl in node.declarators:
                    type_name = JavalangBackend._type_name(node.type)
                    parts.append(f"  {type_name} {decl.name};")
            elif isinstance(node, ConstructorDeclaration):
                params = ", ".join(
                    JavalangBackend._type_name(p.type) + " " + p.name
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
        allowed: List[str] = []
        for imp in sorted(ALWAYS_ALLOWED):
            allowed.append(imp)
        if package_name:
            allowed.append(f"{package_name}.{class_name}")
            allowed.append(f"{package_name}.{class_name}.*")
        used_types: Set[str] = set()
        for pt in param_types:
            used_types.add(pt)
        for ex in throws:
            used_types.add(ex)
        for ut in used_types:
            if "." in ut and not ut.startswith("java.lang."):
                allowed.append(ut)
        for imp in file_imports:
            imp_clean = imp.replace("import ", "").replace(";", "").strip()
            if imp_clean.startswith(("java.", "javax.", "org.junit.")):
                if imp_clean not in allowed:
                    allowed.append(imp_clean)
        return sorted(set(allowed))
