"""
Claude Code skill entry point for /generate-tests.

Invoked by Claude Code when the user asks to generate tests.
Parses skill arguments and delegates to the TestGeneratorAgent.

Returns structured data for Claude to interpret and present.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict, Optional

from config import AgentConfig
from agent import TestGeneratorAgent


def skill_entry(
    project_path: str,
    provider: str = "openai",
    model: str = "gpt-4o-mini",
    package: Optional[list[str]] = None,
    skip_private: bool = False,
    output_dir: Optional[str] = None,
) -> Dict[str, Any]:
    """Called by Claude Code when /generate-tests is invoked.

    Returns a structured dict that Claude can interpret and present to the user.
    """
    config = AgentConfig(
        project_path=Path(project_path),
        llm_provider=provider,
        llm_model=model,
        target_packages=package or [],
        include_private=not skip_private,
        output_dir=output_dir,
        report_format="json",
    )

    agent = TestGeneratorAgent(config)
    report = agent.run()

    return {
        "summary": (
            f"Generated {report.tests_generated} tests for "
            f"{report.methods_targeted} methods across "
            f"{report.source_files_found} source files. "
            f"{report.tests_compiled} compiled, "
            f"{report.tests_runnable} runnable "
            f"({report.compilation_rate:.1%} compilation rate)."
        ),
        "project": report.project_path,
        "methods_found": report.methods_found,
        "methods_targeted": report.methods_targeted,
        "tests_generated": report.tests_generated,
        "tests_compiled": report.tests_compiled,
        "tests_runnable": report.tests_runnable,
        "compilation_rate": report.compilation_rate,
        "duration_seconds": report.duration_seconds,
        "report_path": (
            str(Path(project_path) / "target/testgen-agent/report.json")
        ),
    }


# ── CLI mode (called by skill.yaml) ──────────────────────────

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--project-path", required=True)
    parser.add_argument("--provider", default="openai")
    parser.add_argument("--model", default="gpt-4o-mini")
    parser.add_argument("--package", action="append", default=[])
    parser.add_argument("--skip-private", action="store_true")
    parser.add_argument("--output-dir")
    args = parser.parse_args()

    result = skill_entry(
        project_path=args.project_path,
        provider=args.provider,
        model=args.model,
        package=args.package or None,
        skip_private=args.skip_private,
        output_dir=args.output_dir,
    )
    print(json.dumps(result, indent=2))
