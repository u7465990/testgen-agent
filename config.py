"""Configuration dataclass for the test generation agent."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional


@dataclass
class AgentConfig:
    """All configuration for a single test generation run."""

    # ── Required ──────────────────────────────────────────────
    project_path: Path  # path to the Java project root

    # ── LLM ───────────────────────────────────────────────────
    llm_provider: str = "openai"  # "openai" or "anthropic"
    llm_model: str = "gpt-4o-mini"
    api_key: Optional[str] = None  # None = read from env var
    temperature: float = 0.2
    max_llm_retries: int = 3
    # Anthropic's API requires max_tokens (unlike OpenAI's, where it is
    # optional). 4096 truncated JUnit 5 tests mid-string on a real run — the
    # response looked fine until javac reported an unterminated string literal
    # at EOF. 8192 leaves headroom; raise it for unusually verbose tests.
    max_tokens: int = 8192

    # ── Extraction ────────────────────────────────────────────
    extraction_mode: str = "python"  # "python" (javalang) | "sootup" (javalang + Jimple)

    # ── Target framework ──────────────────────────────────────
    # "auto" follows the project under test (see target_profile.py): whichever
    # JUnit is on its test classpath, and the Java level its pom declares. An
    # explicit value forces it, which is how you generate JUnit 4 for a JUnit 5
    # project (or vice versa). Resolution happens at runtime against the actual
    # project, so the detected values live on a TargetProfile, not here.
    junit_version: str = "auto"   # "auto" | "4" | "5"
    java_version: str = "auto"    # "auto" | "8" | "11" | "17" | "21"

    # ── Method filtering ──────────────────────────────────────
    include_public: bool = True
    include_private: bool = True
    include_protected: bool = True
    include_package_private: bool = True
    include_static: bool = True
    include_constructors: bool = False
    include_abstract: bool = False
    target_packages: List[str] = field(default_factory=list)  # empty = all
    exclude_methods: List[str] = field(default_factory=list)  # by name

    # ── Target generation ─────────────────────────────────────
    target_types: List[str] = field(
        default_factory=lambda: ["normal", "boundary", "exception", "path"]
    )
    max_tests_per_method: int = 10

    # ── Build / compilation ───────────────────────────────────
    build_tool: str = "auto"  # "maven" | "ant" | "gradle" | "manual" | "auto"
    classpath_extras: List[str] = field(default_factory=list)
    java_home: Optional[str] = None  # None = read JAVA_HOME env

    # ── Repair loop ───────────────────────────────────────────
    max_compile_attempts: int = 3
    max_runtime_rounds: int = 3
    branch_coverage_target: float = 0.98
    run_coverage_improvement: bool = True

    # ── Quality analysis ──────────────────────────────────────
    # Compilation success only proves the file parses; these control the
    # measurement of whether the tests are actually meaningful.
    run_mutation_analysis: bool = True   # PiTest mutation score (Maven only)
    pitest_version: str = "1.15.0"
    mutation_timeout_seconds: int = 1800

    # ── Resume / checkpoint ───────────────────────────────────
    resume: bool = True  # skip already-generated tests on re-run (JSONL checkpoint)

    # ── Output ────────────────────────────────────────────────
    output_dir: Optional[str] = None  # default → project's src/test/java
    report_format: str = "json"  # "json" | "csv" | "both"
    verbose: bool = False

    # ── Derived helpers ───────────────────────────────────────

    def get_api_key(self) -> str:
        if self.api_key:
            return self.api_key
        if self.llm_provider == "openai":
            return os.environ.get("OPENAI_API_KEY", "")
        # Anthropic-compatible endpoints: prefer ANTHROPIC_API_KEY,
        # fall back to ANTHROPIC_AUTH_TOKEN (used by DeepSeek etc.)
        return (
            os.environ.get("ANTHROPIC_API_KEY")
            or os.environ.get("ANTHROPIC_AUTH_TOKEN")
            or ""
        )

    def get_java_home(self) -> Optional[str]:
        return self.java_home or os.environ.get("JAVA_HOME")
