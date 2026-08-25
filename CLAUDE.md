# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

TestGen Agent is a standalone Python tool that automatically generates **JUnit 4 unit tests** for Java projects using an LLM (OpenAI, Anthropic, or any Anthropic-compatible endpoint such as DeepSeek). It parses a Java project, extracts methods and branch conditions, generates rule-based test targets, asks an LLM to write a test for each target, compiles the results with `javac`, repairs compilation failures by feeding errors back to the LLM, and writes a JSON/CSV/console report. The only runtime the Python code itself exercises is the LLM and `javac`/`mvn` — the "tests" are generated JUnit files, verified by running `mvn test` against a real Java project (see `examples/demo-project`). There is no Python test suite.

The verified demo run (`examples/demo-project`, Maven, Java 8, 4 classes) produced 40 tests with 100% compile rate and 36/38 runtime pass rate. Full details are in `README.md`.

## Commands

Requires Python 3.10+, `javac` (JDK on `JAVA_HOME`, not a JRE), and an LLM API key. On Windows `mvn.cmd` is invoked through `cmd /c` automatically.

```bash
# Discover methods a project would target (no LLM calls, fast)
python main.py analyze <project-path>

# Full pipeline: discover → extract → generate → repair → report
python main.py generate <project-path>

# Re-compile already-generated _Test_*.java files and report status
python main.py repair <project-path>
```

API keys: `OPENAI_API_KEY` (default provider `openai`, model `gpt-4o-mini`), or for Anthropic/DeepSeek use `--provider anthropic` plus `ANTHROPIC_API_KEY` (falls back to `ANTHROPIC_AUTH_TOKEN`) and `ANTHROPIC_BASE_URL` (e.g. `https://api.deepseek.com/anthropic`).

Useful flags: `--package <pkg>` (takes a **package name** like `com.demo`, repeatable, not a class name), `--exclude <method>`, `--skip-private`, `--target-types normal boundary`, `--max-per-method N` (default 10), `--max-repair N` (default 3), `--no-coverage` (skips the JaCoCo phase B), `--no-resume` (ignore the JSONL checkpoint and regenerate from scratch), `--provider anthropic --model <model>`.

Reproducing the verified demo run:

```bash
cd examples/demo-project && mvn -q compile
cd ../.. && python main.py generate examples/demo-project \
  --provider anthropic --model deepseek-v4-flash --max-per-method 2 --no-coverage
cd examples/demo-project && mvn test   # must use `clean` if re-running: mvn clean test
```

Note: generated test files use the naming convention `ClassName_method_ParamType_Test_Type_N`; Maven projects must configure surefire `<includes>**/*_Test_*.java</includes>` for them to be executed (see `examples/demo-project/pom.xml`).

## Architecture

The pipeline is orchestrated by `TestGeneratorAgent.run()` in `agent.py`, which drives 7 phases. `AgentConfig` (`config.py`) is the single configuration object threaded through every module.

```
project/ → [1] java_analyzer → [2] method_extractor → [3] target_generator
        → [4] prompt_manager + llm_client + test_writer → [5] compiler + repair_loop (Phase A)
        → [6] coverage_analyzer + repair_loop (Phase B, optional) → [7] report_generator
```

- **Phase 1 — Project analysis** (`java_analyzer.py`): `JavaProjectAnalyzer` detects the build tool (Maven/Ant/Gradle/manual via `pom.xml`/`build.gradle`/`build.xml`), walks `src/main/java` for `.java` files, and resolves the classpath. `resolve_classpath()` runs `mvn dependency:build-classpath -Dmdep.includeScope=test` (test scope is required so JUnit is on the compile classpath) and caches to `target/classpath.txt`. The classpath separator is `;` on Windows, `:` elsewhere.
- **Phase 2 — Method extraction** (`method_extractor.py` + `extractor/`): `MethodExtractor` is a facade over a backend. The default `JavalangBackend` (`extractor/javalang_backend.py`) parses source with `javalang`, producing a `MethodInfo` per method. `SootUpBackend` (`extractor/sootup_backend.py`) is an opt-in (`--extraction-mode sootup`) that additionally compiles `extractor/SootUpExtractor.java` and runs it as a subprocess to attach Jimple IR — it requires a compiled `target/classes` and SootUp JARs, and silently falls back to javalang-only on any failure.
- **Phase 3 — Target generation** (`target_generator.py`): `TargetGenerator` turns each `MethodInfo` into descriptive target strings the LLM must satisfy: `[Normal]`, `[Boundary]` (one per parameter, from a type→edge-value table), `[Exception]` (one per declared checked exception), `[Path]` (two per extracted branch condition, true/false), `[Reflection]` (for private methods). Results are capped at `max_tests_per_method`.
- **Phase 4 — LLM generation** (`prompt_manager.py`, `llm_client.py`, `test_writer.py`): `PromptManager` loads the four `.txt` templates from `prompts/` and substitutes `#{FQN}#`, `#{Signature}#`, `#{SourceCode}#`, `#{BranchConditions}#`, `#{ClassContext}#`, `#{AllowedImports}#`, `#{ThrowsExceptions}#`, `#{Modifiers}#`, `#{GenerationTarget}#` (`#{JimpleCode}#` is empty unless the sootup backend ran). `LLMClient` wraps OpenAI and Anthropic chat APIs with exponential-backoff retries. `TestWriter` extracts the Java block from the response, dedupes imports, renames the class to the deterministic `ClassName_method_ParamType_Test_Type_N` form, writes the file to `src/test/java/<package>/`, and also derives the package from the FQN.
- **Phase 5 — Compilation repair (Phase A)** (`compiler.py`, `repair_loop.py`): `JavaCompiler` invokes `javac` with `-source 8 -target 8` against the resolved classpath. `RepairLoop.repair_compilation()` runs up to `max_compile_attempts` rounds: compile → on failure, send the javac error + code back to the LLM via `render_repair_prompt()` → write the fix → recompile. It force-fixes the `package` declaration before each compile and injects a reflection hint when the error mentions `private`.
- **Phase 6 — Coverage improvement (Phase B, optional)** (`coverage_analyzer.py`, `repair_loop.improve_coverage()`): only when `--no-coverage` is absent. Runs `mvn clean test jacoco:report`, parses `target/site/jacoco/jacoco.xml`, finds methods below `branch_coverage_target` (0.98), and generates `[MissingBranch]` tests, up to `max_runtime_rounds` (3). Requires Maven + JaCoCo configured in the target project; on any failure it prints a warning and returns no new tests.
- **Phase 7 — Reporting** (`report_generator.py`): `AgentReport` is assembled per-method (`MethodReport`), printed to console, and written to `target/testgen-agent/report.json` and `report.csv`. Compilation rate is computed in Phase 7 by recompiling every surviving test file.

## Key data model and conventions

- **`MethodInfo`** (`method_extractor.py`) is the central data structure flowing through the whole pipeline: FQN, signature, source code, `branch_conditions` (extracted via regex over the body for `if`/`while`/`for`/`catch` predicates), `class_context` (fields + constructors), `allowed_imports` (JUnit + reflection + `java.lang.reflect` always allowed, plus project imports), `throws_exceptions`, and flags (`is_private`, `is_static`, `is_abstract`, `is_constructor`).
- **`TestFile`** (`repair_loop.py`) wraps a generated test file with its `compiles` / `runnable` / `compile_attempts` status.
- **Prompt templates** live in `prompts/`: `generate_system.txt`/`generate_user.txt` define the persona, strict import restriction, JUnit 4-only rules (no `assertThrows`, no lambdas, no Java 8+ APIs), and reflection requirement for private methods; `repair_system.txt`/`repair_user.txt` are for the compile-fix loop.
- **Claude Code skill**: `skill.yaml` + `skill_entry.py` expose the pipeline as `/generate-tests`; `skill_entry()` builds an `AgentConfig` and returns a structured summary dict.

## Gotchas

- **Windows**: `javac` resolution requires `JAVA_HOME` to point at a JDK; `mvn` on Windows is `mvn.cmd` and must be run through `cmd /c` (handled in `java_analyzer._resolve_maven_classpath`). Do not hard-code Unix paths/separators.
- **Anthropic-compatible models (e.g. DeepSeek) return a `ThinkingBlock` before the text block** — `LLMClient` concatenates only `type == "text"` blocks; keep this when changing the client.
- **The classpath must include test-scope dependencies** (`-Dmdep.includeScope=test`); without it JUnit is missing and every generated test fails to compile.
- **The compilation check does not catch empty test classes** (no `@Test` method) — a file can compile yet still be a no-op, which is why the demo shows 40 compiled but only 38 executed.
- **Resume/checkpoint** (`agent.py` + `checkpoint.py`): `generate` processes source files in a streaming loop and records each successfully-compiled test to `target/testgen-agent/checkpoint.jsonl` (JSONL; each line stores the full `MethodInfo`). A re-run skips recorded tests so an interrupted run doesn't re-call the LLM; the global target counter still advances for skipped items so class names match a full run. Phase B (coverage) tests are not checkpointed; `mvn clean` wipes `target/`, deleting the checkpoint too.
- `--package` filters on the package name only, not the class name; the demo classes all live in `com.demo`.
- The `sootup` extraction backend (`extractor/`) is legacy/opt-in and degrades gracefully; the default `python` mode (javalang, no Jimple) is what the verified run used.
