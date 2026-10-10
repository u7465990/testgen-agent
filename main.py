#!/usr/bin/env python3
"""
testgen-agent — AI agent for automatic JUnit 4/5 test generation.

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
from runlog import setup_logging, get_logger

logger = get_logger(__name__)


def build_config(args: argparse.Namespace) -> AgentConfig:
    """Build AgentConfig from parsed CLI arguments."""
    return AgentConfig(
        project_path=Path(args.project_path),
        extraction_mode=args.extraction_mode,
        junit_version=args.junit,
        java_version=args.java,
        add_mock_deps=args.add_mock_deps,
        llm_provider=args.provider,
        llm_model=args.model,
        api_key=args.api_key,
        temperature=args.temperature,
        max_tokens=args.max_tokens,
        include_constructors=args.include_constructors,
        include_private=not args.skip_private,
        target_packages=args.package,
        exclude_methods=args.exclude,
        target_types=args.target_types,
        max_tests_per_method=args.max_per_method,
        max_compile_attempts=args.max_repair,
        run_coverage_improvement=not args.no_coverage,
        resume=not args.no_resume,
        run_mutation_analysis=not args.no_mutation,
        pitest_version=args.pitest_version,
        output_dir=args.output_dir,
        report_format=args.report_format,
        verbose=args.verbose,
    )


def cmd_analyze(config: AgentConfig) -> None:
    """Discover source files and methods without generating tests."""
    from java_analyzer import JavaProjectAnalyzer
    from method_extractor import MethodExtractor
    from target_profile import TargetProfile, detect_into

    analyzer = JavaProjectAnalyzer(config.project_path)

    # Detect here too: this is the fast, no-LLM inspection path, so it is the
    # natural place to check what `--junit auto` would resolve to before
    # spending any API calls.
    profile = detect_into(
        TargetProfile(),
        config.project_path,
        classpath=analyzer.resolve_classpath(),
        configured_java=config.java_version,
        configured_junit=config.junit_version,
    )
    extractor = MethodExtractor(
        project_name=config.project_path.name,
        mode=config.extraction_mode,
        java_home=config.java_home,
        profile=profile,
    )

    print(f"Project: {config.project_path}")
    print(f"Build tool: {analyzer.detect_build_tool()}")
    print(f"Target: {profile.describe()}")
    for warning in profile.warnings:
        print(f"  [WARN] {warning}")
    print()

    sources = analyzer.find_source_files()
    print(f"Found {len(sources)} source files:\n")

    total_methods = 0
    for src in sources:
        total_methods += len(extractor.extract_methods(src))
    logger.info("analyze: %d source files, %d methods, build tool=%s",
                len(sources), total_methods, analyzer.detect_build_tool())
    logger.debug("classpath: %s", analyzer.resolve_classpath())

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
    """Re-compile already-generated tests and report which fail.

    Scans the test directory for _Test_*.java files and compiles each one
    against the project classpath. NOTE: despite the name it does not invoke
    the LLM repair loop — it only reports status.
    """
    from compiler import JavaCompiler
    from java_analyzer import JavaProjectAnalyzer
    from target_profile import TargetProfile, detect_into

    analyzer = JavaProjectAnalyzer(config.project_path)
    test_dir = analyzer.find_test_directory()
    test_files = list(test_dir.rglob("*_Test_*.java"))

    if not test_files:
        print("No generated test files found")
        return

    print(f"Found {len(test_files)} generated test files")

    # Compile at the project's own Java level, not a hard-coded 8.
    profile = detect_into(
        TargetProfile(),
        config.project_path,
        classpath=analyzer.resolve_classpath(),
        configured_java=config.java_version,
        configured_junit=config.junit_version,
    )
    print(f"Target: {profile.describe()}")

    compiler = JavaCompiler(config, profile=profile)

    success_count = 0
    for tf in test_files:
        # compile() resolves the classpath itself. Passing it again as
        # extra_classpath duplicated every entry on the javac command line.
        success, error = compiler.compile(tf)
        if success:
            success_count += 1
            # ASCII only: ✓/✗ are not in the GBK console codepage and crash
            # on Windows when stdout is a real console.
            print(f"  [OK]   {tf.name}")
        else:
            print(f"  [FAIL] {tf.name}")
            print(f"    {error[:200]}")

    print(f"\n{success_count}/{len(test_files)} compile successfully")


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="testgen-agent — automatic JUnit 4/5 test generation agent",
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

    # Target framework — "auto" follows the project under test
    parser.add_argument(
        "--junit", default="auto", choices=["auto", "4", "5"],
        help="JUnit version to generate for: 'auto' (default) follows the "
             "project's test classpath; 4 or 5 forces it",
    )
    parser.add_argument(
        "--java", default="auto", choices=["auto", "8", "11", "17", "21"],
        help="Java version to compile the generated tests for: 'auto' "
             "(default) follows the project's pom/build file; an explicit "
             "value is passed to javac as -source/-target",
    )

    parser.add_argument(
        "--add-mock-deps", action="store_true",
        help="Write the Mockito test dependency into the target project's "
             "pom.xml so mock tests can compile. Off by default: the agent "
             "otherwise never modifies the project it is pointed at. "
             "Idempotent, and the original pom is backed up once.",
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
    parser.add_argument(
        "--max-tokens", type=int, default=8192,
        help="Max tokens per LLM response (default: 8192; Anthropic-family "
             "providers only). Raise it if generated tests come back "
             "truncated — the run log will say so explicitly.",
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
        default=["normal", "boundary", "exception", "path", "reflection",
                 "mock"],
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
    parser.add_argument(
        "--no-resume", action="store_true",
        help="Ignore the checkpoint and regenerate every test from scratch",
    )

    # Quality analysis
    parser.add_argument(
        "--no-mutation", action="store_true",
        help="Skip PiTest mutation-score analysis (slow; needs Maven)",
    )
    parser.add_argument(
        "--pitest-version", default="1.15.0",
        help="pitest-maven plugin version (default: 1.15.0)",
    )

    # Output
    parser.add_argument(
        "--output-dir",
        help="Test output directory (default: project's src/test/java)",
    )
    parser.add_argument(
        "--report-format", default="all",
        choices=["json", "csv", "both", "md", "all"],
        help="Report output format: md (human-readable), json, csv, "
             "both (json+csv), all (default: md+json+csv)",
    )
    parser.add_argument(
        "-v", "--verbose", action="store_true",
        help="Also echo debug logging to the console (the run log in "
             ".testgen-agent/run.log is always written)",
    )

    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv or sys.argv[1:])
    config = build_config(args)

    # analyze/repair never reach TestGeneratorAgent.run(), which sets this up,
    # so attach the run log here for every command. Idempotent.
    setup_logging(config.project_path, config.verbose)

    if args.command == "analyze":
        cmd_analyze(config)
    elif args.command == "generate":
        cmd_generate(config)
    elif args.command == "repair":
        cmd_repair(config)


if __name__ == "__main__":
    main()
