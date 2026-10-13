# TestGen Agent
GitHub: https://github.com/u7465990/testgen-agent

**Automated JUnit 4/5 test generation for Java projects, powered by LLMs.**

```bash
pip install testgen-agent
testgen-agent analyze  ./my-project
testgen-agent generate ./my-project
```

TestGen Agent takes a Java project, discovers its methods, generates JUnit unit tests with an LLM (OpenAI, Anthropic, or any Anthropic-compatible endpoint such as DeepSeek), compiles and repairs them, and measures how good the result actually is.

**It follows the project it is pointed at.** The JUnit version (4 or 5) and the target Java level are auto-detected — from the build file and the project's resolved test classpath — so the same agent emits `org.junit.Assert` for a JUnit 4 codebase and `assertThrows(..., () -> ...)` for a JUnit 5 one. `--junit {auto,4,5}` and `--java {auto,8,11,17,21}` override detection when you want to.

**It measures the right thing.** Compilation success only proves a file parses — an empty test class compiles perfectly. TestGen Agent therefore reports **mutation score** (PiTest) as its headline metric: the fraction of injected faults the generated tests actually catch.

## Verified results

Run end-to-end on both bundled demos with `deepseek-v4-flash` through DeepSeek's Anthropic-compatible endpoint. Every run regenerates the tests and the LLM does not repeat itself, so these are given as **ranges across two measured runs**, not a single pinned figure — pinning one number is the overclaiming this tool exists to avoid.

| | `demo-project`<br>JUnit 4 / Java 8 | `demo-project-junit5`<br>JUnit 5 / Java 17 |
|---|---|---|
| Methods found / targeted | 22 / 20 | 22 / 20 |
| Test files generated | 40 | 40 |
| Compile rate | 100% (40/40) | 100% (40/40) |
| Tests executed (surefire) | 38 | 40 |
| Runtime pass rate | 94.7% (36/38) | 100% |
| **Mutation score (PiTest)** | **75–84% (60–67 / 80)** | **76–86% (61–69 / 80)** |
| Assertion density | 2.75–2.79 per `@Test` | 2.83 per `@Test` |
| Empty test classes | 0–2 | 0 |

The mutation score is the number that matters, and 75–86% of injected faults caught is on par with the human-written baseline (83.98%) reported in the ICST 2026 replication study.

The comparison between the two columns is the point: one agent, two projects, and it writes `try`/`catch` + `org.junit.Assert` for the Java 8 one and idiomatic lambdas for the Java 17 one:

```java
IllegalArgumentException ex = Assertions.assertThrows(
        IllegalArgumentException.class,
        () -> account.deposit(0.0));
Assertions.assertEquals("Deposit must be positive", ex.getMessage());
```

**Honest caveats** — most are *measured* rather than merely acknowledged, and they vary run to run:

- **0–2 of 40 files were empty test classes** (compiled, but contained no `@Test`). The compile check does not catch this; the `empty_test_classes` metric does, and the report names them.
- **2 of 38 executed tests failed** on the JUnit 4 demo because the LLM missed a class invariant: `BankAccount` forbids negative balances, so an overdrawn state is unreachable through the public API and the generated `isOverdrawn` tests tried to build one anyway. PiTest needs a green suite, so such classes are excluded from mutation analysis automatically and listed in the report.
- **5–12 of 80 mutants were never reached by any test** (`NO_COVERAGE`) — a coverage gap, not an assertion gap. Reported separately.
- The demo runs used `--no-coverage`, so Phase B (coverage-guided improvement) was **not** exercised there; it is implemented and was exercised in the underlying Defects4J experiments.
- Maven, Ant, Gradle and manual layouts are auto-detected by design, but only the **Maven** path has been exercised in the demo verification.

Artifacts (`report.json`, `report.csv`, surefire output, the generated tests) are checked in under `examples/`. See the [demo README](examples/demo-project/README.md) for reproduction steps.

> **On the first published JUnit 5 number.** An earlier revision of this README quoted a single 82.5%. That measurement was real but taken while a wiring bug fed the *generate* prompt JUnit 4 rules (`"Do NOT use assertThrows()"`) while the target text asked for JUnit 5 — contradictory instructions that produced zero `assertThrows` and one anonymous `new Executable() { ... }`. Fixing the wiring (`agent.py` was not passing the detected framework to `render_generate_prompt`) changed the output to idiomatic lambdas and the scores above. It had been masked because the *repair* prompt did receive the framework correctly, so only first-pass generation was wrong.

## Install

```bash
git clone https://github.com/u7465990/testgen-agent
cd testgen-agent
pip install .
```

That installs the `testgen-agent` command. `pip install -r requirements.txt` plus `python main.py` from the clone is equivalent.

### Docker (no local JDK or Maven)

The agent drives `javac` and `mvn`, so running it natively means a JDK on `JAVA_HOME` (a JDK, not a JRE) plus Maven. The bundled image pins both:

```bash
docker build -t testgen-agent .

docker run --rm \
  -v "$PWD/my-java-project:/work" \
  -e ANTHROPIC_BASE_URL -e ANTHROPIC_AUTH_TOKEN \
  testgen-agent generate /work
```

`analyze` and `repair` work the same way. Mount a named volume at `/home/testgen/.m2` if you want Maven's dependency cache to survive across runs. On Linux, build with `--build-arg UID=$(id -u) --build-arg GID=$(id -g)` so the files written into your project belong to you.

> **The container is not a sandbox.** It runs `mvn` against whatever you mount, and Maven executes the plugins that project's `pom.xml` declares — equivalent to running the tool natively. The agent writes into the mount (generated tests, `target/`, `.testgen-agent/`, and `pom.xml` under `--add-mock-deps`), so mount a copy if you want the original untouched.

### API keys

```bash
# OpenAI — the default provider
export OPENAI_API_KEY="sk-..."

# Anthropic
export ANTHROPIC_API_KEY="sk-ant-..."

# Any Anthropic-compatible endpoint, e.g. DeepSeek
export ANTHROPIC_BASE_URL="https://api.deepseek.com/anthropic"
export ANTHROPIC_AUTH_TOKEN="sk-..."
```

`ANTHROPIC_API_KEY` falls back to `ANTHROPIC_AUTH_TOKEN`, so DeepSeek and other Anthropic-compatible providers work out of the box.

## Usage

| Command | Description |
|---------|-------------|
| `analyze <path>` | Discover and display methods — no generation, no LLM calls |
| `generate <path>` | Full pipeline: discover → extract → generate → repair → report |
| `repair <path>` | Re-compile existing `_Test_*.java` files and report their status |

Running `analyze` first shows what would be targeted before you spend any tokens.

Generated tests go to `<project>/src/test/java/`; reports to `<project>/.testgen-agent/` — deliberately **outside `target/`**, because the coverage phase runs `mvn clean` and would otherwise delete the reports and the resume checkpoint mid-run.

### What it does

- **Resumable** — an interrupted `generate` resumes from a JSONL checkpoint instead of re-calling the LLM.
- **Self-healing compilation** — compile errors are fed back to the LLM for repair, up to `--max-repair` attempts per test.
- **Coverage-guided improvement** *(optional)* — JaCoCo finds uncovered branches, and `[MissingBranch]` tests are generated for them.
- **Multi-provider** — OpenAI (GPT-4o-mini by default), Anthropic, or any Anthropic-compatible endpoint.
- **Structured output** — Markdown, JSON, CSV, console, plus an always-on run log.
- **Claude Code skill** — install as `/generate-tests` (see below).

### Options

```
LLM:
  --provider {openai,anthropic}  Provider (default: openai)
  --model MODEL                  Model name (default: gpt-4o-mini)
  --api-key KEY                  Overrides the env var
  --temperature TEMP             Default 0.2

Framework:
  --junit {auto,4,5}             Default auto = follow the project's test classpath
  --java {auto,8,11,17,21}       Default auto = follow the project's build file
  --add-mock-deps                Write the Mockito test dependency into the target
                                 pom.xml — the only flag that modifies the project

Methods:
  --package PACKAGE              Only this package (repeatable, a package not a class)
  --exclude METHOD               Exclude by method name (repeatable)
  --skip-private                 Skip private methods
  --include-constructors         Target constructors too (off by default)
  --target-types [NORMAL ...]    normal boundary exception path reflection
  --max-per-method N             Per-method target cap (default 10)

Repair / coverage:
  --max-repair N                 Compile-repair attempts per test (default 3)
  --no-coverage                  Skip Phase B
  --no-resume                    Ignore the checkpoint and regenerate everything

Quality:
  --no-mutation                  Skip PiTest (slow; needs Maven)
  --pitest-version VERSION       pitest-maven version (default 1.15.0)

Output:
  --output-dir DIR               Default src/test/java
  --report-format {json,csv,both,md,all}
                                 Default all = md + json + csv

Diagnostics:
  -v, --verbose                  Also echo debug logging to the console
```

### Examples

```bash
# One package only
testgen-agent generate ./my-project --package org.example.service

# Anthropic Claude, or DeepSeek over its Anthropic-compatible endpoint
testgen-agent generate ./my-project --provider anthropic --model claude-sonnet-4-20250514
testgen-agent generate ./my-project --provider anthropic --model deepseek-v4-flash

# Skip private methods, generate only normal + boundary targets
testgen-agent generate ./my-project --skip-private --target-types normal boundary

# Reproduce the verified demo run
python main.py generate examples/demo-project \
  --provider anthropic --model deepseek-v4-flash --max-per-method 2 --no-coverage
cd examples/demo-project && mvn clean test
```

> Do **not** add a `mvn compile` step first — the agent builds the project itself, because `javac` cannot resolve the project's own types otherwise. (An earlier version told you to pre-build, which hid exactly that bug: a clean checkout scored an 18/40 compile rate. See fix 9.)

## How it works

```
Project directory
  │
[1] Project analysis    build-tool detection, source walk, classpath resolution,
  │                     and a build if target/classes is not there yet
[2] Method extraction   javalang → FQN, signature, modifiers, params, exceptions,
  │                     branch conditions, class context, allowed imports
[3] Target generation   Normal / Boundary / Exception / Path / Reflection / Mock
  │                     — descriptive targets the LLM has to satisfy
[4] LLM generation      fill the template → call the LLM → format the Java into a
  │                     uniquely named, correctly packaged test file
[5] Compile repair (A)  javac against the project classpath; on failure send the
  │                     error + code back to the LLM and retry
[6] Coverage (B)*       mvn test with JaCoCo → uncovered branches → [MissingBranch]
  │                     tests, repeated until the threshold is met
[7] Final verification  recompile every survivor, build the per-method report
[8] Test quality        empty classes, assertion density, mutation score (PiTest)
  ▼
Report — Markdown + JSON + CSV + console summary
```

*\*Phase B requires Maven and JaCoCo configured in the target project.*

Branch conditions are extracted from the **source code**, not Jimple IR — which removed the need for SootUp while preserving the LLM's visibility into control flow. `prompts/` holds four templates: `generate_{system,user}.txt` (persona, strict import restriction, framework syntax and exception rules, the reflection requirement for private methods) and `repair_{system,user}.txt` for the compile-fix loop. Framework-dependent wording is substituted into those templates rather than duplicated into a second set.

`--extraction-mode sootup` is a legacy opt-in backend that attaches Jimple IR via a subprocess; it degrades silently to javalang and is not what the verified runs used.

## Output

Everything lands in `<project>/.testgen-agent/`:

| File | For | Contents |
|---|---|---|
| `report.md` | **humans** | Mutation score first, then the weakest classes and what needs a human |
| `report.json` | CI / tooling | Every metric, machine-readable |
| `report.csv` | spreadsheets | Per-test-file detail |
| `run.log` | **debugging** | The diagnostics the console swallows — javac errors, LLM retries, classpath resolution, per-phase timings |

### Console (real output from the demo run, abridged)

```
  Test Generation Agent — Summary
  Build tool:         maven      Tests generated:    40
  Methods found:      22         Tests compiled:     40
  Methods targeted:   20         Compilation rate:   100.0%
  Test methods:       38         Assertion density:  2.79 per test
  Empty test classes: 2 (compile, but contain no @Test)
  Mutation score:     83.8% (67/80 mutants killed)
    (5 mutants were never even reached by a test)
    (2 test class(es) excluded — they fail before mutation)

  Weakest classes (mutation score):
  com.demo.BankAccount 76.5% (13/17)   com.demo.PasswordValidator 79.2% (19/24)
  com.demo.Calculator  78.9% (15/19)   com.demo.TextUtil          100.0% (20/20)
```

### `report.md` (abridged)

The human-facing artifact, written on every run and safe to commit or paste into a review. Mutation score leads:

```markdown
# TestGen Agent 报告 — demo-project

## 核心指标
| 指标 | 值 |
|---|---|
| **Mutation score** | **83.8%** (67/80 mutants killed) |
| 编译通过率 | 100.0% (40/40) |
| 可运行率 | 95.0% (38/40) |
| 断言密度 | 2.79 / 测试 |
| 空测试类 | 2 |

**结论：良好 —— 与人工撰写测试的典型水平（约 80–85%）相当。**

## 需要人工介入
**2 个测试运行时失败**（已排除出 mutation 分析，PiTest 要求测试全绿）:
- `com.demo.BankAccount_isOverdrawn_Test_Normal_8`
```

The Chinese headings are the report's own — it is written as UTF-8 to a file, so it is unaffected by the console codepage. The report ends with the exact command that reproduces the run.

### `report.json`

```json
{
  "build_tool": "maven",
  "methods_found": 22, "methods_targeted": 20,
  "tests_generated": 40, "tests_compiled": 40, "tests_runnable": 40,
  "compilation_rate": 1.0, "branch_coverage": null, "line_coverage": null,
  "total_test_methods": 38, "assertion_density": 2.789,
  "empty_test_classes": 2,
  "empty_test_class_names": ["PasswordValidator_hasDigit_Str_Test_Boundary_29"],
  "mutation_score": 0.8375, "mutations_killed": 67, "mutations_total": 80,
  "mutations_no_coverage": 5,
  "mutations_excluded_tests": ["com.demo.BankAccount_isOverdrawn_Test_Normal_8"],
  "mutation_by_class": [
    { "name": "com.demo.TextUtil", "killed": 20, "total": 20, "score": 1.0 }],
  "method_reports": [
    { "fqn": "com.demo.BankAccount.getBalance()", "tests_generated": 2,
      "tests_compiled": 2, "tests_runnable": 2 }]
}
```

`branch_coverage` / `line_coverage` are populated only when Phase B runs; `mutation_score` is `null` when mutation analysis was skipped or unavailable.

### `report.csv`

One row per test file: `Project, FQN, Signature, SourceCode, BranchConditions, ClassContext, AllowedImports, ThrowsExceptions, Modifiers, GenerationTarget, GeneratedCode, CodeAfterFormatting, SavedPath, Runnable`.

## Debugging a run

The console is a progress display — it tells you *what* is running, not *why* it failed. Every run also writes `.testgen-agent/run.log`, recording what is otherwise swallowed: the full javac error handed to the repair loop, LLM retries and their responses, and exactly what ended up on the classpath.

```bash
# The javac error behind a [FAIL] line
grep -A6 "FAILED (exit" .testgen-agent/run.log

# Per-phase timings — where did the time go?
grep "since last phase" .testgen-agent/run.log

# What was on the classpath
grep -A8 "classpath resolved" .testgen-agent/run.log
```

`-v` echoes the same output live on stderr. The log is rewritten on each run.

## Claude Code skill

A working skill definition is in [`references/skill-draft-SKILL.md`](references/skill-draft-SKILL.md). Copy it into place and fill in this repo's absolute path:

```bash
mkdir -p .claude/skills/generate-tests
cp references/skill-draft-SKILL.md .claude/skills/generate-tests/SKILL.md
# then replace <REPO> in that file with the absolute path to this repo
```

Start a new Claude Code session and run `/generate-tests examples/demo-project`. Claude reads the skill, runs the pipeline, reads `report.json`, and reports — including *why* any tests failed to compile, not just the counts.

> `skill.yaml` + `skill_entry.py` are a **legacy CLI wrapper that never worked** — they assume a `command:`/`arguments:` templating engine Claude Code does not have. Kept only for history; the definition above supersedes them.

## Requirements

- **Python 3.10+**
- **JDK 8+** on `JAVA_HOME` — a JDK, not a JRE. Generated tests match the level the project declares; Java 8 is the floor. Mutation analysis additionally needs **JDK 11+** to run PiTest.
- **Maven** *(optional)* — required for classpath resolution, Phase B, and Phase 8.
- An **API key** for your provider (see above).

On Windows, `javac` resolution requires `JAVA_HOME` to point at a JDK, and `mvn.cmd` is invoked through `cmd /c` automatically.

## Limitations

- **Framework and level follow the project.** A JUnit 4 project gets no lambdas and no `assertThrows`; a JUnit 5 project gets both. Java 8 is the floor.
- **Mocking is supported, narrowly.** A class whose constructor/field dependency is an interface or abstract class *resolving to project source* gets a `[Mock]` target, with the collaborator's public signatures put in the prompt. The idiom is explicit `Mockito.mock(...)`, never `@Mock`/`@InjectMocks` — the annotation form fails *silently* when the runner annotation is dropped (fields stay null, every test NPEs) and the compile-only repair loop cannot recover. Not covered: `mockStatic`, HTTP/DB/MQ stand-ins, and concrete project classes as parameters — so a constructor mixing a mockable collaborator with a concrete type gets no mock target rather than an uncompilable half-mock.
- **Mockito must already be declared in the pom.** The agent is read-only by default and warns instead. `--add-mock-deps` writes the dependency (idempotent, original backed up once to `pom.xml.testgen-backup`), picking `mockito-core` 4.11.0 for Java 8 and 5.12.0 for Java 11+, plus `mockito-junit-jupiter` on JUnit 5.
- **`[Exception]` targets only cover *declared* checked exceptions** (the `throws` clause). A method that throws `IllegalArgumentException` from its body gets no exception target, so the LLM may assert it with `try`/`catch` instead of `assertThrows`. Generating targets from `throw new X(...)` in the method body is the follow-up.
- Generated files are named `ClassName_method_ParamType_Test_Type_N`. Maven projects must configure surefire's `<includes>` — e.g. `**/*_Test_*.java` — for them to be executed; see `examples/demo-project/pom.xml`.
- Branch conditions come from source code, so compiler-generated branches can be missed.
- **PiTest requires Maven and a JDK 11+**, refuses to run unless the suite is green (failing classes are excluded and listed), and on a JUnit 5 project the target pom must declare `pitest-junit5-plugin` — the plugin is invoked as a bare GAV with `-D` properties, so there is no command-line channel for a plugin dependency. The agent detects its absence and skips with an explicit message rather than failing opaquely.
- Compiled-but-empty test classes are reported but **not** automatically regenerated.
- Large projects with hundreds of methods take significant time and tokens — the pipeline is single-threaded today.

## Verified fixes

Bugs found and fixed by actually running the pipeline on `examples/demo-project`:

1. **Windows Maven resolution** — `mvn` is `mvn.cmd` on Windows and the subprocess could not find it, so the classpath silently resolved empty.
2. **Test-scope dependencies missing** — `dependency:build-classpath` excludes test scope by default, so JUnit was never on the compile classpath; fixed with `-Dmdep.includeScope=test`.
3. **Anthropic `ThinkingBlock` handling** — DeepSeek returns a thinking block before the text block and the client crashed on `content[0].text`.
4. **`--max-per-method` ignored** — the target list was hard-coded to `targets[:10]`.
5. **Surefire naming mismatch** — generated files did not match surefire's default `*Test.java` pattern, so `mvn test` ran zero tests.
6. **Checkpoint and reports lived inside `target/`** — the coverage phase runs `mvn clean`, which deleted them mid-run. Moved to `.testgen-agent/`.
7. **PiTest requires a green suite** — one failing test aborted the whole mutation phase. The offending classes are now parsed out of PiTest's output, excluded, retried, and listed in the report.
8. **Compilation-only reporting was self-refuting** — the headline was "100% compile rate", but an empty test class compiles too. Phase 8 now reports mutation score, assertion density, and empty-class detection.
9. **The pipeline never built the project** — `resolve_classpath()` only adds `target/classes` when it already exists, so on a project that had not been pre-built every generated test failed with `cannot find symbol`. A clean-copy run scored an 18/40 compile rate and took 7× longer, because the repair loop burned three LLM attempts per test. It stayed hidden because the instructions told you to run `mvn compile` first.
10. **`main.py repair` crashed on every invocation** — it used `JavaProjectAnalyzer` without importing it, and printed `✓`/`✗`, which raise `UnicodeEncodeError` on a GBK console. It had never worked on Windows.
11. **Diagnostics were invisible** — the javac error was handed to the repair loop and never printed, so a failing test showed only `[FAIL] <file>`. Every run now writes `.testgen-agent/run.log` with the full javac error, LLM retries, and classpath resolution — the log that surfaced the classpath-deduplication bug fixed alongside it.

## License

MIT
