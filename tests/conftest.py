"""Shared fixtures for the testgen-agent test suite.

Everything here is deterministic and offline: no LLM call, no javac, no Maven.
That is what lets the suite run in CI with no API key and no JDK — and the two
autouse guards below enforce that rather than assuming it.
"""

from __future__ import annotations

import socket
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

from llm_client import LLMClient  # noqa: E402
from method_extractor import MethodInfo  # noqa: E402


@pytest.fixture(autouse=True)
def _no_outbound_network(monkeypatch):
    """Fail any test that opens an outbound network connection.

    The suite must run with no secrets and no cost, and "no test calls the LLM
    API" is the same property as "no test makes a network call" — enforced once
    here rather than trusted per-test. It also covers the paths the LLM guard
    below cannot see (a stray `requests` call, a download).

    Maven is unaffected: the e2e tests shell out to it, and the JVM does its own
    networking rather than going through Python sockets. `socket.socket.connect`
    is where every outbound attempt lands, `create_connection` and `urlopen`
    included — both were checked to be intercepted.
    """
    def deny(*args, **kwargs):
        raise RuntimeError(
            "A test tried to open a network connection. The suite must run "
            "offline — no API calls, no downloads. Stub the caller instead "
            "(see tests/test_e2e_pipeline.py for the LLM case)."
        )

    monkeypatch.setattr(socket.socket, "connect", deny)
    monkeypatch.setattr(socket.socket, "connect_ex", deny)
    monkeypatch.setattr(socket, "create_connection", deny)


class _NoRealLLMClient:
    """Stand-in for the provider SDK client. Any use of it is a test bug."""

    def __getattr__(self, name):
        raise RuntimeError(
            "No test may call the LLM API — the suite runs with no API key, no "
            "network and no cost, which is what lets CI run it without secrets. "
            "Stub LLMClient.generate instead, as tests/test_e2e_pipeline.py "
            "does."
        )


@pytest.fixture(autouse=True)
def _never_use_a_real_llm_client(monkeypatch):
    """Make a live LLM client unusable, suite-wide.

    `LLMClient.__init__` would otherwise import the provider SDK and hold a
    real client — one HTTP call away from the API, with whatever key the
    environment happens to hold. Substituting the client rather than refusing
    to build one keeps every test free to construct an `LLMClient` and patch
    `generate` itself, which is exactly what the e2e tests do. See
    tests/test_offline_guarantees.py.
    """
    monkeypatch.setattr(LLMClient, "_init_client",
                        lambda self, key: _NoRealLLMClient())


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
