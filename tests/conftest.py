"""Shared fixtures for the testgen-agent test suite.

Everything here is deterministic and offline: no LLM call, no javac, no Maven.
That is what lets the suite run in CI with no API key and no JDK.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

# The modules under test are flat at the repo root and use absolute flat
# imports (`from config import AgentConfig`), exactly as `python main.py`
# resolves them. pytest.ini's `pythonpath` does this too; repeating it here
# keeps the suite working on pytest versions without that option.
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from method_extractor import MethodInfo  # noqa: E402


@pytest.fixture
def make_method():
    """Factory for a MethodInfo carrying only what a given test cares about.

    MethodInfo has eleven required fields and everything else defaulted, so a
    helper keeps each test's intent visible instead of buried in boilerplate.
    """

    def _make(
        fqn: str = "com.demo.Calculator.add(int, int)",
        class_name: str = "Calculator",
        method_name: str = "add",
        package_name: str = "com.demo",
        parameter_types=("int", "int"),
        parameter_names=("a", "b"),
        **overrides,
    ) -> MethodInfo:
        return MethodInfo(
            project_name="demo",
            source_file="Calculator.java",
            class_name=class_name,
            package_name=package_name,
            method_name=method_name,
            fqn=fqn,
            signature="int add(int a, int b)",
            return_type="int",
            parameter_types=list(parameter_types),
            parameter_names=list(parameter_names),
            modifiers=["public"],
            **overrides,
        )

    return _make
