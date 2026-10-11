"""Regression tests for the framework-specific prompt text.

This is the highest-value test in the suite. A `profile` parameter was once
added to `render_generate_prompt` and one call site was missed, so the generate
prompt silently fell back to `TargetProfile()` — JUnit 4 / Java 8 — and told
every project "Do NOT use assertThrows()", including the JUnit 5 ones. The
generated files still compiled, so nothing caught it.

Careful with the obvious assertion: the JUnit 4 rule *bans* assertThrows, so the
string "assertThrows" appears in BOTH prompts. `assert "assertThrows" not in
junit4_prompt` would fail. Assert on the ban and on the lambda requirement.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from prompt_manager import PromptManager
from target_profile import TargetProfile

PROMPTS = Path(__file__).resolve().parent.parent / "prompts"


@pytest.fixture
def manager():
    return PromptManager(PROMPTS)


@pytest.fixture
def junit4():
    return TargetProfile(java_version=8, junit_version=4)


@pytest.fixture
def junit5():
    return TargetProfile(java_version=17, junit_version=5)


def _system(manager, profile, make_method) -> str:
    system, _ = manager.render_generate_prompt(
        make_method(), "[Normal] t", profile
    )
    return system


class TestFrameworkRules:
    def test_junit5_requires_a_lambda(self, manager, junit5, make_method):
        system = _system(manager, junit5, make_method)
        assert "assertThrows" in system
        assert "LAMBDA" in system
        assert "org.junit.jupiter.api.Assertions" in system

    def test_junit5_does_not_ban_assert_throws(self, manager, junit5, make_method):
        assert "not available in JUnit 4" not in _system(
            manager, junit5, make_method
        )

    def test_junit4_bans_assert_throws(self, manager, junit4, make_method):
        system = _system(manager, junit4, make_method)
        assert "not available in JUnit 4" in system
        assert "org.junit.Assert" in system

    def test_junit4_does_not_ask_for_a_lambda(self, manager, junit4, make_method):
        assert "and pass a LAMBDA" not in _system(manager, junit4, make_method)

    def test_the_two_system_prompts_differ(self, manager, junit4, junit5, make_method):
        m = make_method()
        s4, _ = manager.render_generate_prompt(m, "[Normal] t", junit4)
        s5, _ = manager.render_generate_prompt(m, "[Normal] t", junit5)
        assert s4 != s5

    def test_the_user_prompt_is_framework_independent(
        self, manager, junit4, junit5, make_method
    ):
        # The framework reaches the model through the target string, not this
        # template — so the user prompt is byte-identical either way.
        m = make_method()
        _, u4 = manager.render_generate_prompt(m, "[Normal] t", junit4)
        _, u5 = manager.render_generate_prompt(m, "[Normal] t", junit5)
        assert u4 == u5

    def test_no_profile_defaults_to_junit4(self, manager, make_method):
        # Pins the silent default: a caller that forgets to pass a profile gets
        # JUnit 4 rules. If that ever changes, this test is what says so.
        assert "not available in JUnit 4" in _system(manager, None, make_method)


class TestDeterminism:
    def test_rendering_is_byte_identical_across_calls(self, manager, junit5, make_method):
        # Everything downstream — the replay fixtures, the checkpoint — rests
        # on the same MethodInfo producing byte-identical prompts.
        m = make_method(branch_conditions=["a > 0"], throws_exceptions=["java.io.IOException"])
        first = manager.render_generate_prompt(m, "[Boundary] t", junit5)
        second = manager.render_generate_prompt(m, "[Boundary] t", junit5)
        assert first == second

    def test_method_data_is_substituted(self, manager, junit5, make_method):
        system, user = manager.render_generate_prompt(
            make_method(fqn="com.demo.Calculator.divide(int, int)"),
            "[Normal] t",
            junit5,
        )
        assert "com.demo.Calculator.divide(int, int)" in user
        assert "[Normal] t" in user
        # Placeholders must all be gone once rendering is done.
        assert "#{" not in user
