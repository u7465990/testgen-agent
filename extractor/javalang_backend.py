"""javalang-based extraction backend — pure Python, fast, no JVM needed."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

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
from method_extractor import (
    Collaborator,
    ConstructorInfo,
    FieldInfo,
    MethodInfo,
    always_allowed,
    mockito_allowed,
)
from target_profile import TargetProfile


@dataclass
class _ClassShape:
    """One type's fields and constructors, structured, before rendering."""

    name: str
    is_interface: bool = False
    is_abstract: bool = False
    fields: List[FieldInfo] = field(default_factory=list)
    constructors: List[ConstructorInfo] = field(default_factory=list)

    @property
    def is_mockable_kind(self) -> bool:
        """Interfaces and abstract classes are the mockable shape."""
        return self.is_interface or self.is_abstract


class JavalangBackend(ExtractorBackend):
    """Pure-Python extraction using javalang AST parser."""

    def __init__(
        self, project_name: str = "", profile: Optional[TargetProfile] = None
    ):
        self._project_name = project_name
        # Shared, populated in place during Phase 1; read at extract time so a
        # backend built before detection still picks up the detected version.
        self._profile = profile or TargetProfile()
        # Set by the agent once it has discovered the project's source files;
        # without it no collaborator type name can be resolved to real source.
        self._source_index = None

    def set_source_index(self, source_index) -> None:
        self._source_index = source_index

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
        shapes = self._collect_class_shapes(tree)

        methods: List[MethodInfo] = []
        for path, node in tree:
            if isinstance(node, (MethodDeclaration, ConstructorDeclaration)):
                shape = shapes.get(JavalangBackend._owning_type_name(path) or "")
                mi = self._extract_one(
                    node, source_file, source_text, file_imports,
                    self._render_class_context(shape), shape,
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
        shape: Optional["_ClassShape"] = None,
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
            file_imports, pkg, cls, param_types, throws,
            self._profile.junit_version, self._profile.mockito_available,
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
            fields=list(shape.fields) if shape else [],
            constructors=list(shape.constructors) if shape else [],
            collaborators=self._resolve_collaborators(shape, pkg, file_imports),
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
    def _owning_type_name(path) -> Optional[str]:
        """The innermost class/interface a node at `path` belongs to."""
        owner = next(
            (n for n in reversed(path)
             if isinstance(n, (ClassDeclaration, InterfaceDeclaration))),
            None,
        )
        return owner.name if owner is not None else None

    @staticmethod
    def _collect_class_shapes(
        tree: CompilationUnit,
    ) -> Dict[str, "_ClassShape"]:
        """Group each type's fields and constructors under its own name.

        The previous implementation walked the whole tree and appended every
        field and constructor into one flat list, so a file holding two classes
        gave each of them the other's members with no way to tell them apart.
        Ownership is recoverable from the parse `path`, so attribute properly
        here — this is what lets mock generation ask "what does *this* class
        take as dependencies".

        Order within a class is the source traversal order, deliberately: the
        rendered prompt string has to stay identical for single-class files.
        """
        shapes: Dict[str, "_ClassShape"] = {}
        for path, node in tree:
            if not isinstance(
                node, (FieldDeclaration, ConstructorDeclaration)
            ):
                continue
            owner_name = JavalangBackend._owning_type_name(path)
            if not owner_name:
                continue
            if owner_name not in shapes:
                owner = next(
                    (n for n in reversed(path)
                     if isinstance(n, (ClassDeclaration, InterfaceDeclaration))),
                    None,
                )
                shapes[owner_name] = _ClassShape(
                    name=owner_name,
                    is_interface=isinstance(owner, InterfaceDeclaration),
                    is_abstract="abstract" in (
                        getattr(owner, "modifiers", None) or set()
                    ),
                )
            shape = shapes[owner_name]

            if isinstance(node, FieldDeclaration):
                type_name = JavalangBackend._type_name(node.type)
                for decl in node.declarators:
                    shape.fields.append(FieldInfo(
                        type_name=type_name,
                        name=decl.name,
                        modifiers=sorted(getattr(node, "modifiers", None) or []),
                    ))
            else:
                shape.constructors.append(ConstructorInfo(
                    name=node.name,
                    parameter_types=[
                        JavalangBackend._type_name(p.type)
                        for p in (node.parameters or [])
                    ],
                    parameter_names=[
                        p.name for p in (node.parameters or [])
                    ],
                    modifiers=sorted(
                        getattr(node, "modifiers", None) or []
                    ),
                ))
        return shapes

    @staticmethod
    def _render_class_context(shape: Optional["_ClassShape"]) -> str:
        """Render a class shape into the prompt's `class context:` string.

        Kept byte-identical to the original for single-class files: same
        header, same two-space indent, same field-then-constructor order, same
        omission of modifiers.
        """
        if shape is None:
            return ""
        parts: List[str] = []
        for f in shape.fields:
            parts.append(f"  {f.type_name} {f.name};")
        for c in shape.constructors:
            params = ", ".join(
                f"{t} {n}"
                for t, n in zip(c.parameter_types, c.parameter_names)
            )
            parts.append(f"  {c.name}({params});")
        if not parts:
            return ""
        return "class context:\n" + "\n".join(parts)

    def _resolve_collaborators(
        self,
        shape: Optional["_ClassShape"],
        package_name: str,
        file_imports: List[str],
    ) -> List[Collaborator]:
        """Injected dependencies of the class under test, ready to mock.

        Empty unless a SourceIndex has been attached (see
        collaborator_resolver.py) — without project sources there is nothing to
        resolve a type name against, and guessing would produce mock targets
        that cannot compile.
        """
        if shape is None or self._source_index is None:
            return []
        return self._source_index.find_collaborators(
            shape, package_name, file_imports
        )

    @staticmethod
    def _compute_allowed_imports(
        file_imports: List[str],
        package_name: str,
        class_name: str,
        param_types: List[str],
        throws: List[str],
        junit_version: int = 4,
        mockito_available: bool = False,
    ) -> List[str]:
        allowed: List[str] = []
        for imp in sorted(always_allowed(junit_version)):
            allowed.append(imp)
        # Gated on availability, not on whether the class has collaborators:
        # an unresolvable import is worse than a missing one.
        if mockito_available:
            for imp in sorted(mockito_allowed(junit_version)):
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
            if not imp_clean.startswith(("java.", "javax.", "org.junit.")):
                continue
            # Do not carry the *other* JUnit's imports across. A project
            # mid-migration has both on disk, and an allowed-list entry for
            # org.junit.Assert would invite the LLM to write JUnit 4 assertions
            # into a JUnit 5 test (and vice versa for a forced --junit 4).
            if imp_clean.startswith("org.junit."):
                is_jupiter = imp_clean.startswith("org.junit.jupiter.")
                if (junit_version == 5) != is_jupiter:
                    continue
            if imp_clean not in allowed:
                allowed.append(imp_clean)
        return sorted(set(allowed))
