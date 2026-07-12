"""Unified LLM client — supports OpenAI and Anthropic."""

from __future__ import annotations

import os
import time
from typing import Optional

from config import AgentConfig


class LLMError(Exception):
    """Raised when the LLM call fails after all retries."""


class LLMClient:
    """Lightweight wrapper around OpenAI and Anthropic chat completion APIs."""

    def __init__(self, config: AgentConfig):
        self.provider = config.llm_provider
        self.model = config.llm_model
        self.temperature = config.temperature
        self.max_retries = config.max_llm_retries
        self._client = self._init_client(config.get_api_key())

    def _init_client(self, api_key: str):
        if self.provider == "openai":
            from openai import OpenAI
            return OpenAI(api_key=api_key)
        elif self.provider == "anthropic":
            from anthropic import Anthropic
            return Anthropic(api_key=api_key)
        else:
            raise ValueError(f"Unsupported provider: {self.provider}")

    def generate(self, system_prompt: str, user_prompt: str) -> str:
        """Send a chat completion request and return the text response."""
        last_error: Optional[Exception] = None

        for attempt in range(1, self.max_retries + 1):
            try:
                if self.provider == "openai":
                    response = self._client.chat.completions.create(
                        model=self.model,
                        messages=[
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": user_prompt},
                        ],
                        temperature=self.temperature,
                    )
                    return response.choices[0].message.content or ""

                elif self.provider == "anthropic":
                    response = self._client.messages.create(
                        model=self.model,
                        system=system_prompt,
                        messages=[{"role": "user", "content": user_prompt}],
                        max_tokens=4096,
                        temperature=self.temperature,
                    )
                    return response.content[0].text if response.content else ""

            except Exception as e:
                last_error = e
                if attempt < self.max_retries:
                    wait = 2 ** attempt
                    print(f"  LLM call failed (attempt {attempt}), "
                          f"retrying in {wait}s: {e}")
                    time.sleep(wait)

        raise LLMError(
            f"LLM call failed after {self.max_retries} attempts: {last_error}"
        ) from last_error
