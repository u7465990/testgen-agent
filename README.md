# TestGen Agent
GitHub：https://github.com/u7465990/testgen-agent
**Automated JUnit 4 test generation for Java projects, powered by LLMs.**

```
pip install testgen-agent
testgen-agent analyze  ./my-project
testgen-agent generate ./my-project
```

TestGen Agent is a standalone Python tool that takes a Java project, discovers its methods, generates JUnit 4 unit tests using an LLM (OpenAI, Anthropic, or any Anthropic-compatible endpoint such as DeepSeek), compiles and repairs them, and outputs a structured report. It replaces a fragmented manual pipeline with a single autonomous agent.

> **Verification status:** the full pipeline has been **run end-to-end and verified** on the bundled `examples/demo-project` (see [Verified End-to-End Run](#verified-end-to-end-run)). Maven, Ant, Gradle, and manual project layouts are auto-detected by design; only the **Maven** path has been exercised in the demo verification so far.

## Features

- **Java project discovery** — auto-detects Maven, Ant, Gradle, or manual project layouts
- **Intelligent method discovery** — parses source files to extract FQN, signature, modifiers, parameter types, exceptions, branch conditions, and class context
- **Fuzzing-inspired test targets** — generates Normal, Boundary, Exception, and Path targets per method, ensuring diverse test coverage
- **Multi-provider LLM support** — works with OpenAI (GPT-4o-mini), Anthropic (Claude), or any Anthropic-compatible endpoint via `ANTHROPIC_BASE_URL` (e.g. DeepSeek)
- **Self-healing compilation** — if generated tests fail to compile, the agent sends error diagnostics back to the LLM for automatic repair (up to 3 attempts)
- **Coverage-guided improvement** *(optional)* — runs tests with JaCoCo, identifies uncovered branches, and generates additional targeted tests
- **Structured output** — JSON summary, CSV data, and console report
- **Claude Code skill** — install as `/generate-tests` in Claude Code

## Verified End-to-End Run

The pipeline was executed against `examples/demo-project`, a small Maven Java 8 library (4 classes: `Calculator`, `TextUtil`, `BankAccount`, `PasswordValidator` — covering arithmetic, string handling, stateful logic, exception branches, and private methods). The run used `deepseek-v4-flash` through DeepSeek's Anthropic-compatible endpoint.

| Metric | Result |
|--------|--------|
| Source files discovered | 4 |
| Methods extracted | 22 |
| Methods targeted | 20 |
| Test files generated | 40 |
| **Compile pass rate** | **40 / 40 (100%)** |
| Tests executed via Maven surefire | 38 |
| **Pass rate (runtime)** | **36 / 38 (94.7%)** |

**Honest caveats observed during the run:**

- **2 of 40 generated files were empty test classes** (compiled but contained no `@Test` method) — the compilation check alone does not catch this.
- **2 of 38 executed tests failed** because the LLM misunderstood a class invariant (`BankAccount` forbids negative balances in its constructor, so an overdrawn state is unreachable through the public API — the generated `isOverdrawn` tests tried to construct one anyway).
- The demo run used `--no-coverage`, so the coverage-guided phase (Phase B) was **not** exercised in this run; it is implemented and was exercised in the underlying Defects4J experiments.

Run artifacts (report.json / report.csv / surefire results / generated tests) are in the repo for inspection. See the [demo README](examples/demo-project/README.md) for reproduction steps.

## Quick Start

### Installation

```bash
pip install javalang openai anthropic pyyaml
```

### Set up API Key

```bash
# OpenAI (default)
export OPENAI_API_KEY="sk-..."

# Or Anthropic
export ANTHROPIC_API_KEY="sk-ant-..."

# Or any Anthropic-compatible endpoint (e.g. DeepSeek)
export ANTHROPIC_BASE_URL="https://api.deepseek.com/anthropic"
export ANTHROPIC_AUTH_TOKEN="sk-..."
```

The agent reads `ANTHROPIC_BASE_URL` and falls back to `ANTHROPIC_AUTH_TOKEN` when `ANTHROPIC_API_KEY` is unset, so DeepSeek and other Anthropic-compatible providers work out of the box.

### Analyze a Project

See what methods the agent would target without generating any tests:

```bash
testgen-agent analyze ./my-java-project
```

### Generate Tests

Run the full pipeline: discover → extract → generate → repair → report:

```bash
testgen-agent generate ./my-java-project
```

Tests are saved to `./my-java-project/src/test/java/`. A report is written to `./my-java-project/target/testgen-agent/report.json`.

## Usage

### Commands

| Command | Description |
|---------|-------------|
| `analyze <path>` | Discover and display methods (no generation) |
| `generate <path>` | Full pipeline: discover → extract → generate → repair → report |
| `repair <path>` | Re-compile existing `_Test_*.java` files and report status |

### Options

```
LLM:
  --provider {openai,anthropic}   LLM provider (default: openai)
  --model MODEL                   Model name (default: gpt-4o-mini)
  --api-key KEY                   API key (default: reads env var)
  --temperature TEMP              LLM temperature (default: 0.2)

Method filtering:
  --package PACKAGE               Only target this package (repeatable)
  --exclude METHOD                Exclude method by name (repeatable)
  --skip-private                  Skip private methods
  --include-constructors          Include constructors as targets
  --target-types [NORMAL ...]     Target types to generate (default: all)

Repair:
  --max-repair N                  Max compilation repair attempts (default: 3)
  --no-coverage                   Skip coverage-guided improvement

Output:
  --output-dir DIR                Test output directory (default: src/test/java)
  --report-format {json,csv,both} Report format (default: both)
```

### Examples

```bash
# Quick analysis of a project
testgen-agent analyze ./my-project

# Generate tests for a specific package only
testgen-agent generate ./my-project --package org.example.service

# Use Anthropic Claude
testgen-agent generate ./my-project --provider anthropic --model claude-sonnet-4-20250514

# Use DeepSeek (Anthropic-compatible endpoint)
testgen-agent generate ./my-project --provider anthropic --model deepseek-v4-flash

# Skip private methods, only normal + boundary targets
testgen-agent generate ./my-project --skip-private --target-types normal boundary

# Export report as CSV only
testgen-agent generate ./my-project --report-format csv

# Verbose output
testgen-agent generate ./my-project -v

# Reproduce the verified demo run (bundled example project)
cd examples/demo-project && mvn -q compile
cd ../.. && python main.py generate examples/demo-project \
  --provider anthropic --model deepseek-v4-flash --max-per-method 2 --no-coverage
cd examples/demo-project && mvn test
```

## How It Works

### Pipeline

```
Project Directory
  │
  ▼
[1] Project Analysis
  │  Detect build tool (Maven/Ant/Gradle/manual)
  │  Walk src/main/java for .java files
  │  Resolve classpath
  ▼
[2] Method Extraction
  │  Parse each source file with javalang
  │  Extract: FQN, signature, modifiers,
  │  params, exceptions, branch conditions,
  │  class context, allowed imports
  ▼
[3] Target Generation
  │  For each method:
  │    Normal  → 1 target (valid inputs)
  │    Boundary → N targets (null, 0, -1, etc.)
  │    Exception→ 1 target per declared exception
  │    Path    → 2 targets per branch (true/false)
  ▼
[4] LLM Test Generation
  │  Fill prompt template with method context + target
  │  Call GPT-4o-mini or Claude
  │  Extract Java code from response
  │  Format: unique class name, correct package,
  │  deduplicated imports
  ▼
[5] Compilation Repair (Phase A)
  │  Compile with javac against project classpath
  │  If fail → send error + code to LLM → fix → retry
  │  Up to 3 attempts per test
  ▼
[6] Coverage Improvement (Phase B)*
  │  Run mvn test with JaCoCo
  │  Find uncovered branches
  │  Generate [MissingBranch] targets
  │  → Repeat until all methods meet threshold
  ▼
[7] Report
    JSON + CSV + console summary
```

*\*Phase B requires Maven and JaCoCo to be configured in the target project*

### Prompt Templates

The agent uses two prompt templates adapted from the original assignment:

- **`generate_system.txt`** / **`generate_user.txt`** — Used for initial test generation. Defines persona (expert Java test developer), strict import restrictions, JUnit 4 rules, reflection rules, and output format.
- **`repair_system.txt`** / **`repair_user.txt`** — Used for compilation repair. Focuses on debugging error messages, fixing imports, handling reflection, and preserving test structure.

Branch conditions extracted from source code replace the Jimple IR used in earlier approaches, eliminating the need for SootUp while preserving the LLM's visibility into control flow.

### Project Layout

```
agent/
├── main.py                  CLI entry point
├── config.py                AgentConfig dataclass
├── agent.py                 TestGeneratorAgent orchestrator
├── java_analyzer.py         Project discovery (build tool, sources, classpath)
├── method_extractor.py      javalang-based method extraction
├── target_generator.py      Rule-based target generation
├── prompt_manager.py        Prompt template loading + substitution
├── llm_client.py            Unified OpenAI + Anthropic/DeepSeek client
├── test_writer.py           Test formatting, naming, file I/O
├── compiler.py              javac invocation + classpath resolution
├── repair_loop.py           LLM-based compilation repair + coverage loop
├── coverage_analyzer.py     JaCoCo XML parsing
├── report_generator.py      JSON + CSV + console output
├── skill_entry.py           Claude Code skill bridge
├── prompts/
│   ├── generate_system.txt
│   ├── generate_user.txt
│   ├── repair_system.txt
│   └── repair_user.txt
├── examples/
│   └── demo-project/        Verified end-to-end demo (Maven, Java 8)
└── skill.yaml               Claude Code skill manifest
```

## Output

### Console (real output from the demo run)

```
───────────────────────────────────────────────────────
  Test Generation Agent — Summary
───────────────────────────────────────────────────────
  Project:        examples\demo-project
  Build tool:     maven
  Source files:   4
  Methods found:  22
  Methods targeted: 20
  Tests generated:   40
  Tests compiled:    40
  Compilation rate: 100.0%
  Duration:       491.2s
───────────────────────────────────────────────────────

  Per-method breakdown:
  Method                                              Gen  Cmp  Run
  ────────────────────────────────────────────────── ──── ──── ────
  com.demo.BankAccount.getBalance()                     2    2    2
  com.demo.BankAccount.deposit(double)                  2    2    2
  com.demo.Calculator.divide(int,int)                   2    2    2
  com.demo.PasswordValidator.isValid(String)            2    2    2
  com.demo.TextUtil.truncate(String,int)                2    2    2
  ... (20 methods, all compiled & runnable)
```

### JSON Report (`target/testgen-agent/report.json`)

```json
{
  "project_path": "examples\\demo-project",
  "build_tool": "maven",
  "source_files_found": 4,
  "methods_found": 22,
  "methods_targeted": 20,
  "tests_generated": 40,
  "tests_compiled": 40,
  "tests_runnable": 40,
  "compilation_rate": 1.0,
  "branch_coverage": null,
  "line_coverage": null,
  "method_reports": [
    {
      "fqn": "com.demo.BankAccount.getBalance()",
      "signature": "double getBalance()",
      "modifiers": "public",
      "tests_generated": 2,
      "tests_compiled": 2,
      "tests_runnable": 2
    }
  ]
}
```

> `branch_coverage` / `line_coverage` are populated only when the coverage phase (Phase B) runs (without `--no-coverage`).

### CSV Report (`target/testgen-agent/report.csv`)

Columns: `Project`, `FQN`, `Signature`, `SourceCode`, `BranchConditions`, `ClassContext`, `AllowedImports`, `ThrowsExceptions`, `Modifiers`, `GenerationTarget`, `GeneratedCode`, `CodeAfterFormatting`, `SavedPath`, `Runnable`

## Claude Code Skill

Install as a skill to use from within Claude Code:

```bash
claude add skill ./agent/skill.yaml
```

Then in any Claude session:

```
/generate-tests --project-path /path/to/project
```

Claude will run the agent, interpret the results, and present a summary.

## Requirements

- **Java 8+** (for compiling generated tests — the project under test must target Java 8)
- **Python 3.10+**
- **Javac** — must be on `PATH` or `JAVA_HOME` set
- **Maven** *(optional)* — only needed for classpath resolution and coverage
- **API Key** — OpenAI (`OPENAI_API_KEY`) or Anthropic (`ANTHROPIC_API_KEY` / `ANTHROPIC_AUTH_TOKEN` + `ANTHROPIC_BASE_URL`)

On Windows, `javac` resolution requires `JAVA_HOME` to point to a JDK (not JRE), and the agent invokes `mvn.cmd` through `cmd /c` automatically.

## Limitations

- Generated tests are **JUnit 4**, Java 8 compatible — no JUnit 5, no lambdas, no Java 8+ APIs
- Generated test files use the naming convention `ClassName_method_ParamType_Test_Type_N`. Maven projects must configure surefire's `<includes>` (e.g. `**/*_Test_*.java`) for them to be executed — see `examples/demo-project/pom.xml`.
- Branch conditions are extracted from **source code** rather than Jimple IR (may miss compiler-generated branches)
- Phase B (coverage improvement) requires **Maven + JaCoCo** configured in the target project
- Large projects with hundreds of methods may take significant time and API tokens

## Verified Fixes

Bugs found and fixed by actually running the pipeline on `examples/demo-project`:

1. **Windows Maven resolution** — `mvn` is `mvn.cmd` on Windows and subprocess couldn't find it; classpath silently resolved empty. Fixed with `shutil.which` + `cmd /c`.
2. **Test-scope dependencies missing** — `mvn dependency:build-classpath` excludes test-scope by default, so JUnit was never on the compile classpath. Fixed by passing `-Dmdep.includeScope=test`.
3. **Anthropic `ThinkingBlock` handling** — DeepSeek returns a thinking block before the text block; the client crashed on `content[0].text`. Fixed by concatenating only `type == "text"` blocks.
4. **`--max-per-method` ignored** — `target_generator.py` hard-coded `targets[:10]`. Now the configured cap is respected.
5. **Surefire naming mismatch** — generated test files didn't match surefire's default `*Test.java` include pattern, so `mvn test` ran 0 tests. Documented in the demo `pom.xml`.

## License

MIT
