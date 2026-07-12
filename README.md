# TestGen Agent

**Automated JUnit 4 test generation for any Java project, powered by LLMs.**

```
pip install testgen-agent
testgen-agent analyze  ./my-project
testgen-agent generate ./my-project
```

TestGen Agent is a standalone Python tool that takes any Java project, discovers its methods, generates JUnit 4 unit tests using an LLM (OpenAI or Anthropic), compiles and repairs them, and outputs a structured report. It replaces a fragmented manual pipeline with a single autonomous agent.

## Features

- **Any Java project** — auto-detects Maven, Ant, Gradle, or manual project layouts
- **Intelligent method discovery** — parses source files to extract FQN, signature, modifiers, parameter types, exceptions, branch conditions, and class context
- **Fuzzing-inspired test targets** — generates Normal, Boundary, Exception, and Path targets per method, ensuring diverse test coverage
- **Multi-provider LLM support** — works with OpenAI (GPT-4o-mini) or Anthropic (Claude)
- **Self-healing compilation** — if generated tests fail to compile, the agent sends error diagnostics back to the LLM for automatic repair (up to 3 attempts)
- **Coverage-guided improvement** *(optional)* — runs tests with JaCoCo, identifies uncovered branches, and generates additional targeted tests
- **Structured output** — JSON summary, CSV data, and console report
- **Claude Code skill** — install as `/generate-tests` in Claude Code

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
```

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

# Skip private methods, only normal + boundary targets
testgen-agent generate ./my-project --skip-private --target-types normal boundary

# Export report as CSV only
testgen-agent generate ./my-project --report-format csv

# Verbose output
testgen-agent generate ./my-project -v
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
├── llm_client.py            Unified OpenAI + Anthropic client
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
└── skill.yaml               Claude Code skill manifest
```

## Output

### Console

```
───────────────────────────────────────────────────────
  Test Generation Agent — Summary
───────────────────────────────────────────────────────
  Project:        /home/user/my-java-project
  Build tool:     maven
  Source files:   12
  Methods found:  48
  Methods targeted: 42
  Tests generated:   98
  Tests compiled:    92
  Compilation rate: 93.9%
  Duration:       142.3s
───────────────────────────────────────────────────────

  Per-method breakdown:
  Method                                              Gen  Cmp  Run
  ────────────────────────────────────────────────── ──── ──── ────
  org.example.service.UserService.findUser(Str,int)    4    4    4
  org.example.service.UserService.deleteUser(Str)      3    2    2
  ...
```

### JSON Report (`target/testgen-agent/report.json`)

```json
{
  "project_path": "/home/user/my-java-project",
  "tests_generated": 98,
  "tests_compiled": 92,
  "tests_runnable": 92,
  "compilation_rate": 0.939,
  "method_reports": [
    {
      "fqn": "org.example.service.UserService.findUser(String,int)",
      "tests_generated": 4,
      "tests_compiled": 4,
      "tests_runnable": 4
    }
  ]
}
```

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
- **API Key** — OpenAI (`OPENAI_API_KEY`) or Anthropic (`ANTHROPIC_API_KEY`)

On Windows, `javac` resolution requires `JAVA_HOME` to point to a JDK (not JRE).

## Limitations

- Generated tests are **JUnit 4**, Java 8 compatible — no JUnit 5, no lambdas, no Java 8+ APIs
- Branch conditions are extracted from **source code** rather than Jimple IR (may miss compiler-generated branches)
- Phase B (coverage improvement) requires **Maven + JaCoCo** configured in the target project
- Large projects with hundreds of methods may take significant time and API tokens

## License

MIT
