"""Tests for collaborator_resolver.py — deciding what is safe to mock.

The bar this module sets is what keeps the Mockito feature from firing on
projects that have nothing to mock: a collaborator must resolve to *project
source* and be an interface or abstract class, and a constructor with one
unresolvable parameter disqualifies the whole class. Both halves matter — the
first stops a mock being invented for a JDK type, the second stops a skeleton
being emitted for a class the test cannot actually instantiate.

Everything is offline: the Java sources are written to tmp_path and parsed with
javalang. No JDK, no Maven, no LLM.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from collaborator_resolver import (
    ResolvedType,
    SourceIndex,
    _core_name,
    _fully_qualified_is_jdk,
    is_jdk_type,
)
from extractor.javalang_backend import _ClassShape
from java_analyzer import SourceFile
from method_extractor import ConstructorInfo, FieldInfo

# ── Fixture sources ───────────────────────────────────────────

GATEWAY = """package com.demo;
public interface PaymentGateway {
    boolean charge(String token, double amount);
    void refund(String token);
}
"""

NOTIFIER = """package com.demo;
public interface Notifier {
    void notify(String message);
}
"""

ABSTRACT_BASE = """package com.demo;
public abstract class AbstractStore {
    public abstract void save(String key);
    protected void helper() { }
}
"""

CONCRETE = """package com.demo;
public class ConcreteThing {
    public void doIt() { }
}
"""

COMBO = """package com.demo;
public class Combo {
    public void onlyPublic() { }
    private void secret() { }
    public static void util() { }
    void packagePrivate() { }
}
"""

NESTED = """package com.demo;
public class Outer {
    public interface Inner { void ping(); }
    public void onOuter() { }
}
"""

# A second PaymentGateway in another package, for the ambiguity case.
DUP_GATEWAY = """package com.other;
public interface PaymentGateway {
    boolean charge(String token, double amount);
}
"""


def _source(tmp_path: Path, rel: str, code: str) -> SourceFile:
    """Write a Java file at src/main/java/<rel> and wrap it as a SourceFile."""
    path = tmp_path / "src/main/java" / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(code, encoding="utf-8")
    package = ".".join(Path(rel).parts[:-1])
    return SourceFile(path, package)


@pytest.fixture
def index(tmp_path):
    """An index over the fixture project, with an ambiguity left in place."""
    sources = [
        _source(tmp_path, "com/demo/PaymentGateway.java", GATEWAY),
        _source(tmp_path, "com/demo/Notifier.java", NOTIFIER),
        _source(tmp_path, "com/demo/AbstractStore.java", ABSTRACT_BASE),
        _source(tmp_path, "com/demo/ConcreteThing.java", CONCRETE),
        _source(tmp_path, "com/demo/Combo.java", COMBO),
        _source(tmp_path, "com/demo/Outer.java", NESTED),
        _source(tmp_path, "com/other/PaymentGateway.java", DUP_GATEWAY),
    ]
    return SourceIndex(sources)


# ── Type text handling ────────────────────────────────────────

class TestCoreName:
    @pytest.mark.parametrize(
        "written,expected",
        [
            ("String", "String"),
            ("  Foo  ", "Foo"),
            ("List<Order>", "List"),
            ("Map<String, List<Order>>", "Map"),
            ("List<Order>[]", "List"),
            ("String...", "String"),
            ("final Foo", "Foo"),
            ("String[]", "String"),
        ],
    )
    def test_reduces_to_the_outer_name(self, written, expected):
        assert _core_name(written) == expected

    @pytest.mark.parametrize("written", ["", "   ", None, "<T>"])
    def test_nothing_usable_is_none(self, written):
        assert _core_name(written) is None

    def test_generic_arguments_are_dropped_not_recursed_into(self):
        # Injecting a List is what the constructor takes; Order is not a
        # dependency of the class just because it sits between the brackets.
        assert _core_name("List<Order>") == "List"


class TestIsJdkType:
    @pytest.mark.parametrize(
        "written", ["int", "void", "boolean", "double", "char"]
    )
    def test_primitives_are_never_mockable(self, written):
        assert is_jdk_type(written) is True

    @pytest.mark.parametrize(
        "written",
        ["String", "Object", "List<String>", "Optional<Foo>", "LocalDate",
         "String[]", "Map<String, Integer>", "BigDecimal"],
    )
    def test_jdk_value_types_are_never_mockable(self, written):
        assert is_jdk_type(written) is True

    @pytest.mark.parametrize(
        "written", ["PaymentGateway", "com.demo.PaymentGateway"]
    )
    def test_a_project_type_is_not_jdk(self, written):
        assert is_jdk_type(written) is False

    def test_empty_text_counts_as_jdk(self):
        # Fails closed: an unreadable type must never become a mock candidate.
        assert is_jdk_type("") is True


class TestFullyQualifiedIsJdk:
    @pytest.mark.parametrize(
        "name", ["java.util.List", "javax.swing.JFrame", "jakarta.mail.Session"]
    )
    def test_jdk_packages(self, name):
        assert _fully_qualified_is_jdk(name) is True

    @pytest.mark.parametrize("name", ["com.demo.Foo", "PaymentGateway", ""])
    def test_everything_else(self, name):
        assert _fully_qualified_is_jdk(name) is False


class TestResolvedType:
    @pytest.mark.parametrize("kind", ["interface", "abstract-class"])
    def test_only_the_mockable_shapes(self, kind):
        assert ResolvedType("X", "com.demo.X", Path("X.java"), kind).is_mockable

    def test_a_concrete_class_is_not_mockable(self):
        # Deliberate: the module's scope line says concrete project classes are
        # not covered. Pinned so widening it is a conscious change.
        assert not ResolvedType(
            "X", "com.demo.X", Path("X.java"), "class"
        ).is_mockable


# ── Resolution order ──────────────────────────────────────────

class TestResolve:
    def test_same_package_needs_no_import(self, index):
        found = index.resolve("PaymentGateway", "com.demo", [])
        # Two PaymentGateways exist project-wide, so this only resolves because
        # the owner's own package wins before the project-wide fallback.
        assert found is not None and found.fqn == "com.demo.PaymentGateway"

    def test_an_explicit_import_wins(self, index):
        found = index.resolve("PaymentGateway", "com.elsewhere",
                              ["com.other.PaymentGateway"])
        assert found is not None and found.fqn == "com.other.PaymentGateway"

    def test_a_wildcard_import_works_when_nothing_else_matched(self, index):
        found = index.resolve("Notifier", "com.elsewhere", ["com.demo.*"])
        assert found is not None and found.fqn == "com.demo.Notifier"

    def test_a_unique_project_wide_name_resolves(self, index):
        # No import, no matching package, exactly one candidate in the project.
        found = index.resolve("Notifier", "com.elsewhere", [])
        assert found is not None and found.fqn == "com.demo.Notifier"

    def test_ambiguity_resolves_to_nothing(self, index):
        # Two PaymentGateways and nothing to choose between them. Returning one
        # would produce a mock that cannot compile.
        assert index.resolve("PaymentGateway", "com.elsewhere", []) is None

    def test_an_unknown_type_resolves_to_nothing(self, index):
        assert index.resolve("NeverDeclared", "com.demo", []) is None

    def test_a_written_fqn_resolves_directly(self, index):
        found = index.resolve("com.other.PaymentGateway", "com.elsewhere", [])
        assert found is not None and found.fqn == "com.other.PaymentGateway"

    @pytest.mark.parametrize(
        "written", ["String", "java.util.List", "int", "java.time.LocalDate"]
    )
    def test_jdk_types_resolve_to_nothing(self, index, written):
        assert index.resolve(written, "com.demo", []) is None


# ── Shape parsing ─────────────────────────────────────────────

class TestParsedShapes:
    def test_an_interface_is_labelled_as_one(self, index):
        found = index.resolve("PaymentGateway", "com.demo", [])
        assert found.kind == "interface" and found.is_mockable

    def test_an_abstract_class_is_labelled_as_one(self, index):
        found = index.resolve("AbstractStore", "com.demo", [])
        assert found.kind == "abstract-class" and found.is_mockable

    def test_a_concrete_class_is_labelled_as_one(self, index):
        found = index.resolve("ConcreteThing", "com.demo", [])
        assert found.kind == "class" and not found.is_mockable

    def test_a_nested_type_is_not_exposed(self, index):
        # Injecting `Inner` by simple name would not compile without
        # qualification, so nested declarations are skipped.
        assert index.resolve("Inner", "com.demo", []) is None

    def test_an_unparseable_file_degrades_to_nothing(self, tmp_path):
        broken = _source(tmp_path, "com/demo/Broken.java", "public class {{{")
        index = SourceIndex([broken])
        assert index.resolve("Broken", "com.demo", []) is None


class TestPublicSignatures:
    def test_interface_methods_are_kept_despite_no_modifier(self, index):
        # Interface methods are implicitly public; dropping them would leave the
        # prompt without the signatures it exists to supply.
        found = index.resolve("PaymentGateway", "com.demo", [])
        assert "boolean charge(String, double)" in found.method_signatures

    def test_a_concrete_class_advertises_only_its_public_methods(self, index):
        found = index.resolve("Combo", "com.demo", [])
        assert "void onlyPublic()" in found.method_signatures
        assert not any("secret" in s for s in found.method_signatures)
        assert not any("packagePrivate" in s for s in found.method_signatures)

    def test_static_helpers_are_excluded_from_a_class(self, index):
        # A mock cannot be stubbed on a static method.
        found = index.resolve("Combo", "com.demo", [])
        assert not any("util" in s for s in found.method_signatures)


# ── Collaborator detection ────────────────────────────────────

def _shape(constructor_types=(), field_types=()):
    return _ClassShape(
        name="Service",
        fields=[FieldInfo(type_name=t, name=f"f{i}")
                for i, t in enumerate(field_types)],
        constructors=[
            ConstructorInfo(name="Service", parameter_types=list(constructor_types))
        ] if constructor_types else [],
    )


class TestFindCollaborators:
    def test_a_constructor_injected_interface_is_a_collaborator(self, index):
        found = index.find_collaborators(
            _shape(constructor_types=["PaymentGateway"]), "com.demo", []
        )
        assert len(found) == 1
        assert found[0].fqn == "com.demo.PaymentGateway"
        assert found[0].injection == "constructor"
        assert found[0].kind == "interface"

    def test_a_field_injected_interface_is_a_collaborator(self, index):
        found = index.find_collaborators(
            _shape(field_types=["Notifier"]), "com.demo", []
        )
        assert len(found) == 1
        assert found[0].injection == "field"

    def test_jdk_parameters_alongside_a_collaborator_are_fine(self, index):
        # The test can supply a String literal; the collaborator gets mocked.
        found = index.find_collaborators(
            _shape(constructor_types=["String", "PaymentGateway", "int"]),
            "com.demo", [],
        )
        assert [c.fqn for c in found] == ["com.demo.PaymentGateway"]

    def test_a_class_with_only_jdk_dependencies_yields_nothing(self, index):
        # The property that makes this feature a no-op on ordinary projects.
        assert index.find_collaborators(
            _shape(constructor_types=["String", "double", "List<String>"]),
            "com.demo", [],
        ) == []

    def test_a_concrete_project_class_is_not_a_collaborator(self, index):
        assert index.find_collaborators(
            _shape(constructor_types=["ConcreteThing"]), "com.demo", []
        ) == []

    def test_an_unresolvable_parameter_disqualifies_the_class(self, index):
        # Mocking one of two dependencies and inventing the other would produce
        # a skeleton that cannot compile — the whole constructor must be
        # satisfiable, not just the part that happens to resolve.
        assert index.find_collaborators(
            _shape(constructor_types=["PaymentGateway", "NeverDeclared"]),
            "com.demo", [],
        ) == []

    def test_no_dependencies_at_all(self, index):
        assert index.find_collaborators(_shape(), "com.demo", []) == []

    def test_the_source_path_is_carried_through(self, index):
        found = index.find_collaborators(
            _shape(constructor_types=["PaymentGateway"]), "com.demo", []
        )
        assert found[0].source_path.endswith("PaymentGateway.java")

    def test_signatures_are_carried_through_for_the_prompt(self, index):
        found = index.find_collaborators(
            _shape(constructor_types=["PaymentGateway"]), "com.demo", []
        )
        assert "boolean charge(String, double)" in found[0].method_signatures
