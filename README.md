<p align="right">
  <b>English</b> | <a href="README.zh-CN.md">简体中文</a>
</p>

# TestGen Agent
GitHub: https://github.com/u7465990/testgen-agent
**Automated JUnit 4 test generation for Java projects, powered by LLMs.**

```
pip install testgen-agent
testgen-agent analyze  ./my-project
testgen-agent generate ./my-project
```

TestGen Agent is a standalone Python tool that takes a Java project, discovers its methods, generates JUnit 4 unit tests using an LLM (OpenAI, Anthropic, or any Anthropic-compatible endpoint such as DeepSeek), compiles and repairs them, and measures how good the result actually is. It replaces a fragmented manual pipeline with a single autonomous agent.

> **Measuring the right thing.** Compilation success only proves a test file parses — an empty test class compiles perfectly. TestGen Agent therefore reports **mutation score** (PiTest) as its headline metric: the fraction of injected faults the generated tests actually catch.

> **Verification status:** the full pipeline has been **run end-to-end and verified** on the bundled `examples/demo-project` (see [Verified End-to-End Run](#verified-end-to-end-run)). Maven, Ant, Gradle, and manual project layouts are auto-detected by design; only the **Maven** path has been exercised in the demo verification so far.

## What you get

Everything lands in `<project>/.testgen-agent/` — deliberately **outside `target/`**,
because the coverage phase runs `mvn clean` and would otherwise delete it mid-run.

| Output | For | Contents |
|---|---|---|
| `report.md` | **humans** | Mutation score first, then the weakest classes and what needs a human |
| `report.json` | CI / tooling | Every metric, machine-readable |
| `report.csv` | spreadsheets | Per-test-file detail |
| `run.log` | **debugging** | The diagnostics the console swallows — javac errors, LLM retries, classpath resolution, per-phase timings |

Plus the generated tests themselves, written into the project's `src/test/java/`.

## Features

- **Java project discovery** — auto-detects Maven, Ant, Gradle, or manual project layouts
- **Intelligent method discovery** — parses source files to extract FQN, signature, modifiers, parameter types, exceptions, branch conditions, and class context
- **Fuzzing-inspired test targets** — generates Normal, Boundary, Exception, and Path targets per method, ensuring diverse test coverage
- **Multi-provider LLM support** — works with OpenAI (GPT-4o-mini), Anthropic (Claude), or any Anthropic-compatible endpoint via `ANTHROPIC_BASE_URL` (e.g. DeepSeek)
- **Self-healing compilation** — if generated tests fail to compile, the agent sends error diagnostics back to the LLM for automatic repair (up to 3 attempts)
- **Coverage-guided improvement** *(optional)* — runs tests with JaCoCo, identifies uncovered branches, and generates additional targeted tests
- **Test-quality measurement** — mutation score (PiTest), assertion density, and empty-test-class detection
- **Resumable** — an interrupted run resumes from a JSONL checkpoint instead of re-calling the LLM
- **Human-readable report** — a Markdown report is written on every run
- **Always-on run log** — every run writes `.testgen-agent/run.log`, including the diagnostics the console never shows (javac errors, LLM retries, classpath resolution)
- **Structured output** — Markdown, JSON, CSV, and console report
- **Claude Code skill** — install as `/generate-tests` in Claude Code

## Verified End-to-End Run

The pipeline was executed against `examples/demo-project`, a small Maven Java 8 library (4 classes: `Calculator`, `TextUtil`, `BankAccount`, `PasswordValidator` — covering arithmetic, string handling, stateful logic, exception branches, and private methods). The run used `deepseek-v4-flash` through DeepSeek's Anthropic-compatible endpoint.

| Metric | Result |
|--------|--------|
| Source files discovered | 4 |
| Methods extracted | 22 |
| Methods targeted | 20 |
| Test files generated | 40 |
| Compile pass rate | 40 / 40 (100%) |
| Tests executed via Maven surefire | 38 |
| Pass rate (runtime) | 36 / 38 (94.7%) |
| **Mutation score (PiTest)** | **60–67 / 80 (75–84%)** |
| Assertion density | 2.75–2.79 per `@Test` method |
| Empty test classes | 0–2 |

The mutation score is the number that matters: **75–84% of injected faults are caught** — on par with the human-written baseline of 83.98% reported in the ICST 2026 replication study.

> These are given as **ranges, not a single figure**, because every run regenerates the tests from scratch and the LLM does not produce the same output twice. Two measured runs on this project came out at 83.8% (67/80) and 75.0% (60/80). Quoting one run's number as *the* result would be exactly the kind of overclaiming this tool exists to avoid.

Per class (from the 83.8% run):

| Class | Mutation score |
|-------|----------------|
| `com.demo.TextUtil` | 100.0% (20/20) |
| `com.demo.PasswordValidator` | 79.2% (19/24) |
| `com.demo.Calculator` | 78.9% (15/19) |
| `com.demo.BankAccount` | 76.5% (13/17) |

**Honest caveats** — most of these are now *measured* rather than merely acknowledged, and they vary run to run:

- **0–2 of 40 generated files were empty test classes** (compiled but contained no `@Test` method). The compilation check does not catch this; the `empty_test_classes` metric does, and the agent now reports it.
- **2 of 38 executed tests failed** because the LLM misunderstood a class invariant (`BankAccount` forbids negative balances in its constructor, so an overdrawn state is unreachable through the public API — the generated `isOverdrawn` tests tried to construct one anyway). PiTest requires a green suite, so these are automatically excluded from mutation analysis and listed in the report.
- **5–12 of 80 mutants were never reached by any test** (`NO_COVERAGE`) — a coverage gap, not an assertion gap, and the report breaks it out separately.
- The demo runs used `--no-coverage`, so the coverage-guided phase (Phase B) was **not** exercised; it is implemented and was exercised in the underlying Defects4J experiments.

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

Tests are saved to `./my-java-project/src/test/java/`. Reports are written to `./my-java-project/.testgen-agent/` (`report.md`, `report.json`, `report.csv`).

> The report directory sits **outside `target/`** on purpose: the coverage phase runs `mvn clean`, which would otherwise delete the reports — and the resume checkpoint with them.

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
  --no-resume                     Ignore the checkpoint and regenerate everything

Quality:
  --no-mutation                   Skip PiTest mutation-score analysis (slow; needs Maven)
  --pitest-version VERSION        pitest-maven plugin version (default: 1.15.0)

Output:
  --output-dir DIR                Test output directory (default: src/test/java)
  --report-format {json,csv,both,md,all}
                                  Report format (default: all = md + json + csv)

Diagnostics:
  -v, --verbose                   Also echo debug logging to the console
```

## Debugging a run

The console is a progress display — it tells you *what* is running, not *why* it
failed. Every run also writes a debug log to `.testgen-agent/run.log`, which
records the things that are otherwise swallowed: the full javac error that gets
handed to the repair loop, LLM retries and their responses, and exactly what
ended up on the classpath.

```bash
# What actually went wrong with that failing test?
grep -A6 "FAILED (exit" .testgen-agent/run.log

# Console says:  [FAIL] BankAccount_deposit_Dbl_Test_Boundary_5.java
# Log says:      -> FAILED (exit 1)
#                ...:3: 错误: 找不到符号
#                import com.demo.BankAccount;
#                  符号:   类 BankAccount
#                  位置: 程序包 com.demo

# Per-phase timings (where did the time go?)
grep "since last phase" .testgen-agent/run.log

# Classpath resolution
grep -A8 "classpath resolved" .testgen-agent/run.log
```

Use `-v` to see the same output live on stderr. The log is rewritten on each run.

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
python main.py generate examples/demo-project \
  --provider anthropic --model deepseek-v4-flash --max-per-method 2 --no-coverage
cd examples/demo-project && mvn test   # uses `clean` if re-running
```

> No `mvn compile` first — the agent builds the project itself before generating
> anything, because `javac` cannot see the project's own classes otherwise. (An
> earlier version omitted this, and every test failed with `cannot find symbol`
> on any project that had not been pre-built. See fix 9 below.)

## How It Works

### Pipeline

```
Project Directory
  │
  ▼
[1] Project Analysis
  │  Detect build tool (Maven/Ant/Gradle/manual)
  │  Walk src/main/java for .java files
  │  Build the project if its classes are not there yet — javac
  │  cannot see the project's own types otherwise
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
[7] Final Verification
  │  Recompile every surviving test against the classpath
  │  Build per-method report
  ▼
[8] Test Quality
  │  Empty test classes (compiles but has no @Test)
  │  Assertion density (assertions per @Test method)
  │  Mutation score via PiTest — retries with failing
  │  test classes excluded, since PiTest needs a green suite
  ▼
Report
    Markdown + JSON + CSV + console summary
```

*\*Phase B requires Maven and JaCoCo to be configured in the target project*

### Prompt Templates

The agent uses two prompt templates adapted from the original assignment:

- **`generate_system.txt`** / **`generate_user.txt`** — Used for initial test generation. Defines persona (expert Java test developer), strict import restrictions, JUnit 4 rules, reflection rules, and output format.
- **`repair_system.txt`** / **`repair_user.txt`** — Used for compilation repair. Focuses on debugging error messages, fixing imports, handling reflection, and preserving test structure.

Branch conditions extracted from source code replace the Jimple IR used in earlier approaches, eliminating the need for SootUp while preserving the LLM's visibility into control flow.

### Project Layout

~3,800 lines of Python across 19 modules — all at the repo root.

```
agent.py             566  TestGeneratorAgent — the 8-phase orchestrator
repair_loop.py       413  Compilation repair loop + coverage improvement
report_generator.py  401  Markdown / JSON / CSV / console output
java_analyzer.py     312  Project discovery, build-tool detection, classpath
main.py              277  CLI entry point
quality_analyzer.py  251  Empty classes, assertion density, PiTest parsing
coverage_analyzer.py 235  JaCoCo XML parsing
compiler.py          222  javac invocation + project build
target_generator.py  212  Normal / Boundary / Exception / Path / Reflection targets
test_writer.py       186  Test formatting, naming, file I/O
method_extractor.py  166  javalang-based method extraction
llm_client.py        104  Unified OpenAI + Anthropic/DeepSeek client
skill_entry.py        96  Legacy CLI wrapper (see the skill note above)
runlog.py             93  Run logging (.testgen-agent/run.log)
config.py             87  AgentConfig dataclass
prompt_manager.py     80  Prompt template loading + substitution
checkpoint.py         60  JSONL resume support
extractor/                Pluggable extraction backends (javalang, opt-in SootUp)
prompts/                  Four prompt templates (generate/repair × system/user)
examples/demo-project/    Verified end-to-end demo (Maven, Java 8, 4 classes)
references/               Skill definition draft
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
  ---------------------------------------------------
  Test methods:     38
  Assertion density: 2.79 per test
  Empty test classes: 2 (compile, but contain no @Test)
  Mutation score:   83.8% (67/80 mutants killed)
    (5 mutants were never even reached by a test)
    (2 test class(es) excluded — they fail before mutation)
  Duration:       491.2s
───────────────────────────────────────────────────────

  Weakest classes (mutation score):
  com.demo.BankAccount                            76.5%  (13/17)
  com.demo.Calculator                             78.9%  (15/19)
  com.demo.PasswordValidator                      79.2%  (19/24)
  com.demo.TextUtil                              100.0%  (20/20)

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

### Markdown Report (`.testgen-agent/report.md`)

The human-facing artifact — written on every run, safe to commit or paste into a review. Mutation score leads:

```markdown
# TestGen Agent 报告 — demo-project

> 生成于 2026-10-09 13:40 · 耗时 491.2s · 构建工具 `maven`

## 核心指标
| 指标 | 值 |
|---|---|
| **Mutation score** | **83.8%** (67/80 mutants killed) |
| 编译通过率 | 100.0% (40/40) |
| 可运行率 | 95.0% (38/40) |
| 断言密度 | 2.79 / 测试 |
| 空测试类 | 2 |

**结论：良好 —— 与人工撰写测试的典型水平（约 80–85%）相当。**

## 最弱的类
| 类 | Mutation score | Killed |
|---|---|---|
| `com.demo.BankAccount` | 76.5% | 13/17 |
| `com.demo.Calculator` | 78.9% | 15/19 |

## 需要人工介入
**2 个测试运行时失败**（已排除出 mutation 分析，PiTest 要求测试全绿）:
- `com.demo.BankAccount_isOverdrawn_Test_Normal_8`
```

The report ends with the exact command that reproduces the run.

### JSON Report (`.testgen-agent/report.json`)

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
  "total_test_methods": 38,
  "empty_test_classes": 2,
  "empty_test_class_names": [
    "PasswordValidator_hasDigit_Str_Test_Boundary_29",
    "PasswordValidator_strength_Str_Test_Normal_30"
  ],
  "assertion_density": 2.789473684210526,
  "mutation_score": 0.8375,
  "mutations_killed": 67,
  "mutations_total": 80,
  "mutations_no_coverage": 5,
  "mutations_excluded_tests": [
    "com.demo.BankAccount_isOverdrawn_Test_Normal_8",
    "com.demo.BankAccount_isOverdrawn_Test_Path_9"
  ],
  "mutation_by_class": [
    { "name": "com.demo.TextUtil", "killed": 20, "total": 20, "score": 1.0 }
  ],
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

> `branch_coverage` / `line_coverage` are populated only when the coverage phase (Phase B) runs (without `--no-coverage`). `mutation_score` is `null` when mutation analysis was skipped or unavailable.

### CSV Report (`.testgen-agent/report.csv`)

Columns: `Project`, `FQN`, `Signature`, `SourceCode`, `BranchConditions`, `ClassContext`, `AllowedImports`, `ThrowsExceptions`, `Modifiers`, `GenerationTarget`, `GeneratedCode`, `CodeAfterFormatting`, `SavedPath`, `Runnable`

## Claude Code Skill

A working skill definition is in
[`references/skill-draft-SKILL.md`](references/skill-draft-SKILL.md). Copy it into
place and fill in this repo's absolute path:

```bash
mkdir -p .claude/skills/generate-tests
cp references/skill-draft-SKILL.md .claude/skills/generate-tests/SKILL.md
# then replace <REPO> in that file with the absolute path to this repo
```

Start a new Claude Code session and:

```
/generate-tests examples/demo-project
```

Claude reads the skill, runs the pipeline, reads `report.json`, and reports —
including *why* any tests failed to compile, not just the counts.

> **Note on `skill.yaml`.** An earlier version of this repo shipped a `skill.yaml`
> containing a `command:` template and an `arguments:` schema, and the README told
> you to run `claude add skill ./agent/skill.yaml`. None of that is how Claude Code
> skills work: a skill is a `SKILL.md` with `name`/`description` frontmatter plus a
> Markdown body of instructions — there is no parameter-templating engine, and
> `claude add skill` is not a real command. As shipped, that skill never loaded.
> `skill.yaml` and `skill_entry.py` are kept only as a historical CLI wrapper;
> the definition above supersedes them.

## Requirements

- **Java 8+** (for compiling generated tests — the project under test must target Java 8)
- **Python 3.10+**
- **Javac** — must be on `PATH` or `JAVA_HOME` set
- **Maven** *(optional)* — needed for classpath resolution, coverage (Phase B), and mutation analysis (Phase 8). Mutation analysis additionally needs **JDK 11+** to run PiTest.
- **API Key** — OpenAI (`OPENAI_API_KEY`) or Anthropic (`ANTHROPIC_API_KEY` / `ANTHROPIC_AUTH_TOKEN` + `ANTHROPIC_BASE_URL`)

On Windows, `javac` resolution requires `JAVA_HOME` to point to a JDK (not JRE), and the agent invokes `mvn.cmd` through `cmd /c` automatically.

## Limitations

- Generated tests are **JUnit 4**, Java 8 compatible — no JUnit 5, no lambdas, no Java 8+ APIs
- **No mocking.** The prompt forbids Mockito, so classes with injected dependencies (services, repositories) generally cannot produce runnable tests. This is the single biggest gap for real-world projects.
- Generated test files use the naming convention `ClassName_method_ParamType_Test_Type_N`. Maven projects must configure surefire's `<includes>` (e.g. `**/*_Test_*.java`) for them to be executed — see `examples/demo-project/pom.xml`.
- Branch conditions are extracted from **source code** rather than Jimple IR (may miss compiler-generated branches)
- Phase B (coverage improvement) requires **Maven + JaCoCo** configured in the target project
- Mutation analysis (Phase 8) requires **Maven** and a **JDK 11+** to run PiTest — it needs `pitest-maven`, resolved on demand and pinned via `--pitest-version`. PiTest also refuses to run unless the test suite is green; failing test classes are automatically excluded and listed in the report.
- Compiled-but-empty test classes are reported but **not** automatically regenerated
- Large projects with hundreds of methods may take significant time and API tokens (single-threaded today)

## Verified Fixes

Bugs found and fixed by actually running the pipeline on `examples/demo-project`:

1. **Windows Maven resolution** — `mvn` is `mvn.cmd` on Windows and subprocess couldn't find it; classpath silently resolved empty. Fixed with `shutil.which` + `cmd /c`.
2. **Test-scope dependencies missing** — `mvn dependency:build-classpath` excludes test-scope by default, so JUnit was never on the compile classpath. Fixed by passing `-Dmdep.includeScope=test`.
3. **Anthropic `ThinkingBlock` handling** — DeepSeek returns a thinking block before the text block; the client crashed on `content[0].text`. Fixed by concatenating only `type == "text"` blocks.
4. **`--max-per-method` ignored** — `target_generator.py` hard-coded `targets[:10]`. Now the configured cap is respected.
5. **Surefire naming mismatch** — generated test files didn't match surefire's default `*Test.java` include pattern, so `mvn test` ran 0 tests. Documented in the demo `pom.xml`.
6. **Checkpoint and reports lived inside `target/`** — the coverage phase runs `mvn clean`, which deleted the resume checkpoint and every report mid-run. Moved to `.testgen-agent/` at the project root, with an automatic migration of any legacy checkpoint.
7. **PiTest requires a green suite** — it aborts with "did not pass without mutation" if any test fails, so a single failing generated test blocked the whole mutation phase. The agent now parses the offending test classes out of PiTest's output, excludes them, and retries — recording the exclusions in the report.
8. **Compilation-only reporting was self-refuting** — the headline metric was "100% compile rate", but an empty test class compiles too. Mutation score, assertion density, and empty-class detection were added as Phase 8.
9. **The pipeline never built the project** — `resolve_classpath()` only adds `target/classes` when it already exists, so on a project that had not been pre-built every generated test failed with `cannot find symbol`. A clean-copy run scored a 45% compile rate (18/40) and took 7x longer, because the repair loop burned 3 LLM attempts per test. It stayed hidden because these instructions told you to run `mvn -q compile` first. `JavaCompiler.ensure_project_built()` now builds before generating.
10. **`main.py repair` crashed on every invocation** — it used `JavaProjectAnalyzer` without importing it, and printed a checkmark/cross that raise `UnicodeEncodeError` on a GBK console. It had never worked on Windows.
11. **Diagnostics were invisible** — the javac error is handed to the repair loop and never printed, so a failing test showed only `[FAIL] <file>`. Every run now writes `.testgen-agent/run.log` with the full javac error, LLM retries, and classpath resolution. That log is what surfaced the classpath-deduplication and command-line-bloat issues fixed alongside it.

## License

MIT
