"""Tests for target_generator.py — the target strings handed to the LLM."""

from __future__ import annotations

import pytest

from method_extractor import Collaborator
from target_generator import TargetGenerator
from target_profile import TargetProfile


@pytest.fixture
def junit4():
    return TargetProfile(java_version=8, junit_version=4)


@pytest.fixture
def junit5():
    return TargetProfile(java_version=17, junit_version=5)


def _gen(profile, types, cap=100) -> TargetGenerator:
    return TargetGenerator(
        target_types=types, max_tests_per_method=cap, profile=profile
    )


class TestNormal:
    def test_one_normal_target(self, junit4, make_method):
        targets = _gen(junit4, ["normal"]).generate_targets(make_method())
        assert len(targets) == 1
        assert targets[0].startswith("[Normal]")

    def test_framework_name_follows_the_profile(self, junit4, junit5, make_method):
        assert "JUnit 4" in _gen(junit4, ["normal"]).generate_targets(make_method())[0]
        assert "JUnit 5" in _gen(junit5, ["normal"]).generate_targets(make_method())[0]


class TestBoundary:
    def test_one_target_per_edge_value(self, junit4, make_method):
        m = make_method(
            parameter_types=("String", "int"), parameter_names=("s", "n")
        )
        targets = _gen(junit4, ["boundary"]).generate_targets(m)
        # String -> 3 edges (null / empty / non-empty), int -> 3 (0 / 1 / -1).
        assert len(targets) == 6
        assert all(t.startswith("[Boundary]") for t in targets)
        assert '""' in targets[1]
        assert "-1" in targets[-1]

    def test_string_edges_keep_their_order(self, junit4, make_method):
        m = make_method(parameter_types=("String",), parameter_names=("s",))
        targets = _gen(junit4, ["boundary"]).generate_targets(m)
        assert "null" in targets[0]
        assert '"test"' in targets[2]

    def test_array_type_gets_array_edges(self, junit4, make_method):
        m = make_method(parameter_types=("int[]",), parameter_names=("xs",))
        targets = _gen(junit4, ["boundary"]).generate_targets(m)
        assert "new int[0]" in targets[1]

    def test_unknown_type_falls_back_to_a_default(self, junit4, make_method):
        m = make_method(parameter_types=("Foo",), parameter_names=("f",))
        targets = _gen(junit4, ["boundary"]).generate_targets(m)
        assert len(targets) == 1
        assert "(Foo) 0" in targets[0]


class TestCapAndMockOrder:
    def test_cap_truncates(self, junit4, make_method):
        m = make_method(
            parameter_types=("String", "int"), parameter_names=("s", "n")
        )
        targets = _gen(junit4, ["normal", "boundary"], cap=2).generate_targets(m)
        assert len(targets) == 2
        assert targets[0].startswith("[Normal]")

    def test_mock_target_is_prepended_and_exempt_from_the_cap(self, make_method):
        # The cap is 1, yet the mock target survives and holds index 0. That is
        # the invariant the resume checkpoint's class names depend on.
        profile = TargetProfile(
            java_version=8, junit_version=4, mockito_available=True
        )
        m = make_method(
            collaborators=[Collaborator(type_name="PaymentGateway")]
        )
        targets = TargetGenerator(["normal", "mock"], 1, profile).generate_targets(m)
        assert len(targets) == 2
        assert targets[0].startswith("[Mock]")
        assert targets[1].startswith("[Normal]")

    def test_no_mock_target_without_mockito(self, junit4, make_method):
        m = make_method(
            collaborators=[Collaborator(type_name="PaymentGateway")]
        )
        targets = _gen(junit4, ["normal", "mock"]).generate_targets(m)
        assert not any(t.startswith("[Mock]") for t in targets)

    def test_no_mock_target_without_collaborators(self, make_method):
        profile = TargetProfile(
            java_version=8, junit_version=4, mockito_available=True
        )
        targets = _gen(profile, ["normal", "mock"]).generate_targets(make_method())
        assert not any(t.startswith("[Mock]") for t in targets)


class TestException:
    def test_junit4_uses_try_catch(self, junit4, make_method):
        m = make_method(throws_exceptions=["java.io.IOException"])
        targets = _gen(junit4, ["exception"]).generate_targets(m)
        assert len(targets) == 1
        assert targets[0].startswith("[Exception]")
        assert "IOException" in targets[0]
        assert "try-catch" in targets[0]
        assert "Do NOT use assertThrows" in targets[0]

    def test_junit5_uses_assert_throws_with_a_lambda(self, junit5, make_method):
        m = make_method(throws_exceptions=["java.io.IOException"])
        targets = _gen(junit5, ["exception"]).generate_targets(m)
        assert "assertThrows" in targets[0]
        assert "lambda" in targets[0]

    def test_no_declared_exceptions_means_no_target(self, junit4, make_method):
        # Known gap: an exception thrown from the *body* rather than named in
        # the throws clause gets no target, because throws_exceptions is the
        # only source. Pinned so the gap is visible if it is ever closed.
        assert _gen(junit4, ["exception"]).generate_targets(make_method()) == []


class TestPath:
    def test_two_targets_per_branch_condition(self, junit4, make_method):
        m = make_method(branch_conditions=["a > 0"])
        targets = _gen(junit4, ["path"]).generate_targets(m)
        assert len(targets) == 2
        assert "condition holds" in targets[0]
        assert "FALSE" in targets[1]

    def test_no_branches_falls_back_to_statement_coverage(self, junit4, make_method):
        targets = _gen(junit4, ["path"]).generate_targets(make_method())
        assert len(targets) == 1
        assert "statement coverage" in targets[0]


class TestReflection:
    def test_private_method_gets_a_reflection_target(self, junit4, make_method):
        targets = _gen(junit4, ["reflection"]).generate_targets(
            make_method(is_private=True)
        )
        assert len(targets) == 1
        assert targets[0].startswith("[Reflection]")
        assert "getDeclaredMethod" in targets[0]

    def test_public_method_does_not(self, junit4, make_method):
        assert _gen(junit4, ["reflection"]).generate_targets(
            make_method(is_private=False)
        ) == []


class TestDeterminism:
    def test_same_method_yields_the_same_targets(self, junit4, make_method):
        gen = _gen(junit4, ["normal", "boundary", "path", "exception"])
        m = make_method(
            parameter_types=("String", "int"),
            parameter_names=("s", "n"),
            branch_conditions=["a > 0"],
            throws_exceptions=["java.io.IOException"],
        )
        assert gen.generate_targets(m) == gen.generate_targets(m)
