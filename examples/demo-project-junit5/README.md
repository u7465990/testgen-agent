# demo-project-junit5

The same four utility classes as [`../demo-project`](../demo-project), but on
**JUnit 5 / Java 17** instead of JUnit 4 / Java 8.

It exists to verify one thing: that testgen-agent **follows the project it is
pointed at** rather than imposing a framework. Same agent, two projects:

| Project | Detected as | Generated tests use |
|---------|-------------|---------------------|
| `../demo-project` | Java 8 / JUnit 4 | `org.junit.Test`, `org.junit.Assert` |
| `demo-project-junit5` | Java 17 / JUnit 5 | `org.junit.jupiter.api.Test`, `org.junit.jupiter.api.Assertions` |

Detection is automatic (`--junit auto` / `--java auto`, the defaults). It reads
the compiler level from `pom.xml` and the framework from the resolved test
classpath — see `target_profile.py`.

## Reproduction

```bash
# From the repo root
python main.py analyze examples/demo-project-junit5   # shows the detected target
python main.py generate examples/demo-project-junit5 \
  --provider anthropic --model deepseek-v4-flash --max-per-method 2 --no-coverage
cd examples/demo-project-junit5 && mvn clean test
```

## Measured results (2026-10)

Two runs on DeepSeek `deepseek-v4-flash`. **A sample, not a benchmark** — the
LLM does not repeat itself, which is why the score is quoted as a range.

| Metric | Result |
|--------|--------|
| Detected target | Java 17 / JUnit 5 |
| Test files generated | 40 |
| Compile pass rate | 40 / 40 (100%) |
| Tests executed (surefire) | 40 |
| **Mutation score (PiTest)** | **61–69 / 80 (76–86%)** |
| Assertion density | 2.83 per `@Test` method |
| Empty test classes | 0 |

The two runs scored 76.2% and 86.2%.

Sample generated exception assertion:

```java
IllegalArgumentException ex = Assertions.assertThrows(
        IllegalArgumentException.class,
        () -> account.deposit(0.0)
);
Assertions.assertEquals("Deposit must be positive", ex.getMessage());
```

## Why `pitest-junit5-plugin` is declared in this pom

PiTest cannot see JUnit 5 tests without it, and the plugin dependency **cannot
be passed on the Maven command line** — only the pom can supply it. testgen-agent
invokes PiTest as a fully-qualified plugin GAV with bare `-D` properties, so when
this dependency is missing the agent now detects that and skips mutation analysis
with an explicit message rather than letting Maven fail opaquely.

That is why the declaration lives here, in a project we own, instead of the agent
editing the pom of a project it was pointed at.

## Known limitations observed in these runs

- The `BankAccount.isOverdrawn` tests error out for the same reason as in the
  JUnit 4 demo: the constructor rejects negative balances, so an overdrawn state
  is unreachable through the public API and the generated tests try to construct
  one. The LLM understands the signature but not the class invariant.
- 0 of 40 generated files were empty test classes in these runs (an earlier run
  had 1).
- **`assertThrows` now appears** (5 files) and is used correctly — a lambda, with
  the thrown exception captured so its message can be asserted. An earlier
  published revision of this file claimed `assertThrows` never appeared; that was
  a symptom of a wiring bug, not of the target generator. The *generate* prompt
  was not being given the detected framework, so it kept asserting "Do NOT use
  assertThrows() (not available in JUnit 4)" while the target text asked for
  JUnit 5. The LLM resolved the contradiction with an anonymous
  `new Executable() { ... }` — legal under both readings, idiomatic under
  neither. The related but separate limitation still stands: `[Exception]` targets
  are only generated for *declared* checked exceptions, so a method that throws
  an unchecked exception from its body gets no exception target and the LLM may
  reach for `try/catch` instead. Detecting `throw new X(...)` in the method body
  is the follow-up for that.
