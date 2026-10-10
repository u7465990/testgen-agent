"""Resolve a class's injected dependencies to project source, so they can be mocked.

Why this module exists at all: `class_context` carries a collaborator's *type
name* as text, but writing a usable Mockito test needs more than the name —
`when(gateway.charge(...)).thenReturn(true)` is only possible if the LLM knows
`PaymentGateway.charge(String, double)` exists and returns a boolean. So a type
name has to be resolved to its source file, parsed, and reduced to its public
signatures before it goes into a prompt.

The bar for calling something a collaborator is deliberately high: it must
resolve to *project source* and be an interface or abstract class. That is not
just precision for its own sake — it is what keeps the feature a no-op on
projects with nothing to mock. A type that cannot be resolved is never a
collaborator, and no JDK type or value object ever resolves, so a class whose
only constructor parameters are `String` and `double` yields no mock targets and
generates exactly the same tests it did before.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Set

from javalang import parse
from javalang.tree import (
    ClassDeclaration,
    InterfaceDeclaration,
    MethodDeclaration,
)

from extractor.javalang_backend import JavalangBackend, _ClassShape
from java_analyzer import SourceFile
from method_extractor import Collaborator


# ── Type classification ───────────────────────────────────────

_PRIMITIVES: Set[str] = {
    "void", "boolean", "byte", "char", "short", "int", "long", "float",
    "double",
}

# Bare names that are never collaborators, however they are spelled. Anything
# not here that still fails to resolve to project source is also rejected, so
# this set only has to cover the common cases — it is a fast path, not the
# safety net.
_JDK_VALUE_NAMES: Set[str] = {
    "String", "Object", "Integer", "Long", "Double", "Float", "Boolean",
    "Byte", "Character", "Short", "Number", "BigInteger", "BigDecimal",
    "CharSequence", "StringBuilder", "StringBuffer", "Class", "Thread",
    "Enum", "UUID", "Locale", "Currency",
    "List", "Set", "Map", "Collection", "Iterable", "Iterator", "Comparator",
    "ArrayList", "LinkedList", "HashMap", "LinkedHashMap", "HashSet",
    "TreeMap", "TreeSet", "Queue", "Deque", "ArrayDeque", "Optional",
    "Stream", "Collector", "Function", "Supplier", "Consumer", "Predicate",
    "LocalDate", "LocalTime", "LocalDateTime", "Instant", "Duration",
    "Period", "ZoneId", "ZonedDateTime", "Date", "Calendar", "TimeZone",
    "Path", "File", "URI", "URL", "Pattern", "Matcher", "Random",
    "Exception", "RuntimeException", "Throwable", "Error",
    "AtomicInteger", "AtomicLong", "AtomicBoolean",
}

_JDK_PACKAGE_PREFIXES = (
    "java.", "javax.", "jakarta.", "sun.", "com.sun.", "jdk.",
)

_MAX_SIGNATURES_PER_TYPE = 12


def _core_name(type_text: str) -> Optional[str]:
    """Reduce a written type to its outer name: `List<Order>[]` -> `List`.

    Generic *arguments* are dropped rather than recursed into: injecting a
    `List` is what the constructor takes, and `Order` is not a dependency of
    the class just because it appears between the angle brackets.
    """
    text = (type_text or "").strip()
    while text.endswith("[]"):
        text = text[:-2].strip()
    text = text.replace("...", "").strip()
    if "<" in text:
        text = text.split("<", 1)[0].strip()
    text = text.lstrip("?").strip()
    text = text.replace("final ", "").strip()
    return text or None


def is_jdk_type(type_text: str) -> bool:
    """True for primitives and JDK value types — never mock candidates."""
    core = _core_name(type_text)
    if not core:
        return True
    simple = core.rsplit(".", 1)[-1]
    return simple in _PRIMITIVES or simple in _JDK_VALUE_NAMES


def _fully_qualified_is_jdk(core: str) -> bool:
    if "." not in core:
        return False
    return core.rsplit(".", 1)[0].startswith(_JDK_PACKAGE_PREFIXES)


# ── Resolved collaborators ────────────────────────────────────

@dataclass
class ResolvedType:
    """A project type a collaborator name resolved to."""

    simple_name: str
    fqn: str
    source_path: Path
    kind: str                                    # interface | abstract-class | class
    method_signatures: List[str] = field(default_factory=list)

    @property
    def is_mockable(self) -> bool:
        return self.kind in ("interface", "abstract-class")


class SourceIndex:
    """Look up project types by name and read their public signatures.

    Built once per run from the already-discovered source files. Parsing is
    cached per path, including negative results, so a type shared by many
    classes is read at most once.
    """

    def __init__(self, sources: Sequence[SourceFile]):
        self._by_fqn: Dict[str, SourceFile] = {}
        self._by_simple: Dict[str, List[SourceFile]] = {}
        for src in sources:
            fqn = src.qualified_name
            if fqn:
                self._by_fqn[fqn] = src
            stem = src.path.stem
            self._by_simple.setdefault(stem, []).append(src)
        self._shape_cache: Dict[Path, Dict[str, ResolvedType]] = {}

    # ── Resolution ────────────────────────────────────────────

    def resolve(
        self,
        type_text: str,
        owner_package: str,
        owner_imports: Sequence[str],
    ) -> Optional[ResolvedType]:
        """Resolve a written type name to project source, or None.

        Order: an explicit single-type import, then the owner's own package,
        then a wildcard import, then a unique project-wide match by simple
        name. Ambiguity or absence resolves to None — a wrong guess here would
        produce a mock that cannot compile.
        """
        core = _core_name(type_text)
        if not core or is_jdk_type(core):
            return None

        if "." in core:  # written fully-qualified in the source
            if _fully_qualified_is_jdk(core):
                return None
            src = self._by_fqn.get(core)
            return self._shape_for(src, core.rsplit(".", 1)[-1]) if src else None

        imports = [i.replace("import ", "").replace("static ", "")
                   .replace(";", "").strip() for i in (owner_imports or [])]

        # 1. explicit single-type import
        for imp in imports:
            if imp.endswith(".*"):
                continue
            if imp.rsplit(".", 1)[-1] == core:
                src = self._by_fqn.get(imp)
                if src is not None:
                    return self._shape_for(src, core)

        # 2. same package (no import needed)
        if owner_package:
            src = self._by_fqn.get(f"{owner_package}.{core}")
            if src is not None:
                return self._shape_for(src, core)

        # 3. wildcard import
        for imp in imports:
            if imp.endswith(".*"):
                src = self._by_fqn.get(f"{imp[:-2]}.{core}")
                if src is not None:
                    return self._shape_for(src, core)

        # 4. unique match anywhere in the project
        candidates = self._by_simple.get(core, [])
        if len(candidates) == 1:
            return self._shape_for(candidates[0], core)

        return None

    def _shape_for(
        self, src: SourceFile, wanted_name: str
    ) -> Optional[ResolvedType]:
        """Parse a source file (cached) and pull out one type's shape."""
        parsed = self._shape_cache.get(src.path)
        if parsed is None:
            parsed = self._parse_types(src)
            self._shape_cache[src.path] = parsed
        return parsed.get(wanted_name)

    @staticmethod
    def _parse_types(src: SourceFile) -> Dict[str, ResolvedType]:
        """All types declared in one file, keyed by their declared name.

        Never raises: an unparseable collaborator file degrades to "not
        resolvable", which surfaces as "no mock target" rather than a crash.
        """
        types: Dict[str, ResolvedType] = {}
        try:
            tree = parse.parse(src.path.read_text(encoding="utf-8"))
        except Exception:
            return types

        for path, node in tree:
            if not isinstance(node, (ClassDeclaration, InterfaceDeclaration)):
                continue
            # Skip nested/inner types: they cannot be injected by simple name
            # without qualification. `path` is the ancestor chain *excluding*
            # this node, so any type in it means this declaration is nested.
            if any(isinstance(n, (ClassDeclaration, InterfaceDeclaration))
                   for n in path):
                continue
            is_interface = isinstance(node, InterfaceDeclaration)
            is_abstract = "abstract" in (getattr(node, "modifiers", None) or set())
            kind = ("interface" if is_interface
                    else "abstract-class" if is_abstract else "class")
            types[node.name] = ResolvedType(
                simple_name=node.name,
                fqn=src.qualified_name or node.name,
                source_path=src.path,
                kind=kind,
                method_signatures=SourceIndex._public_signatures(node, is_interface),
            )
        return types

    @staticmethod
    def _public_signatures(node, is_interface: bool) -> List[str]:
        """Signatures of the methods a caller can actually reach.

        Interface methods carry no modifier but are implicitly public, so they
        are kept; constructors, private and `static` helpers are not — a mock
        cannot be stubbed on them.
        """
        signatures: List[str] = []
        # `node.methods` rather than `node.filter(MethodDeclaration)`: filter()
        # walks descendants, so an abstract class with a nested helper type
        # would advertise that type's methods as its own API.
        for child in (node.methods or []):
            modifiers = getattr(child, "modifiers", None) or set()
            if "private" in modifiers:
                continue
            if not is_interface and "public" not in modifiers:
                continue
            if not is_interface and "static" in modifiers:
                continue
            return_type = JavalangBackend._type_name(child.return_type) \
                if child.return_type else "void"
            params = ", ".join(
                JavalangBackend._type_name(p.type) for p in (child.parameters or [])
            )
            signatures.append(f"{return_type} {child.name}({params})")
            if len(signatures) >= _MAX_SIGNATURES_PER_TYPE:
                break
        return signatures

    # ── Collaborator detection ────────────────────────────────

    def find_collaborators(
        self,
        shape: _ClassShape,
        package_name: str,
        file_imports: Sequence[str],
    ) -> List[Collaborator]:
        """The mockable injected dependencies of one class.

        Returns [] unless the whole constructor is satisfiable — see
        `_constructor_is_satisfiable`. Mocking one of two dependencies and
        inventing the other is exactly the failure mode this guards against.
        """
        constructor_types = [
            t for c in shape.constructors for t in c.parameter_types
        ]
        field_types = [f.type_name for f in shape.fields]

        resolved: Dict[str, ResolvedType] = {}
        for type_text in constructor_types + field_types:
            if is_jdk_type(type_text):
                continue
            r = self.resolve(type_text, package_name, file_imports)
            if r is not None and r.is_mockable:
                resolved[r.fqn] = r

        if not resolved:
            return []

        # Every constructor parameter must be something the test can supply:
        # a JDK value type (a literal the LLM writes) or a mockable
        # collaborator. If some other type is in the way, the class cannot be
        # instantiated and a mock skeleton would be a lie.
        if shape.constructors:
            if not self._constructor_is_satisfiable(
                shape, resolved, package_name, file_imports
            ):
                return []

        constructor_fqns: Set[str] = set()
        for type_text in constructor_types:
            r = self.resolve(type_text, package_name, file_imports)
            if r is not None and r.is_mockable:
                constructor_fqns.add(r.fqn)

        collaborators: List[Collaborator] = []
        for fqn, r in sorted(resolved.items()):
            collaborators.append(Collaborator(
                type_name=r.simple_name,
                fqn=fqn,
                kind=r.kind,
                injection=("constructor" if fqn in constructor_fqns
                           else "field"),
                source_path=str(r.source_path),
                method_signatures=list(r.method_signatures),
            ))
        return collaborators

    def _constructor_is_satisfiable(
        self,
        shape: _ClassShape,
        resolved: Dict[str, ResolvedType],
        package_name: str,
        file_imports: Sequence[str],
    ) -> bool:
        for constructor in shape.constructors:
            for type_text in constructor.parameter_types:
                if is_jdk_type(type_text):
                    continue
                r = self.resolve(type_text, package_name, file_imports)
                if r is None or not r.is_mockable:
                    return False
        return True
