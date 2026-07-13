#!/usr/bin/env python3
"""
testgen-agent — AI agent for automatic JUnit 4 test generation.

Usage:
    testgen-agent analyze   <project-path>   # Discover methods
    testgen-agent generate  <project-path>   # Full pipeline
    testgen-agent repair    <project-path>   # Repair existing generated tests
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from config import AgentConfig
from agent import TestGeneratorAgent


def build_config(args: argparse.Namespace) -> AgentConfig:
    """Build AgentConfig from parsed CLI arguments."""
    return AgentConfig(
        project_path=Path(args.project_path),
        extraction_mode=args.extraction_mode,
        llm_provider=args.provider,
        llm_model=args.model,
        api_key=args.api_key,
        temperature=args.temperature,
        include_constructors=args.include_constructors,
        include_private=not args.skip_private,
        target_packages=args.package,
        exclude_methods=args.exclude,
        target_types=args.target_types,
        max_tests_per_method=args.max_per_method,
        max_compile_attempts=args.max_repair,
        run_coverage_improvement=not args.no_coverage,
        output_dir=args.output_dir,
        report_format=args.report_format,
        verbose=args.verbose,
    )


def cmd_analyze(config: AgentConfig) -> None:
    """Discover source files and methods without generating tests."""
    from java_analyzer import JavaProjectAnalyzer
    from method_extractor import MethodExtractor

    analyzer = JavaProjectAnalyzer(config.project_path)
    extractor = MethodExtractor(
        project_name=config.project_path.name,
        mode=config.extraction_mode,
        java_home=config.java_home,
    )

    print(f"Project: {config.project_path}")
    print(f"Build tool: {analyzer.detect_build_tool()}")
    print()

    sources = analyzer.find_source_files()
    print(f"Found {len(sources)} source files:\n")

    for src in sources:
        methods = extractor.extract_methods(src)
        print(f"  {src.qualified_name}")
        print(f"    File: {src.path}")
        for m in methods:
            mods = " ".join(m.modifiers)
            params = ", ".join(
                f"{t} {n}" for t, n in zip(m.parameter_types, m.parameter_names)
            )
            ret = m.return_type + " " if m.return_type else ""
            print(f"    {mods} {ret}{m.method_name}({params})")
            if m.branch_conditions:
                for bc in m.branch_conditions:
                    print(f"      └─ condition: {bc}")
            if m.throws_exceptions:
                print(f"      throws: {', '.join(m.throws_exceptions)}")
        print()


def cmd_generate(config: AgentConfig) -> None:
    """Run the full test generation pipeline."""
    agent = TestGeneratorAgent(config)
    report = agent.run()

    # Exit with error code if nothing was generated
    if report.tests_runnable == 0:
        print("\nWARNING: No runnable tests were produced.")
        if report.errors:
            print("Errors encountered:")
            for e in report.errors:
                print(f"  - {e}")
        sys.exit(1)


def cmd_repair(config: AgentConfig) -> None:
    """Re-run compilation repair on already-generated tests.

    For MVP: scans the test directory for _Test_*.java files
    and attempts to repair any that don't compile.
    """
    from compiler import JavaCompiler
    from repair_loop import RepairLoop
    from prompt_manager import PromptManager
    from test_writer import TestWriter
    from method_extractor import MethodExtractor
    from llm_client import LLMClient

    analyzer = JavaProjectAnalyzer(config.project_path)
    test_dir = analyzer.find_test_directory()
    test_files = list(test_dir.rglob("*_Test_*.java"))

    if not test_files:
        print("No generated test files found")
        return

    print(f"Found {len(test_files)} generated test files")

    compiler = JavaCompiler(config)
    classpath = compiler.resolve_classpath()

    success_count = 0
    for tf in test_files:
        success, error = compiler.compile(tf, classpath)
        if success:
            success_count += 1
            print(f"  ✓ {tf.name}")
        else:
            print(f"  ✗ {tf.name}")
            print(f"    {error[:200]}")

    print(f"\n{success_count}/{len(test_files)} compile successfully")


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="testgen-agent — automatic JUnit 4 test generation agent",
    )
    parser.add_argument(
        "command",
        choices=["analyze", "generate", "repair"],
        help="Action to perform",
    )
    parser.add_argument(
        "project_path",
        help="Path to the Java project root",
    )

    # Extraction mode
    parser.add_argument(
        "--extraction-mode", default="python",
        choices=["python", "sootup"],
        help="Extraction backend: 'python' (javalang, default) or 'sootup' (adds Jimple IR)",
    )

    # LLM options
    parser.add_argument(
        "--provider", default="openai",
        choices=["openai", "anthropic"],
        help="LLM provider (default: openai)",
    )
    parser.add_argument(
        "--model", default="gpt-4o-mini",
        help="LLM model (default: gpt-4o-mini)",
    )
    parser.add_argument(
        "--api-key",
        help="API key (default: read from env OPENAI_API_KEY / ANTHROPIC_API_KEY)",
    )
    parser.add_argument(
        "--temperature", type=float, default=0.2,
        help="LLM temperature (default: 0.2)",
    )

    # Target filtering
    parser.add_argument(
        "--package", action="append", default=[],
        help="Only target methods in this package (can repeat)",
    )
    parser.add_argument(
        "--exclude", action="append", default=[],
        help="Exclude methods by name (can repeat)",
    )
    parser.add_argument(
        "--skip-private", action="store_true",
        help="Skip private methods",
    )
    parser.add_argument(
        "--include-constructors", action="store_true",
        help="Include constructors as targets",
    )
    parser.add_argument(
        "--target-types", nargs="*",
        default=["normal", "boundary", "exception", "path", "reflection"],
        help="Target types to generate (default: all)",
    )
    parser.add_argument(
        "--max-per-method", type=int, default=10,
        help="Max targets per method (default: 10)",
    )

    # Build / repair
    parser.add_argument(
        "--max-repair", type=int, default=3,
        help="Max compilation repair attempts (default: 3)",
    )
    parser.add_argument(
        "--no-coverage", action="store_true",
        help="Skip coverage-guided improvement phase",
    )

    # Output
    parser.add_argument(
        "--output-dir",
        help="Test output directory (default: project's src/test/java)",
    )
    parser.add_argument(
        "--report-format", default="both",
        choices=["json", "csv", "both"],
        help="Report output format (default: both)",
    )
    parser.add_argument(
        "-v", "--verbose", action="store_true",
        help="Verbose output",
    )

    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv or sys.argv[1:])
    config = build_config(args)

    if args.command == "analyze":
        cmd_analyze(config)
    elif args.command == "generate":
        cmd_generate(config)
    elif args.command == "repair":
        cmd_repair(config)


if __name__ == "__main__":
    main()
