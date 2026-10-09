"""Unified LLM client — supports OpenAI and Anthropic."""

from __future__ import annotations

import os
import time
from typing import Optional

from config import AgentConfig
from runlog import get_logger

logger = get_logger(__name__)


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
            # Respect ANTHROPIC_BASE_URL so Anthropic-compatible
            # providers (e.g. DeepSeek) work out of the box.
            return Anthropic(
                api_key=api_key,
                base_url=os.environ.get("ANTHROPIC_BASE_URL"),
            )
        else:
            raise ValueError(f"Unsupported provider: {self.provider}")

    def generate(self, system_prompt: str, user_prompt: str) -> str:
        """Send a chat completion request and return the text response."""
        last_error: Optional[Exception] = None

        # Prompt *sizes* only — never the API key, and the prompt bodies would
        # bloat the log for little diagnostic value.
        logger.debug(
            "LLM request provider=%s model=%s temp=%s sys=%dch user=%dch",
            self.provider, self.model, self.temperature,
            len(system_prompt), len(user_prompt),
        )

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
                    text = response.choices[0].message.content or ""
                    logger.debug("LLM response %dch:\n%s", len(text), text)
                    return text

                elif self.provider == "anthropic":
                    response = self._client.messages.create(
                        model=self.model,
                        system=system_prompt,
                        messages=[{"role": "user", "content": user_prompt}],
                        max_tokens=4096,
                        temperature=self.temperature,
                    )
                    # Response may contain ThinkingBlock(s) before the
                    # final TextBlock (e.g. DeepSeek reasoning models).
                    # Concatenate only the text blocks.
                    text = "".join(
                        block.text
                        for block in response.content
                        if getattr(block, "type", "") == "text" and block.text
                    )
                    logger.debug("LLM response %dch:\n%s", len(text), text)
                    return text

            except Exception as e:
                last_error = e
                logger.debug(
                    "LLM call failed (attempt %d/%d): %r",
                    attempt, self.max_retries, e,
                )
                if attempt < self.max_retries:
                    wait = 2 ** attempt
                    print(f"  LLM call failed (attempt {attempt}), "
                          f"retrying in {wait}s: {e}")
                    time.sleep(wait)

        raise LLMError(
            f"LLM call failed after {self.max_retries} attempts: {last_error}"
        ) from last_error
