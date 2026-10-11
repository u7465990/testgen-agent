"""The suite must never reach the network — and the LLM API least of all.

CI runs these tests with no secrets and no budget, so "no test calls out" is a
property worth enforcing rather than trusting. `tests/conftest.py` installs two
autouse guards:

* every outbound socket connection fails;
* a live LLM client cannot be used even if one is constructed.

This module pins both, so neither can quietly rot.

Worth being precise about the second one: constructing `openai.OpenAI(api_key="")`
does *not* fail — the SDK only objects to `None` — so the guard is not what
makes construction succeed. It is what stops a constructed client from being
used, which is where the network call would happen.

The e2e tests are exempt by construction: they replace `LLMClient.generate`
outright, so the placeholder client is never dereferenced, and Maven does its
own networking in the JVM rather than through Python sockets.
"""

from __future__ import annotations

import os
import socket

import pytest

from config import AgentConfig
from llm_client import LLMClient, LLMError

_NETWORK_MESSAGE = "tried to open a network connection"


class TestNetworkGuard:
    def test_create_connection_is_blocked(self):
        with pytest.raises(RuntimeError, match=_NETWORK_MESSAGE):
            socket.create_connection(("example.com", 80), timeout=1)

    def test_a_raw_socket_connect_is_blocked(self):
        # The module-level helpers are the common path; this proves the patch
        # sits on the socket class itself, where a library would land.
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            with pytest.raises(RuntimeError, match=_NETWORK_MESSAGE):
                sock.connect(("example.com", 80))
        finally:
            sock.close()


class TestLLMGuard:
    def test_the_real_sdk_client_is_never_built(self, tmp_path, monkeypatch):
        """Asserted structurally, not by calling `generate`.

        If the guard is ever removed this fails on the first line, instead of
        the suite first making a real HTTP request and then reporting a
        confusing auth error. The deleted env vars are belt-and-braces:
        construction must not depend on the environment having an API key.
        """
        for name in ("OPENAI_API_KEY", "ANTHROPIC_API_KEY",
                     "ANTHROPIC_AUTH_TOKEN"):
            monkeypatch.delenv(name, raising=False)
            assert os.environ.get(name) is None

        client = LLMClient(AgentConfig(project_path=tmp_path))

        with pytest.raises(RuntimeError, match="No test may call the LLM API"):
            client._client.chat  # any use of the provider SDK is a test bug

    @pytest.mark.parametrize("provider", ["openai", "anthropic"])
    def test_generate_without_stubbing_the_llm_fails_loudly(
        self, tmp_path, provider
    ):
        """A test that forgets to stub the LLM gets our message, not a bill.

        `max_llm_retries=1` keeps `generate` from sleeping through its
        exponential backoff — it would otherwise take 2 + 4 seconds to fail,
        which is its own kind of bug.
        """
        config = AgentConfig(
            project_path=tmp_path, llm_provider=provider, max_llm_retries=1
        )
        client = LLMClient(config)

        with pytest.raises(LLMError, match="No test may call the LLM API"):
            client.generate("system prompt", "user prompt")
